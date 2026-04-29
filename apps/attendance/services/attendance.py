"""
Attendance Service - Core attendance business logic
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, List, Dict, Any
from datetime import date, time, datetime, timedelta
import logging

from ..models import (
    AttendanceRegister, AttendanceRecord, AttendanceSummary,
    QRCode
)
from ..constants import (
    AttendanceStatus, SessionType, MarkingMethod,
    LOW_ATTENDANCE_THRESHOLD, CRITICAL_ATTENDANCE_THRESHOLD,
    LATE_THRESHOLD_MINUTES, DEFAULT_SESSION_TIMES
)
from ..exceptions import (
    AttendanceRecordNotFoundError,
    DuplicateAttendanceError,
    InvalidAttendanceStatusError,
    StudentNotFoundError,
    ClassNotFoundError,
    QRCodeError,
    InvalidQRCodeError,
    ExpiredQRCodeError,
)
from ..selectors import AttendanceRegisterSelector, AttendanceRecordSelector

from apps.corecode.services import SystemLogService
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector, AcademicTermSelector
from apps.corecode.models import SystemLog
from apps.students.selectors import StudentSelector
from apps.parents.services import NotificationService
from apps.parents.constants import NotificationType

logger = logging.getLogger(__name__)


class AttendanceService:
    """
    Attendance business operations
    Single source of truth for attendance management
    """

    @staticmethod
    @transaction.atomic
    def create_register(
        class_id: int,
        date: date,
        session_type: str = SessionType.MORNING,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        marked_by_id: Optional[int] = None,
        marking_method: str = MarkingMethod.MANUAL
    ) -> AttendanceRegister:
        """
        Create an attendance register for a class
        """
        # Validate class
        student_class = StudentClassSelector.get_by_id(class_id)
        if not student_class:
            raise ClassNotFoundError(f"Class with id {class_id} not found")

        # Get academic context
        if not session_id:
            current_session = AcademicSessionSelector.get_current_session()
            if not current_session:
                raise ValidationError("No active academic session configured")
            session_id = current_session.id

        # Check for existing register
        existing = AttendanceRegister.objects.filter(
            student_class_id=class_id,
            date=date,
            session_type=session_type
        ).exists()

        if existing:
            raise DuplicateAttendanceError(
                f"Register already exists for {student_class['display_name']} on {date}"
            )

        # Create register
        register = AttendanceRegister.objects.create(
            student_class_id=class_id,
            academic_session_id=session_id,
            academic_term_id=term_id,
            date=date,
            session_type=session_type,
            marked_by_id=marked_by_id,
            marking_method=marking_method
        )

        logger.info(f"Attendance register created: {register.register_number}")
        return register

    @staticmethod
    @transaction.atomic
    def mark_attendance(
        register_id: int,
        student_id: int,
        status: str,
        check_in_time: Optional[time] = None,
        remarks: str = "",
        marked_by_id: Optional[int] = None
    ) -> AttendanceRecord:
        """
        Mark attendance for a single student
        """
        try:
            register = AttendanceRegister.objects.select_for_update().get(id=register_id)
        except AttendanceRegister.DoesNotExist:
            raise AttendanceRecordNotFoundError(f"Register {register_id} not found")

        # Check if register is closed
        if register.is_closed:
            raise ValidationError("Cannot mark attendance on closed register")

        # Get student info
        student = StudentSelector.get_by_id(student_id)
        if not student:
            raise StudentNotFoundError(f"Student {student_id} not found")

        # Check for duplicate
        existing = AttendanceRecord.objects.filter(
            register=register,
            student_id=student_id
        ).first()

        if existing:
            raise DuplicateAttendanceError(
                f"Attendance already marked for {student['full_name']}"
            )

        # Validate status
        valid_statuses = [s[0] for s in AttendanceStatus.CHOICES]
        if status not in valid_statuses:
            raise InvalidAttendanceStatusError(f"Invalid status: {status}")

        # Auto-set check-in time for present/late
        if status in [AttendanceStatus.PRESENT, AttendanceStatus.LATE] and not check_in_time:
            check_in_time = timezone.now().time()

        # Create record
        record = AttendanceRecord.objects.create(
            register=register,
            student_id=student_id,
            student_name=student['full_name'],
            status=status,
            check_in_time=check_in_time,
            remarks=remarks,
            marked_by_id=marked_by_id
        )

        # Update register counts
        register.update_counts()

        # Check if this triggers an attendance alert
        AttendanceService._check_attendance_alert(student_id)

        logger.info(f"Attendance marked for {student['full_name']} in register {register_id}")
        return record

    @staticmethod
    @transaction.atomic
    def mark_bulk_attendance(
        register_id: int,
        attendance_data: List[Dict[str, Any]],
        marked_by_id: Optional[int] = None
    ) -> List[AttendanceRecord]:
        """
        Mark attendance for multiple students at once
        """
        try:
            register = AttendanceRegister.objects.select_for_update().get(id=register_id)
        except AttendanceRegister.DoesNotExist:
            raise AttendanceRecordNotFoundError(f"Register {register_id} not found")

        if register.is_closed:
            raise ValidationError("Cannot mark attendance on closed register")

        records = []
        errors = []

        for data in attendance_data:
            try:
                student_id = data.get('student_id')
                status = data.get('status')

                if not student_id or not status:
                    errors.append({
                        'student_id': student_id,
                        'error': 'Missing student_id or status'
                    })
                    continue

                record = AttendanceService.mark_attendance(
                    register_id=register_id,
                    student_id=student_id,
                    status=status,
                    check_in_time=data.get('check_in_time'),
                    remarks=data.get('remarks', ''),
                    marked_by_id=marked_by_id
                )
                records.append(record)

            except Exception as e:
                errors.append({
                    'student_id': data.get('student_id'),
                    'error': str(e)
                })

        if errors:
            logger.warning(f"Bulk attendance had {len(errors)} errors")

        return records

    @staticmethod
    @transaction.atomic
    def update_attendance(
        record_id: int,
        status: Optional[str] = None,
        check_in_time: Optional[time] = None,
        remarks: Optional[str] = None,
        updated_by_id: Optional[int] = None
    ) -> AttendanceRecord:
        """
        Update an existing attendance record
        """
        try:
            record = AttendanceRecord.objects.select_related('register').get(id=record_id)
        except AttendanceRecord.DoesNotExist:
            raise AttendanceRecordNotFoundError(f"Record {record_id} not found")

        if record.register.is_closed:
            raise ValidationError("Cannot update attendance on closed register")

        changes = {}

        if status and status != record.status:
            # Validate status
            valid_statuses = [s[0] for s in AttendanceStatus.CHOICES]
            if status not in valid_statuses:
                raise InvalidAttendanceStatusError(f"Invalid status: {status}")

            changes['status'] = {'old': record.status, 'new': status}
            record.status = status

        if check_in_time and check_in_time != record.check_in_time:
            changes['check_in_time'] = {
                'old': record.check_in_time.isoformat() if record.check_in_time else None,
                'new': check_in_time.isoformat()
            }
            record.check_in_time = check_in_time

        if remarks is not None and remarks != record.remarks:
            changes['remarks'] = {'old': record.remarks, 'new': remarks}
            record.remarks = remarks

        if changes:
            record.save(update_fields=['status', 'check_in_time', 'remarks', 'updated_at'])

            # Update register counts
            record.register.update_counts()

            # Log update
            SystemLogService.log_action(
                user_id=updated_by_id,
                action=SystemLog.ActionType.UPDATE,
                app_label=SystemLog.AppLabel.ATTENDANCE,
                model_name='AttendanceRecord',
                object_id=str(record.id),
                object_repr=f"{record.student_name} - {record.register.date}",
                changes=changes
            )

        return record

    @staticmethod
    @transaction.atomic
    def close_register(
        register_id: int,
        closed_by_id: Optional[int] = None
    ) -> AttendanceRegister:
        """
        Close an attendance register (prevent further edits)
        """
        try:
            register = AttendanceRegister.objects.get(id=register_id)
        except AttendanceRegister.DoesNotExist:
            raise AttendanceRecordNotFoundError(f"Register {register_id} not found")

        register.is_closed = True
        register.closed_at = timezone.now()
        register.closed_by_id = closed_by_id
        register.save(update_fields=['is_closed', 'closed_at', 'closed_by', 'updated_at'])

        logger.info(f"Register {register.register_number} closed")
        return register

    @staticmethod
    def process_qr_check_in(
        qr_code: str,
        session_type: str = SessionType.MORNING,
        check_in_time: Optional[time] = None
    ) -> AttendanceRecord:
        """
        Process QR code check-in for a student
        """
        from ..selectors import QRCodeSelector
    
        # Validate QR code
        qr_data = QRCodeSelector.validate_code(qr_code)
        if not qr_data:
            raise InvalidQRCodeError("Invalid or expired QR code")
    
        student_id = qr_data['student_id']
        today = date.today()
    
        # FIXED: Get student info first to find their class
        student = StudentSelector.get_by_id(student_id)
        if not student:
            raise StudentNotFoundError(f"Student {student_id} not found")
    
        class_id = student.get('current_class', {}).get('id')
        if not class_id:
            raise ValidationError("Student has no assigned class")
    
        # Find or create register for this class today
        try:
            register = AttendanceRegister.objects.get(
                student_class_id=class_id,
                date=today,
                session_type=session_type
            )
        except AttendanceRegister.DoesNotExist:
            register = AttendanceService.create_register(
                class_id=class_id,
                date=today,
                session_type=session_type,
                marking_method=MarkingMethod.QR_CODE
            )
    
        # Check if already marked
        existing = AttendanceRecord.objects.filter(
            register=register,
            student_id=student_id
        ).first()
    
        if existing:
            if existing.status == AttendanceStatus.ABSENT:
                existing.status = AttendanceStatus.PRESENT
                existing.check_in_time = check_in_time or timezone.now().time()
                existing.save(update_fields=['status', 'check_in_time', 'updated_at'])
                record = existing
            else:
                raise DuplicateAttendanceError("Attendance already marked for today")
        else:
            record = AttendanceService.mark_attendance(
                register_id=register.id,
                student_id=student_id,
                status=AttendanceStatus.PRESENT,
                check_in_time=check_in_time,
                remarks="Checked in via QR code",
                marked_by_id=None
            )
    
        # Update QR code usage (same-app model, acceptable)
        QRCode.objects.filter(code=qr_code).update(
            last_used=timezone.now(),
            use_count=models.F('use_count') + 1
        )
    
        return record
    


    @staticmethod
    def _check_attendance_alert(student_id: int):
        """
        Check if student's attendance has dropped below threshold
        and send notification if needed
        """
        # Get current session and term
        current_session = AcademicSessionSelector.get_current_session()
        if not current_session:
            return

        current_term = AcademicTermSelector.get_current_term()

        # Get or create summary
        summary, created = AttendanceSummary.objects.get_or_create(
            student_id=student_id,
            academic_session=current_session,
            academic_term=current_term,
            defaults={
                'student_name': StudentSelector.get_by_id(student_id)['full_name'],
            }
        )

        # Recalculate summary
        AttendanceService._update_student_summary(student_id, current_session.id, current_term.id)

        # Refresh summary
        summary.refresh_from_db()

        # Check if alert needed
        if summary.attendance_alert:
            # Get parent(s) for this student
            from apps.parents.selectors import ChildLinkSelector
            parents = ChildLinkSelector.get_for_student(student_id)

            for parent in parents:
                # Send notification
                NotificationService.send_notification(
                    parent_id=parent['parent_id'],
                    notification_type=NotificationType.ATTENDANCE_ALERT,
                    title="Attendance Alert",
                    message=f"Your child's attendance has dropped to {summary.present_percentage:.1f}%. "
                            f"Please contact the school.",
                    data={
                        'student_id': student_id,
                        'student_name': summary.student_name,
                        'attendance': summary.present_percentage,
                    },
                    related_student_ids=[student_id],
                    priority='high'
                )

    @staticmethod
    def _update_student_summary(
        student_id: int,
        session_id: int,
        term_id: Optional[int] = None
    ) -> AttendanceSummary:
        """
        Update attendance summary for a student
        """
        # Get all records for this student in the session/term
        records = AttendanceRecord.objects.filter(
            student_id=student_id,
            register__academic_session_id=session_id
        )

        if term_id:
            records = records.filter(register__academic_term_id=term_id)

        # Calculate totals
        total_days = records.count()
        present_days = records.filter(status=AttendanceStatus.PRESENT).count()
        absent_days = records.filter(status=AttendanceStatus.ABSENT).count()
        late_days = records.filter(status=AttendanceStatus.LATE).count()
        excused_days = records.filter(
            status__in=[AttendanceStatus.EXCUSED, AttendanceStatus.SICK]
        ).count()

        # Get or create summary
        summary, created = AttendanceSummary.objects.get_or_create(
            student_id=student_id,
            academic_session_id=session_id,
            academic_term_id=term_id,
            defaults={
                'student_name': StudentSelector.get_by_id(student_id)['full_name'],
            }
        )

        # Update counts
        summary.total_days = total_days
        summary.present_days = present_days
        summary.absent_days = absent_days
        summary.late_days = late_days
        summary.excused_days = excused_days
        summary.calculate_percentages()
        summary.save()

        return summary

    @staticmethod
    def update_all_summaries(
        session_id: Optional[int] = None,
        term_id: Optional[int] = None
    ) -> int:
        """
        Update attendance summaries for all students
        Run periodically via celery beat
        """
        from apps.students.selectors import StudentSelector

        if not session_id:
            current_session = AcademicSessionSelector.get_current_session()
            if not current_session:
                return 0
            session_id = current_session.id

        # Get all students
        students = StudentSelector.list_students(limit=10000)  # Get all

        count = 0
        for student in students:
            try:
                AttendanceService._update_student_summary(
                    student_id=student['id'],
                    session_id=session_id,
                    term_id=term_id
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to update summary for student {student['id']}: {e}")

        logger.info(f"Updated attendance summaries for {count} students")
        return count
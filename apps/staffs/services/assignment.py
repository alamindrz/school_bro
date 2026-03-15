"""
Assignment Service - Subject and duty assignments for staff
"""

from django.db import transaction
from django.utils import timezone
from typing import Optional, List, Dict, Any
import logging

from ..models import SubjectAssignment, DutyAssignment, Staff
from ..exceptions import StaffNotFoundError, SubjectAssignmentError
from ..selectors import StaffSelector

from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog, Subject
from apps.corecode.selectors import AcademicSessionSelector
from apps.corecode.selectors import StudentClassSelector

logger = logging.getLogger(__name__)


class AssignmentService:
    """
    Staff assignment business operations
    Handles subject assignments, duty posts, form masters, etc.
    """

    @staticmethod
    @transaction.atomic
    def assign_subject(
        staff_id: int,
        subject_id: int,
        class_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        periods_per_week: int = 1,
        is_class_teacher: bool = False,
        is_form_master: bool = False,
        assigned_by_id: Optional[int] = None
    ) -> SubjectAssignment:
        """
        Assign a subject to a staff member for a specific class
        """
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            raise StaffNotFoundError(f"Staff with id {staff_id} not found")

        # Validate staff is teaching staff
        if staff.staff_category != 'academic':
            raise SubjectAssignmentError("Only academic staff can be assigned subjects")

        # Get current session if not provided
        if not session_id:
            current_session = AcademicSessionSelector.get_current_session()
            if not current_session:
                raise ValidationError("No active academic session configured")
            session_id = current_session.id

        # Check for existing assignment
        existing = SubjectAssignment.objects.filter(
            staff_id=staff_id,
            subject_id=subject_id,
            student_class_id=class_id,
            academic_session_id=session_id,
            academic_term_id=term_id
        ).first()

        if existing:
            logger.info(f"Assignment already exists for staff {staff_id}")
            return existing

        # Create assignment
        assignment = SubjectAssignment.objects.create(
            staff=staff,
            subject_id=subject_id,
            student_class_id=class_id,
            academic_session_id=session_id,
            academic_term_id=term_id,
            periods_per_week=periods_per_week,
            is_class_teacher=is_class_teacher,
            is_form_master=is_form_master,
            assigned_by_id=assigned_by_id
        )

        # Log the action
        SystemLogService.log_action(
            user_id=assigned_by_id,
            action=SystemLog.ActionType.CREATE,
            app_label=SystemLog.AppLabel.STAFFS,
            model_name='SubjectAssignment',
            object_id=str(assignment.id),
            object_repr=f"{staff.get_full_name} - {assignment.subject.name}",
            changes={
                'staff_id': staff_id,
                'subject_id': subject_id,
                'class_id': class_id,
                'session_id': session_id,
            }
        )

        logger.info(f"Subject assigned to staff {staff_id}")
        return assignment

    @staticmethod
    @transaction.atomic
    def assign_duty(
        staff_id: int,
        duty_post: str,
        session_id: Optional[int] = None,
        class_id: Optional[int] = None,
        club_name: str = '',
        sport_name: str = '',
        house_name: str = '',
        day_of_week: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        assigned_by_id: Optional[int] = None
    ) -> DutyAssignment:
        """
        Assign a duty post to a staff member
        """
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            raise StaffNotFoundError(f"Staff with id {staff_id} not found")

        # Get current session if not provided
        if not session_id:
            current_session = AcademicSessionSelector.get_current_session()
            if not current_session:
                raise ValidationError("No active academic session configured")
            session_id = current_session.id

        # Parse times if provided
        start = None
        end = None
        if start_time:
            from datetime import datetime
            start = datetime.strptime(start_time, '%H:%M').time()
        if end_time:
            from datetime import datetime
            end = datetime.strptime(end_time, '%H:%M').time()

        # Create duty assignment
        duty = DutyAssignment.objects.create(
            staff=staff,
            duty_post=duty_post,
            academic_session_id=session_id,
            student_class_id=class_id,
            club_name=club_name,
            sport_name=sport_name,
            house_name=house_name,
            day_of_week=day_of_week,
            start_time=start,
            end_time=end,
            assigned_by_id=assigned_by_id
        )

        logger.info(f"Duty {duty_post} assigned to staff {staff_id}")
        return duty

    @staticmethod
    @transaction.atomic
    def set_form_master(
        staff_id: int,
        class_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        assigned_by_id: Optional[int] = None
    ) -> SubjectAssignment:
        """
        Set a staff member as form master for a class
        """
        # Remove existing form master for this class
        SubjectAssignment.objects.filter(
            student_class_id=class_id,
            academic_session_id=session_id,
            academic_term_id=term_id,
            is_form_master=True
        ).update(is_form_master=False)

        # Find or create subject assignment for this staff
        # Usually the form master teaches at least one subject in the class
        assignment = SubjectAssignment.objects.filter(
            staff_id=staff_id,
            student_class_id=class_id,
            academic_session_id=session_id
        ).first()

        if assignment:
            assignment.is_form_master = True
            assignment.save(update_fields=['is_form_master'])
        else:
            # Create a minimal assignment just for form mastery
            # This assumes they teach at least one subject - need subject_id
            raise SubjectAssignmentError(
                "Staff must be assigned at least one subject in the class to be form master"
            )

        logger.info(f"Staff {staff_id} set as form master for class {class_id}")
        return assignment

    @staticmethod
    @transaction.atomic
    def assign_class_teacher(
        staff_id: int,
        class_id: int,
        subject_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        assigned_by_id: Optional[int] = None
    ) -> SubjectAssignment:
        """
        Assign a staff member as class teacher for a specific subject
        """
        return AssignmentService.assign_subject(
            staff_id=staff_id,
            subject_id=subject_id,
            class_id=class_id,
            session_id=session_id,
            term_id=term_id,
            is_class_teacher=True,
            assigned_by_id=assigned_by_id
        )
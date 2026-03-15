"""
Bulk Attendance Service - CSV import and bulk operations
"""

import csv
import io
from datetime import datetime, date
from typing import List, Dict, Any, Tuple, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
import logging

from ..models import AttendanceRegister, AttendanceRecord
from ..constants import AttendanceStatus
from ..exceptions import BulkOperationError
from .attendance import AttendanceService

from apps.students.selectors import StudentSelector
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector

logger = logging.getLogger(__name__)


class BulkAttendanceService:
    """
    Bulk attendance operations (CSV import, mass updates)
    """

    REQUIRED_CSV_FIELDS = ['student_id', 'status']
    OPTIONAL_CSV_FIELDS = ['check_in_time', 'remarks']

    @classmethod
    @transaction.atomic
    def import_from_csv(
        cls,
        csv_file,
        register_id: int,
        marked_by_id: Optional[int] = None
    ) -> Tuple[List[AttendanceRecord], List[Dict[str, Any]]]:
        """
        Import attendance from CSV file
        """
        try:
            register = AttendanceRegister.objects.get(id=register_id)
        except AttendanceRegister.DoesNotExist:
            raise BulkOperationError(f"Register {register_id} not found")

        if register.is_closed:
            raise BulkOperationError("Cannot import to closed register")

        successful = []
        failed = []

        try:
            decoded_file = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            # Validate headers
            headers = reader.fieldnames or []
            missing = [f for f in cls.REQUIRED_CSV_FIELDS if f not in headers]
            if missing:
                raise BulkOperationError(f"Missing required columns: {', '.join(missing)}")

            for row_num, row in enumerate(reader, start=2):
                try:
                    student_id = int(row.get('student_id'))
                    status = row.get('status')

                    # Validate status
                    valid_statuses = [s[0] for s in AttendanceStatus.CHOICES]
                    if status not in valid_statuses:
                        raise ValidationError(f"Invalid status: {status}")

                    # Check if student exists
                    student = StudentSelector.get_by_id(student_id)
                    if not student:
                        raise ValidationError(f"Student {student_id} not found")

                    # Parse check-in time if provided
                    check_in_time = None
                    if row.get('check_in_time'):
                        try:
                            check_in_time = datetime.strptime(
                                row['check_in_time'], '%H:%M'
                            ).time()
                        except ValueError:
                            raise ValidationError(f"Invalid check-in time format: {row['check_in_time']}")

                    # Mark attendance
                    record = AttendanceService.mark_attendance(
                        register_id=register_id,
                        student_id=student_id,
                        status=status,
                        check_in_time=check_in_time,
                        remarks=row.get('remarks', ''),
                        marked_by_id=marked_by_id
                    )
                    successful.append(record)

                except Exception as e:
                    failed.append({
                        'row': row_num,
                        'data': row,
                        'error': str(e)
                    })

        except Exception as e:
            raise BulkOperationError(f"CSV import failed: {str(e)}")

        logger.info(
            f"CSV import completed: {len(successful)} successful, {len(failed)} failed"
        )

        return successful, failed

    @classmethod
    def generate_csv_template(cls, class_id: int) -> str:
        """
        Generate CSV template for a class
        """
        from apps.students.selectors import StudentSelector

        students = StudentSelector.get_class_students(class_id=class_id)

        output = io.StringIO()
        writer = csv.writer(output)

        # Write headers
        headers = cls.REQUIRED_CSV_FIELDS + cls.OPTIONAL_CSV_FIELDS
        writer.writerow(headers)

        # Write example rows
        for student in students[:5]:  # Add first 5 as examples
            writer.writerow([
                student['id'],
                AttendanceStatus.PRESENT,
                '08:00',
                'On time'
            ])

        return output.getvalue()

    @classmethod
    @transaction.atomic
    def mark_all_present(
        cls,
        register_id: int,
        marked_by_id: Optional[int] = None
    ) -> List[AttendanceRecord]:
        """
        Mark all students in a class as present
        """
        try:
            register = AttendanceRegister.objects.get(id=register_id)
        except AttendanceRegister.DoesNotExist:
            raise BulkOperationError(f"Register {register_id} not found")

        if register.is_closed:
            raise BulkOperationError("Cannot modify closed register")

        # Get all students in the class
        from apps.students.selectors import StudentSelector
        students = StudentSelector.get_class_students(
            class_id=register.student_class_id,
            academic_session_id=register.academic_session_id
        )

        records = []
        for student in students:
            try:
                record = AttendanceService.mark_attendance(
                    register_id=register_id,
                    student_id=student['id'],
                    status=AttendanceStatus.PRESENT,
                    marked_by_id=marked_by_id
                )
                records.append(record)
            except Exception as e:
                logger.error(f"Failed to mark student {student['id']}: {e}")

        logger.info(f"Marked all {len(records)} students as present in register {register_id}")
        return records

    @classmethod
    @transaction.atomic
    def copy_from_previous_day(
        cls,
        target_register_id: int,
        source_date: date,
        marked_by_id: Optional[int] = None
    ) -> List[AttendanceRecord]:
        """
        Copy attendance from previous day's register
        """
        try:
            target_register = AttendanceRegister.objects.get(id=target_register_id)
        except AttendanceRegister.DoesNotExist:
            raise BulkOperationError(f"Target register {target_register_id} not found")

        if target_register.is_closed:
            raise BulkOperationError("Cannot modify closed register")

        # Find source register
        try:
            source_register = AttendanceRegister.objects.get(
                student_class=target_register.student_class,
                date=source_date,
                session_type=target_register.session_type
            )
        except AttendanceRegister.DoesNotExist:
            raise BulkOperationError(f"No register found for {source_date}")

        # Copy attendance records
        source_records = AttendanceRecord.objects.filter(register=source_register)

        records = []
        for source in source_records:
            try:
                record = AttendanceService.mark_attendance(
                    register_id=target_register_id,
                    student_id=source.student_id,
                    status=source.status,
                    remarks=f"Copied from {source_date}",
                    marked_by_id=marked_by_id
                )
                records.append(record)
            except Exception as e:
                logger.error(f"Failed to copy record for student {source.student_id}: {e}")

        logger.info(f"Copied {len(records)} records from {source_date}")
        return records
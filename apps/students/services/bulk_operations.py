"""
Bulk Operations Service
Handles bulk import, export, and mass updates of students
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from typing import List, Dict, Any, Tuple, Optional
import csv
import io
import logging
from datetime import datetime

from ..models import Student
from ..services import StudentService, AdmissionNumberService, StudentUserService
from ..exceptions import BulkOperationError, StudentValidationError
from ..validators import BulkOperationValidator
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class BulkStudentService:
    """
    Bulk operations for student management.
    Handles large-scale imports, exports, and updates.
    """
    
    BATCH_SIZE = 100
    REQUIRED_CSV_FIELDS = [
        'first_name', 'last_name', 'date_of_birth', 
        'gender', 'current_class'
    ]
    OPTIONAL_CSV_FIELDS = [
        'middle_name', 'email', 'phone', 'address', 
        'city', 'state_of_origin', 'blood_group',
        'medical_notes', 'has_special_needs'
    ]
    
    @classmethod
    @transaction.atomic
    def import_from_csv(
        cls,
        csv_file,
        academic_session_id: Optional[int] = None,
        create_user_accounts: bool = False,
        send_welcome_emails: bool = False,
        imported_by_id: Optional[int] = None,
        batch_size: int = BATCH_SIZE
    ) -> Tuple[List[Student], List[Dict[str, Any]]]:
        """
        Import students from CSV file.
        
        Args:
            csv_file: Uploaded CSV file
            academic_session_id: Session to enroll students in
            create_user_accounts: Whether to create Django user accounts
            send_welcome_emails: Whether to send welcome emails
            imported_by_id: User ID performing the import
            batch_size: Number of records to process per transaction
            
        Returns:
            Tuple of (successful_imports, failed_imports)
        """
        # Validate batch size
        BulkOperationValidator.validate_batch_size(batch_size, cls.BATCH_SIZE * 10)
        
        # Get academic session
        if not academic_session_id:
            current_session = AcademicSessionSelector.get_current_session()
            if not current_session:
                raise ValidationError("No active academic session configured")
            academic_session_id = current_session.id
        
        successful = []
        failed = []
        
        # Read and parse CSV
        try:
            decoded_file = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            # Validate headers
            headers = reader.fieldnames or []
            BulkOperationValidator.validate_csv_headers(
                headers, 
                cls.REQUIRED_CSV_FIELDS
            )
            
            # Process in batches
            batch = []
            for row_num, row in enumerate(reader, start=2):
                batch.append((row_num, row))
                
                if len(batch) >= batch_size:
                    batch_success, batch_failed = cls._process_csv_batch(
                        batch, academic_session_id, create_user_accounts,
                        send_welcome_emails, imported_by_id
                    )
                    successful.extend(batch_success)
                    failed.extend(batch_failed)
                    batch = []
            
            # Process remaining records
            if batch:
                batch_success, batch_failed = cls._process_csv_batch(
                    batch, academic_session_id, create_user_accounts,
                    send_welcome_emails, imported_by_id
                )
                successful.extend(batch_success)
                failed.extend(batch_failed)
            
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            raise BulkOperationError(f"CSV import failed: {str(e)}")
        
        # Log bulk import
        SystemLogService.log_action(
            user_id=imported_by_id,
            action=SystemLog.ActionType.IMPORT,
            app_label=SystemLog.AppLabel.STUDENTS,
            model_name='Student',
            object_id='bulk',
            object_repr=f'Bulk import of {len(successful)} students',
            changes={
                'successful_count': len(successful),
                'failed_count': len(failed),
                'academic_session_id': academic_session_id,
                'create_user_accounts': create_user_accounts
            }
        )
        
        if failed:
            raise BulkOperationError(
                message=f"Imported {len(successful)} students with {len(failed)} failures",
                successful=successful,
                failed=failed
            )
        
        return successful, failed
    
    @classmethod
    def _process_csv_batch(
        cls,
        batch: List[Tuple[int, Dict]],
        academic_session_id: int,
        create_user_accounts: bool,
        send_welcome_emails: bool,
        imported_by_id: Optional[int]
    ) -> Tuple[List[Student], List[Dict[str, Any]]]:
        """
        Process a batch of CSV records.
        """
        successful = []
        failed = []
        
        for row_num, row in batch:
            try:
                with transaction.atomic():
                    # Get class ID
                    class_name = row.get('current_class')
                    student_class = StudentClassSelector.get_by_name(class_name)
                    
                    if not student_class:
                        raise ValidationError(f"Class '{class_name}' not found")
                    
                    # Prepare student data
                    student_data = {
                        'first_name': row['first_name'],
                        'last_name': row['last_name'],
                        'middle_name': row.get('middle_name', ''),
                        'date_of_birth': row['date_of_birth'],
                        'gender': row['gender'],
                        'current_class_id': student_class.id,
                        'email': row.get('email', ''),
                        'phone': row.get('phone', ''),
                        'address': row.get('address', ''),
                        'city': row.get('city', ''),
                        'state_of_origin': row.get('state_of_origin', ''),
                        'blood_group': row.get('blood_group', ''),
                        'medical_notes': row.get('medical_notes', ''),
                        'has_special_needs': row.get('has_special_needs', 'false').lower() == 'true',
                        'created_via': 'bulk_import',
                        'created_by_id': imported_by_id,
                    }
                    
                    # Create student
                    student = StudentService.create_from_admission(student_data)
                    
                    # Create user account if requested
                    if create_user_accounts and student.email:
                        try:
                            StudentUserService.create_user_for_student(
                                student=student,
                                send_welcome_email=send_welcome_emails,
                                created_by_id=imported_by_id
                            )
                        except Exception as e:
                            logger.warning(f"Failed to create user for student {student.id}: {e}")
                    
                    successful.append(student)
                    
            except Exception as e:
                failed.append({
                    'row': row_num,
                    'data': row,
                    'error': str(e)
                })
                logger.warning(f"Failed to import row {row_num}: {e}")
        
        return successful, failed
    
    @classmethod
    def generate_csv_template(cls) -> str:
        """
        Generate CSV template for student import.
        
        Returns:
            CSV string with headers and example row
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        headers = cls.REQUIRED_CSV_FIELDS + cls.OPTIONAL_CSV_FIELDS
        writer.writerow(headers)
        
        # Write example row
        example = [
            'John',                    # first_name
            'Doe',                    # last_name
            '2008-01-15',            # date_of_birth
            'M',                     # gender
            'SS1',                   # current_class
            'James',                 # middle_name (optional)
            'john.doe@school.edu',   # email (optional)
            '08012345678',           # phone (optional)
            '123 School Road',       # address (optional)
            'Lagos',                 # city (optional)
            'Lagos',                 # state_of_origin (optional)
            'O+',                    # blood_group (optional)
            'No known allergies',    # medical_notes (optional)
            'false',                 # has_special_needs (optional)
        ]
        writer.writerow(example)
        
        return output.getvalue()
    
    @staticmethod
    def export_students_to_csv(
        student_ids: List[int],
        fields: Optional[List[str]] = None
    ) -> str:
        """
        Export selected students to CSV format.
        
        Args:
            student_ids: List of student IDs to export
            fields: List of fields to include (defaults to all)
            
        Returns:
            CSV string
        """
        if not fields:
            fields = [
                'admission_number', 'first_name', 'last_name', 'middle_name',
                'gender', 'date_of_birth', 'email', 'phone', 'address',
                'city', 'state_of_origin', 'current_class__name',
                'status', 'enrollment_date'
            ]
        
        students = Student.objects.filter(id__in=student_ids).select_related(
            'current_class'
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(fields)
        
        # Write data
        for student in students:
            row = []
            for field in fields:
                if '__' in field:
                    # Handle related fields
                    rel_field = field.split('__')[1]
                    value = getattr(getattr(student, field.split('__')[0]), rel_field, '')
                else:
                    value = getattr(student, field, '')
                row.append(str(value) if value is not None else '')
            writer.writerow(row)
        
        return output.getvalue()
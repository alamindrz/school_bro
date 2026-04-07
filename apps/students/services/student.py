"""
Student Service Layer - ALL write operations for students
NO direct model manipulation in views. All mutations happen here.
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Dict, Any, Optional, List
import logging

from ..models import Student, Guardian, StudentHistory
from ..constants import StudentStatus, StudentCreationMethod
from ..interfaces import StudentDataContract

from apps.corecode.selectors import (
    AcademicSessionSelector, 
    AcademicTermSelector,
    StudentClassSelector
)
from apps.corecode.services import SystemLogService 
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class StudentService:
    """
    Student business operations.
    This is the ONLY place where Student objects are created/updated.
    """
    
    @classmethod
    @transaction.atomic
    def create_from_admission(cls, applicant_data: Dict[str, Any]) -> Student:
        """
        Create a student from admission application data.
        This is the ONLY entry point for converting applications to students.
        """
        from apps.corecode.selectors import StudentClassSelector
        
        # Create contract from dict
        contract = StudentDataContract(**applicant_data)
        contract.validate()
        
        # Get target class info (as dict, not model)
        target_class = StudentClassSelector.get_by_id(contract.current_class_id)
        class_label = target_class.get('name') if target_class else str(contract.current_class_id)
        
        # Generate admission number if not provided
        admission_number = contract.admission_number
        if not admission_number:
            from ..services.admission_number import AdmissionNumberService
            admission_number = AdmissionNumberService.generate_admission_number(
                class_name=class_label,
                session_code=None
            )


        # Get the academic session from the application data
        # The application was created with a specific session (from admissions period)
        enrollment_session_id = contract.enrollment_session_id if hasattr(contract, 'enrollment_session_id') else None
        
        # If not provided, get current session
        if not enrollment_session_id:
            from apps.corecode.selectors import AcademicSessionSelector
            current_session = AcademicSessionSelector.get_current_session()
            enrollment_session_id = current_session.id if current_session else None        
                
        
        # Create student (using class_id, not class object)

        student = Student.objects.create(
            first_name=contract.first_name,
            last_name=contract.last_name,
            middle_name=contract.middle_name or '',
            gender=contract.gender,
            date_of_birth=contract.date_of_birth,
            email=contract.email or '',
            phone=contract.phone or '',
            address=contract.address or '',
            city=contract.city or '',
            state_of_origin=contract.state_of_origin or '',
            nationality=contract.nationality or 'Nigerian',
            current_class_id=contract.current_class_id,
            admission_number=admission_number,
            enrollment_date=contract.enrollment_date or timezone.now().date(),
            enrollment_session_id=enrollment_session_id,  
            created_via=contract.created_via,
            created_by_id=contract.created_by_id,
            status='active'
        )

        # Create guardian if provided
        if contract.guardian_first_name and contract.guardian_last_name:
            from ..models import Guardian
            Guardian.objects.create(
                student=student,
                first_name=contract.guardian_first_name,
                last_name=contract.guardian_last_name,
                relationship=contract.guardian_relationship or 'guardian',
                phone=contract.guardian_phone or '',
                email=contract.guardian_email or '',
                address=contract.guardian_address or '',
                occupation=contract.guardian_occupation or '',
                is_primary=True,
                is_emergency_contact=True
            )
        
        logger.info(f"Student created from application {contract.application_number}: {admission_number}")
        return student


    
    @staticmethod
    @transaction.atomic
    def update_student_status(
        student_id: int,
        new_status: str,
        reason: str = "",
        performed_by_id: Optional[int] = None
    ) -> Student:
        """
        Update student status with validation and audit trail.
        """
        try:
            student = Student.objects.select_related('current_class').get(id=student_id)
        except Student.DoesNotExist:
            raise ValidationError(f"Student with id {student_id} not found")
        
        # Validate transition
        if not student.can_transition_to(new_status):
            raise ValidationError(
                f"Cannot transition from {student.status} to {new_status}"
            )
        
        old_status = student.status
        student.status = new_status
        student.save()
        
        # Record history
        StudentHistory.objects.create(
            student=student,
            academic_session=student.enrollment_session,
            term=1,  # TODO: Get current term from AcademicTermSelector
            class_at_time=student.current_class,
            status_at_time=new_status,
            action=f"STATUS_CHANGE_{old_status}_TO_{new_status}",
            notes=reason,
            performed_by_id=performed_by_id
        )
        
        # Log to system
        SystemLogService.log_action(
            user=performed_by_id,
            action=SystemLog.ActionType.UPDATE,
            app_label=SystemLog.AppLabel.STUDENTS,
            model_name='Student',
            object_id=str(student.id),
            object_repr=student.admission_number,
            changes={'old_status': old_status, 'new_status': new_status, 'reason': reason}
        )
        
        return student
    
    @staticmethod
    @transaction.atomic
    def transfer_student(
        student_id: int,
        new_class_id: int,
        academic_session_id: Optional[int] = None,
        performed_by_id: Optional[int] = None
    ) -> Student:
        """
        Transfer student to a new class (promotion or reclassification)
        """
        
        from apps.corecode.selectors import AcademicSessionSelector, StudentClassSelector
        
        student = Student.objects.get(id=student_id)
        new_class = StudentClassSelector.get_class_by_id(new_class_id)
        
        if not new_class:
            raise ValidationError("Target class not found")
        
        # Get current session if not specified
        if not academic_session_id:
            current_session = AcademicSessionSelector.get_current_session()
            academic_session_id = current_session.id if current_session else None
        
        old_class = student.current_class
        student.current_class_id = new_class_id
        student.save()
        
        # Record history
        StudentHistory.objects.create(
            student=student,
            academic_session_id=academic_session_id,
            term=1,  # TODO: Get current term
            class_at_time_id=new_class_id,
            status_at_time=student.status,
            action="PROMOTED" if old_class.sort_order < new_class.sort_order else "RECLASSIFIED",
            previous_class=old_class,
            notes=f"Transferred from {old_class.display_name} to {new_class.display_name}",
            performed_by_id=performed_by_id
        )
        
        # ✅ CORRECT: Log promotion using service
        SystemLogService.log_promotion(
            user=performed_by_id,
            student=student,
            from_class=old_class,
            to_class=new_class,
            academic_session_id=academic_session_id
        )
        
        return student
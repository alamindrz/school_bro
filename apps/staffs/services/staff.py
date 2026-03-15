"""
Staff Service - Core staff management business logic
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, Dict, Any, List
import logging

from ..models import Staff, Qualification, WorkExperience, StaffDocument, PerformanceEvaluation
from ..constants import EmploymentStatus, StaffCategory
from ..exceptions import (
    StaffNotFoundError, DuplicateStaffError,
    InvalidStatusTransitionError
)
from ..selectors import StaffSelector

from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class StaffService:
    """
    Staff business operations
    Single source of truth for staff management
    """
    @staticmethod
    @transaction.atomic
    def delete_document(
        document_id: int,
        deleted_by_id: Optional[int] = None
    ) -> bool:
        """
        Delete a staff document.
        
        Args:
            document_id: ID of document to delete
            deleted_by_id: User ID performing the deletion
            
        Returns:
            True if deleted successfully
            
        Raises:
            Exception: If document doesn't exist or deletion fails
        """
        try:
            # Get document to log before deletion
            from ..selectors import StaffDocumentSelector
            document = StaffDocumentSelector.get_by_id(document_id)
            
            if not document:
                raise ValueError(f"Document with id {document_id} not found")
            
            # Store info for logging
            doc_info = {
                'id': document_id,
                'staff_id': document['staff_id'],
                'title': document['title'],
                'document_type': document['document_type'],
                'file_name': document['file_name'],
            }
            
            # Delete the physical file if it exists
            from ..models import StaffDocument
            doc_obj = StaffDocument.objects.get(id=document_id)
            if doc_obj.file:
                if os.path.isfile(doc_obj.file.path):
                    os.remove(doc_obj.file.path)
            
            # Delete the database record
            deleted_count, _ = StaffDocument.objects.filter(id=document_id).delete()
            
            if deleted_count == 0:
                raise ValueError(f"Document with id {document_id} not found")
            
            # Log the deletion
            SystemLogService.log_action(
                user_id=deleted_by_id,
                action=SystemLog.ActionType.DELETE,
                app_label=SystemLog.AppLabel.STAFFS,
                model_name='StaffDocument',
                object_id=str(document_id),
                object_repr=doc_info['title'],
                changes={'deleted_document': doc_info}
            )
            
            logger.info(f"Document {document_id} deleted by user {deleted_by_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise    
        

    @staticmethod
    @transaction.atomic
    def create_staff(
        first_name: str,
        last_name: str,
        gender: str,
        date_of_birth: str,
        email: str,
        phone: str,
        address: str,
        city: str,
        state_of_origin: str,
        staff_type: str,
        date_employed: str,
        emergency_contact_name: str,
        emergency_contact_phone: str,
        emergency_contact_relationship: str,
        middle_name: str = '',
        marital_status: str = 'single',
        blood_group: str = '',
        alternate_phone: str = '',
        lga: str = '',
        nationality: str = 'Nigerian',
        employment_type: str = 'permanent',
        shift: str = 'fixed',
        department: str = '',
        unit: str = '',
        supervisor_id: Optional[int] = None,
        highest_qualification: str = 'degree',
        qualification_details: str = '',
        bank_name: str = '',
        account_number: str = '',
        account_name: str = '',
        pension_number: str = '',
        tax_id: str = '',
        medical_conditions: str = '',
        allergies: str = '',
        doctor_name: str = '',
        doctor_phone: str = '',
        created_by_id: Optional[int] = None
    ) -> Staff:
        """
        Create a new staff member
        """
        # Check for existing email
        if Staff.objects.filter(email=email).exists():
            raise DuplicateStaffError(f"Staff with email {email} already exists")

        # Parse dates
        from datetime import datetime
        dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
        employed_date = datetime.strptime(date_employed, '%Y-%m-%d').date()

        # Calculate retirement date (65 years old)
        retirement_date = date(dob.year + 65, dob.month, dob.day)

        # Create staff
        staff = Staff.objects.create(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            gender=gender,
            date_of_birth=dob,
            marital_status=marital_status,
            blood_group=blood_group,
            email=email,
            phone=phone,
            alternate_phone=alternate_phone,
            address=address,
            city=city,
            state_of_origin=state_of_origin,
            lga=lga,
            nationality=nationality,
            staff_type=staff_type,
            employment_status=EmploymentStatus.ACTIVE,
            employment_type=employment_type,
            shift=shift,
            date_employed=employed_date,
            retirement_date=retirement_date,
            department=department,
            unit=unit,
            supervisor_id=supervisor_id,
            highest_qualification=highest_qualification,
            qualification_details=qualification_details,
            bank_name=bank_name,
            account_number=account_number,
            account_name=account_name,
            pension_number=pension_number,
            tax_id=tax_id,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_phone=emergency_contact_phone,
            emergency_contact_relationship=emergency_contact_relationship,
            medical_conditions=medical_conditions,
            allergies=allergies,
            doctor_name=doctor_name,
            doctor_phone=doctor_phone,
            created_by_id=created_by_id
        )

        # Log creation
        SystemLogService.log_action(
            user_id=created_by_id,
            action=SystemLog.ActionType.CREATE,
            app_label=SystemLog.AppLabel.STAFFS,
            model_name='Staff',
            object_id=str(staff.id),
            object_repr=staff.staff_id,
            changes={
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'staff_type': staff_type,
            }
        )

        logger.info(f"Staff created: {staff.staff_id}")
        return staff

    @staticmethod
    @transaction.atomic
    def update_staff_status(
        staff_id: int,
        new_status: str,
        reason: str = "",
        updated_by_id: Optional[int] = None
    ) -> Staff:
        """
        Update staff employment status
        """
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            raise StaffNotFoundError(f"Staff with id {staff_id} not found")

        # Validate transition
        valid_transitions = StaffService._get_valid_status_transitions(staff.employment_status)
        if new_status not in valid_transitions:
            raise InvalidStatusTransitionError(
                f"Cannot transition from {staff.employment_status} to {new_status}"
            )

        old_status = staff.employment_status
        staff.employment_status = new_status
        staff.save(update_fields=['employment_status', 'updated_at'])

        # Log status change
        SystemLogService.log_action(
            user_id=updated_by_id,
            action=SystemLog.ActionType.UPDATE,
            app_label=SystemLog.AppLabel.STAFFS,
            model_name='Staff',
            object_id=str(staff.id),
            object_repr=staff.staff_id,
            changes={
                'status': f'{old_status} → {new_status}',
                'reason': reason
            }
        )

        logger.info(f"Staff {staff.staff_id} status updated: {old_status} → {new_status}")
        return staff

    @staticmethod
    @transaction.atomic
    def add_qualification(
        staff_id: int,
        qualification_type: str,
        title: str,
        institution: str,
        year_obtained: int,
        certificate_number: str = '',
        expiry_date: Optional[str] = None,
        document=None,
        added_by_id: Optional[int] = None
    ) -> Qualification:
        """
        Add qualification to staff record
        """
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            raise StaffNotFoundError(f"Staff with id {staff_id} not found")

        # Parse expiry date if provided
        expiry = None
        if expiry_date:
            from datetime import datetime
            expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()

        qualification = Qualification.objects.create(
            staff=staff,
            qualification_type=qualification_type,
            title=title,
            institution=institution,
            year_obtained=year_obtained,
            certificate_number=certificate_number,
            expiry_date=expiry,
            document=document,
        )

        logger.info(f"Qualification added for staff {staff.staff_id}")
        return qualification

    @staticmethod
    @transaction.atomic
    def add_performance_evaluation(
        staff_id: int,
        evaluator_id: int,
        evaluation_date: str,
        evaluation_period: str,
        punctuality: int,
        job_knowledge: int,
        quality_of_work: int,
        communication: int,
        teamwork: int,
        initiative: int,
        strengths: str = '',
        areas_for_improvement: str = '',
        overall_comments: str = '',
        recommendation: str = ''
    ) -> PerformanceEvaluation:
        """
        Add performance evaluation for staff
        """
        try:
            staff = Staff.objects.get(id=staff_id)
            evaluator = Staff.objects.get(id=evaluator_id)
        except Staff.DoesNotExist:
            raise StaffNotFoundError("Staff or evaluator not found")

        from datetime import datetime
        eval_date = datetime.strptime(evaluation_date, '%Y-%m-%d').date()

        evaluation = PerformanceEvaluation.objects.create(
            staff=staff,
            evaluator=evaluator,
            evaluation_date=eval_date,
            evaluation_period=evaluation_period,
            punctuality=punctuality,
            job_knowledge=job_knowledge,
            quality_of_work=quality_of_work,
            communication=communication,
            teamwork=teamwork,
            initiative=initiative,
            strengths=strengths,
            areas_for_improvement=areas_for_improvement,
            overall_comments=overall_comments,
            recommendation=recommendation
        )

        logger.info(f"Performance evaluation added for staff {staff.staff_id}")
        return evaluation

    @staticmethod
    def _get_valid_status_transitions(current_status: str) -> List[str]:
        """Get valid status transitions"""
        transitions = {
            EmploymentStatus.ACTIVE: [
                EmploymentStatus.ON_LEAVE,
                EmploymentStatus.SUSPENDED,
                EmploymentStatus.TERMINATED,
                EmploymentStatus.RESIGNED,
                EmploymentStatus.RETIRED
            ],
            EmploymentStatus.ON_LEAVE: [
                EmploymentStatus.ACTIVE,
                EmploymentStatus.SUSPENDED,
                EmploymentStatus.TERMINATED,
                EmploymentStatus.RESIGNED
            ],
            EmploymentStatus.PROBATION: [
                EmploymentStatus.ACTIVE,
                EmploymentStatus.TERMINATED,
                EmploymentStatus.RESIGNED
            ],
            EmploymentStatus.CONTRACT: [
                EmploymentStatus.ACTIVE,
                EmploymentStatus.TERMINATED,
                EmploymentStatus.RESIGNED
            ],
            EmploymentStatus.SUSPENDED: [
                EmploymentStatus.ACTIVE,
                EmploymentStatus.TERMINATED,
                EmploymentStatus.RESIGNED
            ],
            EmploymentStatus.TERMINATED: [],
            EmploymentStatus.RESIGNED: [],
            EmploymentStatus.RETIRED: [],
        }
        return transitions.get(current_status, [])
        
        
    @staticmethod
    @transaction.atomic
    def upload_document(
        staff_id: int,
        document_type: str,
        title: str,
        file,
        uploaded_by_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Upload document for a staff member.
        
        Args:
            staff_id: Staff ID
            document_type: Type from DOCUMENT_TYPES
            title: Document title
            file: Uploaded file object
            uploaded_by_id: User ID uploading the document
            
        Returns:
            Document data dictionary
            
        Raises:
            StaffNotFoundError: If staff doesn't exist
            ValidationError: If file is invalid
        """
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            raise StaffNotFoundError(f"Staff with id {staff_id} not found")
    
        # Validate file size (10MB limit)
        if file.size > 10 * 1024 * 1024:
            raise ValidationError("File size must be less than 10MB")
        
        # Validate file type
        allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in allowed_extensions:
            raise ValidationError(f"File type {ext} not allowed. Allowed: {', '.join(allowed_extensions)}")
    
        # Create document
        from ..models import StaffDocument
        document = StaffDocument.objects.create(
            staff=staff,
            document_type=document_type,
            title=title,
            file=file,
            uploaded_by_id=uploaded_by_id
        )
    
        # Log the action
        SystemLogService.log_action(
            user_id=uploaded_by_id,
            action=SystemLog.ActionType.CREATE,
            app_label=SystemLog.AppLabel.STAFFS,
            model_name='StaffDocument',
            object_id=str(document.id),
            object_repr=title,
            changes={
                'staff_id': staff_id,
                'document_type': document_type,
                'title': title,
                'file_size': file.size,
            }
        )
    
        logger.info(f"Document uploaded for staff {staff_id}")
        
        # Return data using selector
        from ..selectors import StaffDocumentSelector
        return StaffDocumentSelector.get_by_id(document.id)
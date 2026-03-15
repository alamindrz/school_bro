# school_bro/apps/admissions/services/applications.py
"""
Application Service - Core admissions business logic
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, Dict, Any, List
import logging

from ..models import Application, ApplicationNote, ApplicationReview
from ..constants import ApplicationStatus, DEFAULT_APPLICATION_FEE
from ..exceptions import (
    ApplicationNotFoundError,
    InvalidApplicationStatusError,
    DuplicateApplicationError,
    AdmissionsClosedError,
)
from ..validators import ApplicationValidator
from ..selectors import ApplicationSelector
from apps.corecode.services import SystemLogService, SiteConfigService
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector
from apps.corecode.models import SystemLog
from apps.corecode.constants import SiteConfigKey
from apps.students.services import StudentService  # The ONLY allowed import from students

logger = logging.getLogger(__name__)


class ApplicationService:
    """
    Application business operations
    Single source of truth for application management
    """
    
    @staticmethod
    @transaction.atomic
    def create_application(
        first_name: str,
        last_name: str,
        gender: str,
        date_of_birth: str,
        email: str,
        phone: str,
        address: str,
        city: str,
        state_of_origin: str,
        applying_for_class_id: int,
        guardian_first_name: str,
        guardian_last_name: str,
        guardian_relationship: str,
        guardian_phone: str,
        nationality: str = 'Nigerian',
        middle_name: str = '',
        alternate_phone: str = '',
        application_type: str = 'new',
        previous_school: str = '',
        previous_class: str = '',
        guardian_email: str = '',
        guardian_address: str = '',
        guardian_occupation: str = '',
        created_by_id: Optional[int] = None
    ) -> Application:
        """
        Create a new application
        
        CRITICAL: This is the ONLY entry point for creating applications
        """
        # Validate admissions are open
        ApplicationValidator.validate_admissions_open()
        
        # Get current session
        current_session = AcademicSessionSelector.get_current_session()
        if not current_session:
            raise ValidationError("No active academic session configured")
        
        # Check for duplicate
        ApplicationValidator.validate_duplicate_application(
            email=email,
            phone=phone,
            session_id=current_session.id
        )
        
        # Validate age for class
        from datetime import datetime
        dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
        ApplicationValidator.validate_applicant_age(dob, applying_for_class_id)
        
        # Check class availability
        ApplicationValidator.validate_class_availability(
            applying_for_class_id, 
            current_session.id
        )
        
        # Generate application number
        application_number = ApplicationService._generate_application_number()
        
        # Create application
        application = Application.objects.create(
            application_number=application_number,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            gender=gender,
            date_of_birth=dob,
            email=email,
            phone=phone,
            alternate_phone=alternate_phone,
            address=address,
            city=city,
            state_of_origin=state_of_origin,
            nationality=nationality,
            applying_for_class_id=applying_for_class_id,
            application_type=application_type,
            previous_school=previous_school,
            previous_class=previous_class,
            guardian_first_name=guardian_first_name,
            guardian_last_name=guardian_last_name,
            guardian_relationship=guardian_relationship,
            guardian_phone=guardian_phone,
            guardian_email=guardian_email,
            guardian_address=guardian_address,
            guardian_occupation=guardian_occupation,
            applying_for_session=current_session,
            status=ApplicationStatus.DRAFT,
            created_by_id=created_by_id
        )
        
        # Log creation
        SystemLogService.log_action(
            user_id=created_by_id,
            action=SystemLog.ActionType.CREATE,
            app_label=SystemLog.AppLabel.ADMISSIONS,
            model_name='Application',
            object_id=str(application.id),
            object_repr=application.application_number,
            changes={
                'first_name': first_name,
                'last_name': last_name,
                'applying_for_class': applying_for_class_id,
            }
        )
        
        logger.info(f"Application created: {application.application_number}")
        return application
    
    @staticmethod
    @transaction.atomic
    def submit_application(
        application_id: int,
        submitted_by_id: Optional[int] = None
    ) -> Application:
        """
        Submit an application for review
        """
        try:
            application = Application.objects.get(id=application_id)
        except Application.DoesNotExist:
            raise ApplicationNotFoundError(f"Application {application_id} not found")
        
        # Validate status transition
        if not application.can_transition_to(ApplicationStatus.SUBMITTED):
            raise InvalidApplicationStatusError(
                from_status=application.status,
                to_status=ApplicationStatus.SUBMITTED
            )
        
        # Validate required fields are complete
        ApplicationService._validate_completeness(application)
        
        # Update status
        old_status = application.status
        application.status = ApplicationStatus.SUBMITTED
        application.submitted_at = timezone.now()
        application.save(update_fields=['status', 'submitted_at', 'updated_at'])
        
        # Create review record
        ApplicationReview.objects.create(
            application=application,
            from_status=old_status,
            to_status=ApplicationStatus.SUBMITTED,
            notes="Application submitted by applicant",
            reviewed_by_id=submitted_by_id
        )
        
        # Log action
        SystemLogService.log_action(
            user_id=submitted_by_id,
            action=SystemLog.ActionType.UPDATE,
            app_label=SystemLog.AppLabel.ADMISSIONS,
            model_name='Application',
            object_id=str(application.id),
            object_repr=application.application_number,
            changes={'status': f'{old_status} → {ApplicationStatus.SUBMITTED}'}
        )
        
        logger.info(f"Application submitted: {application.application_number}")
        return application
    
    @staticmethod
    @transaction.atomic
    def review_application(
        application_id: int,
        new_status: str,
        review_notes: str = '',
        reviewed_by_id: Optional[int] = None
    ) -> Application:
        """
        Review an application (approve/reject/waitlist)
        """
        try:
            application = Application.objects.select_related(
                'applying_for_class', 'applying_for_session'
            ).get(id=application_id)
        except Application.DoesNotExist:
            raise ApplicationNotFoundError(f"Application {application_id} not found")
        
        # Validate status transition
        if not application.can_transition_to(new_status):
            raise InvalidApplicationStatusError(
                from_status=application.status,
                to_status=new_status
            )
        
        # If approving, check class capacity again
        if new_status == ApplicationStatus.APPROVED:
            ApplicationValidator.validate_class_availability(
                application.applying_for_class_id,
                application.applying_for_session_id
            )
        
        # Update application
        old_status = application.status
        application.status = new_status
        application.reviewed_by_id = reviewed_by_id
        application.reviewed_at = timezone.now()
        application.review_notes = review_notes
        application.save(update_fields=[
            'status', 'reviewed_by', 'reviewed_at', 'review_notes', 'updated_at'
        ])
        
        # Create review record
        ApplicationReview.objects.create(
            application=application,
            from_status=old_status,
            to_status=new_status,
            notes=review_notes,
            reviewed_by_id=reviewed_by_id
        )
        
        # If approved, set expiry
        if new_status == ApplicationStatus.APPROVED:
            from .payment import PaymentService
            PaymentService.create_payment_record(application)
        
        # Log action
        SystemLogService.log_action(
            user_id=reviewed_by_id,
            action=SystemLog.ActionType.UPDATE,
            app_label=SystemLog.AppLabel.ADMISSIONS,
            model_name='Application',
            object_id=str(application.id),
            object_repr=application.application_number,
            changes={
                'status': f'{old_status} → {new_status}',
                'review_notes': review_notes
            }
        )
        
        logger.info(f"Application {application.application_number} reviewed: {new_status}")
        return application
    
    @staticmethod
    def _generate_application_number() -> str:
        """
        Generate unique application number
        Format: APP-{YEAR}-{SEQUENCE:04d}
        """
        from django.db.models import Max
        
        year = timezone.now().year
        prefix = f"APP-{year}"
        
        last_app = Application.objects.filter(
            application_number__startswith=prefix
        ).aggregate(Max('application_number'))
        
        if last_app['application_number__max']:
            last_sequence = int(last_app['application_number__max'].split('-')[-1])
            new_sequence = last_sequence + 1
        else:
            new_sequence = 1
        
        return f"{prefix}-{new_sequence:04d}"
    
    @staticmethod
    def _validate_completeness(application: Application):
        """
        Validate that all required fields are filled before submission
        """
        required_fields = [
            'first_name', 'last_name', 'gender', 'date_of_birth',
            'email', 'phone', 'address', 'city', 'state_of_origin',
            'guardian_first_name', 'guardian_last_name',
            'guardian_relationship', 'guardian_phone'
        ]
        
        missing = []
        for field in required_fields:
            if not getattr(application, field):
                missing.append(field)
        
        if missing:
            raise ValidationError(
                f"Missing required fields: {', '.join(missing)}"
            )
        
        # Check if payment is completed
        if not hasattr(application, 'payment') or application.payment.status != 'completed':
            raise ValidationError("Application fee must be paid before submission")
    
    @staticmethod
    def add_note(
        application_id: int,
        note: str,
        created_by_id: Optional[int] = None
    ) -> ApplicationNote:
        """
        Add an internal note to an application
        """
        try:
            application = Application.objects.get(id=application_id)
        except Application.DoesNotExist:
            raise ApplicationNotFoundError(f"Application {application_id} not found")
        
        note_obj = ApplicationNote.objects.create(
            application=application,
            note=note,
            created_by_id=created_by_id
        )
        
        logger.info(f"Note added to application {application.application_number}")
        return note_obj
    
    @staticmethod
    def is_admissions_open() -> bool:
        """Check if admissions are currently open"""
        try:
            ApplicationValidator.validate_admissions_open()
            return True
        except (AdmissionsClosedError, DeadlineExceededError):
            return False
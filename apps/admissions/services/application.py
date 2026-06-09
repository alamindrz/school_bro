# school_bro/apps/admissions/services/application.py
"""
Application Service - Core admissions business logic
"""

from django.db import transaction
from django.db import models as django_models
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, Dict, Any, List
from decimal import Decimal
import logging

from ..models import Application, ApplicationNote, ApplicationReview, AdmissionsPeriod
from ..constants import ApplicationStatus
from ..exceptions import (
    ApplicationNotFoundError,
    InvalidApplicationStatusError,
    DuplicateApplicationError,
    AdmissionsClosedError,
    DeadlineExceededError,
)
from ..validators import ApplicationValidator
from ..selectors import ApplicationSelector, AdmissionsPeriodSelector
from apps.corecode.services import SystemLogService, SiteConfigService
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector
from apps.corecode.models import SystemLog
from apps.corecode.constants import SiteConfigKey

# Import finance services for invoice handling
from apps.finance.services import InvoiceService
from apps.finance.constants import FeeType

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
        applying_for_class_id: int,
        guardian_first_name: str,
        guardian_last_name: str,
        guardian_relationship: str,
        guardian_phone: str,
        state_of_origin: str,
        email: str = '',
        phone: str = '',
        address: str = '',
        city: str = '',
        nationality: str = 'Nigerian',
        middle_name: str = '',
        alternate_phone: str = '',
        application_type: str = 'new',
        previous_school: str = '',
        previous_class: str = '',
        guardian_email: str = '',
        guardian_address: str = '',
        guardian_occupation: str = '',
        created_by_id: Optional[int] = None,
        skip_invoice: bool = False
    ) -> Application:
        """
        Create a new application
        
        CRITICAL: This is the ONLY entry point for creating applications
        
        All required parameters come first, optional parameters with defaults come last.
        
        Args:
            skip_invoice: If True, don't create an invoice (for staff-created applications)
        """
        # STEP 1: Validate admissions are open and get current period
        try:
            current_period = AdmissionsPeriodSelector.get_current_period()
            
            if not current_period:
                raise AdmissionsClosedError(
                    "No active admissions period found. Please check back later."
                )
            
            # Store period info for later use
            period_id = current_period['id']
            period_name = current_period['name']
            period_start = current_period['start_date']
            period_end = current_period.get('end_date')
            application_fee = current_period['application_fee']
            admissions_session_id = current_period['academic_session']['id']
            
            logger.info(f"Creating application for admissions period: {period_name}")
            
        except Exception as e:
            logger.error(f"Failed to get admissions period: {e}")
            raise AdmissionsClosedError("Admissions are currently closed.")
        
        # STEP 2: Get the academic session from the admissions period
        
        try:
            admissions_session = AcademicSessionSelector.get_by_id(admissions_session_id)
            if not admissions_session:
                raise ValidationError(
                    f"Admissions period '{period_name}' is linked to an invalid academic session."
                )
        except Exception as e:
            logger.error(f"Failed to get academic session: {e}")
            raise ValidationError(f"Invalid academic session configuration: {str(e)}")        
        
        
        
        # STEP 3: Validate age for class
        try:
            from datetime import datetime
            dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            ApplicationValidator.validate_applicant_age(dob, applying_for_class_id)
        except Exception as e:
            logger.error(f"Age validation failed: {e}")
            raise ValidationError(f"Age validation failed: {str(e)}")
        
        # STEP 4: Check class availability
        try:
            ApplicationValidator.validate_class_availability(
                applying_for_class_id, 
                admissions_session_id
            )
        except Exception as e:
            logger.error(f"Class availability check failed: {e}")
            raise
        
        # STEP 5: Check for duplicate applications (only if email or phone provided)
        if email or phone:
            try:
                ApplicationValidator.validate_duplicate_application(
                    email=email if email else None,
                    phone=phone if phone else None,
                    session_id=admissions_session_id
                )
            except DuplicateApplicationError as e:
                logger.warning(f"Duplicate application detected: {e}")
                raise
        
        # STEP 6: Generate unique application number
        application_number = ApplicationService._generate_application_number()
        
        # STEP 7: Create the application record
        try:
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
                applying_for_session_id=admissions_session_id,  # Use session from admissions period
                status=ApplicationStatus.DRAFT,
                created_by_id=created_by_id
            )
            
            logger.info(f"Application created: {application.application_number}")
            
        except Exception as e:
            logger.error(f"Failed to create application record: {e}")
            raise ValidationError(f"Failed to create application: {str(e)}")
        
        # STEP 8: Create invoice in finance app for application fee (skip if requested)

        if not skip_invoice:
            try:
                # Get student class for display
                student_class = StudentClassSelector.get_by_id(applying_for_class_id)
                class_name = student_class.get('display_name') if student_class else "Unknown"
                
                invoice = InvoiceService.create_invoice(
                    student_id=None,  # No student yet - this is for application
                    student_name=f"{last_name} {first_name}",
                    class_id=applying_for_class_id,
                    fee_type=FeeType.APPLICATION,
                    amount=Decimal(str(application_fee)),
                    description=f"Application Fee - {application_number} ({period_name})",
                    session_id=admissions_session_id,
                    term_id=None,  # One-time fee, not term-specific
                    created_by_id=created_by_id
                )
                
                # Link application to invoice
                application.invoice_id = invoice.id
                application.save(update_fields=['invoice_id'])
                
                logger.info(f"Invoice {invoice.invoice_number} created for application {application_number}")
                
            except Exception as e:
                # Log but don't fail - invoice can be created later
                logger.warning(f"Failed to create invoice for application {application_number}: {e}")
        else:
            logger.info(f"Skipping invoice creation for staff-created application {application_number}")
        
        # Auto-submit staff applications (moved outside the else block)
        if skip_invoice:
            try:
                ApplicationService.submit_application(
                    application_id=application.id,
                    submitted_by_id=created_by_id
                )
                logger.info(f"Staff application {application.application_number} auto-submitted")
            except Exception as e:
                logger.warning(f"Failed to auto-submit staff application {application.application_number}: {e}")
        
        # STEP 9: Increment application count for the admissions period
        try:
            AdmissionsPeriod.objects.filter(id=period_id).update(
                current_applications=django_models.F('current_applications') + 1
            )
            logger.info(f"Incremented application count for period {period_name}")
        except Exception as e:
            logger.warning(f"Failed to increment period application count: {e}")
        
        # STEP 10: Log the creation
        if created_by_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=created_by_id)
                SystemLogService.log_action(
                    user=user,
                    action=SystemLog.ActionType.CREATE,
                    app_label=SystemLog.AppLabel.ADMISSIONS,
                    model_name='Application',
                    object_id=str(application.id),
                    object_repr=application.application_number,
                    changes={
                        'first_name': first_name,
                        'last_name': last_name,
                        'applying_for_class': applying_for_class_id,
                        'admissions_period': period_name,
                        'academic_session': admissions_session.get('name') if admissions_session else None,
                    },
                    ip_address='',
                    user_agent=''
                )
            except User.DoesNotExist:
                logger.warning(f"User {created_by_id} not found for logging")
            except Exception as e:
                logger.warning(f"Failed to log application creation: {e}")
        
        logger.info(
            f"Application {application.application_number} created successfully "
            f"for period: {period_name}, session: {admissions_session.name if admissions_session else 'N/A'}"
        )
        
        return application
    
    @staticmethod
    @transaction.atomic
    def submit_application(
        application_id: int,
        submitted_by_id: Optional[int] = None
    ) -> Application:
        """
        Submit an application for review
        
        Requires payment to be completed before submission (unless no invoice)
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
        
        # Validate payment is completed (only if invoice exists)
        if application.invoice_id and not application.payment_completed:
            raise ValidationError("Application fee must be paid before submission")
        
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
        if submitted_by_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=submitted_by_id)
                SystemLogService.log_action(
                    user=user,
                    action=SystemLog.ActionType.UPDATE,
                    app_label=SystemLog.AppLabel.ADMISSIONS,
                    model_name='Application',
                    object_id=str(application.id),
                    object_repr=application.application_number,
                    changes={'status': f'{old_status} → {ApplicationStatus.SUBMITTED}'},
                    ip_address='',
                    user_agent=''
                )
            except User.DoesNotExist:
                logger.warning(f"Audit log skipped: User {submitted_by_id} not found for application {application.application_number}")
        
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
        
        # Log action
        if reviewed_by_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=reviewed_by_id)
                SystemLogService.log_action(
                    user=user,
                    action=SystemLog.ActionType.UPDATE,
                    app_label=SystemLog.AppLabel.ADMISSIONS,
                    model_name='Application',
                    object_id=str(application.id),
                    object_repr=application.application_number,
                    changes={
                        'status': f'{old_status} → {new_status}',
                        'review_notes': review_notes
                    },
                    ip_address='',
                    user_agent=''
                )
            except User.DoesNotExist:
                logger.warning(f"Audit log skipped: User {reviewed_by_id} not found for application {application.application_number}")
        
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
        
        NOTE: Contact fields (email, phone, address, city) are NOT required
        because students may not have personal contact details.
        Guardian contact is the primary contact method.
        """
        required_fields = [
            'first_name', 'last_name', 'gender', 'date_of_birth',
            'state_of_origin',
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
            current_period = AdmissionsPeriodSelector.get_current_period()
            return current_period is not None
        except Exception:
            return False
"""
Admissions Validators - Pure validation functions
"""

import re
from datetime import date
from typing import Optional, List
from django.core.exceptions import ValidationError

from .constants import ApplicationStatus, DocumentType
from .exceptions import (
    AdmissionsClosedError,
    DeadlineExceededError,
    DuplicateApplicationError,
    DocumentTypeError,
    DocumentSizeError,
    ClassFullError,
)
from apps.corecode.selectors import SiteConfigSelector, StudentClassSelector
from apps.corecode.constants import SiteConfigKey
from apps.students.validators import StudentValidator  # Reuse student validators


class ApplicationValidator:
    """Validate application data"""
    
    MAX_DOCUMENT_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_DOCUMENT_TYPES = ['pdf', 'jpg', 'jpeg', 'png']
    
    @classmethod
    def validate_admissions_open(cls):
        """Check if admissions are currently open using AdmissionsPeriod"""
        from .selectors import AdmissionsPeriodSelector
        
        current_period = AdmissionsPeriodSelector.get_current_period()
        
        if not current_period:
            raise AdmissionsClosedError(
                "No active admissions period found. Please check back later."
            )
        
        # Also check if we're within the period dates
        now = timezone.now()
        start_date = datetime.fromisoformat(current_period['start_date'])
        end_date = datetime.fromisoformat(current_period['end_date']) if current_period['end_date'] else None
        
        if now < start_date:
            raise AdmissionsClosedError(
                f"Admissions for {current_period['name']} will open on "
                f"{start_date.strftime('%B %d, %Y')}"
            )
        
        if end_date and now > end_date:
            raise AdmissionsClosedError(
                f"Admissions period '{current_period['name']}' closed on "
                f"{end_date.strftime('%B %d, %Y')}"
            )
        
        if not current_period.get('has_capacity', True):
            raise AdmissionsClosedError(
                f"The {current_period['name']} admissions period has reached its maximum capacity."
            )
        
        # Store the current period info for later use (like application_fee)
        cls.current_admission_period = current_period
    
    
    
    @classmethod
    def validate_duplicate_application(cls, email: str, phone: str, session_id: int):
        """
        Check for existing active application with same email/phone
        """
        from .models import Application
        from .constants import ApplicationStatus
        
        if email:
            existing = Application.objects.filter(
                email=email,
                applying_for_session_id=session_id,
                status__in=ApplicationStatus.ACTIVE_STATES
            ).exists()
            
            if existing:
                raise DuplicateApplicationError(
                    "An active application already exists for this email address"
                )
        
        if phone:
            existing_phone = Application.objects.filter(
                phone=phone,
                applying_for_session_id=session_id,
                status__in=ApplicationStatus.ACTIVE_STATES
            ).exists()
            
            if existing_phone:
                raise DuplicateApplicationError(
                    "An active application already exists for this phone number"
                )
    
    @classmethod
    def validate_class_availability(cls, class_id: int, session_id: int):
        """
        Check if target class has capacity for new applications
        """
        from .models import Application
        from apps.students.models import Student
        
        student_class = StudentClassSelector.get_by_id(class_id)
        if not student_class:
            raise ValidationError(f"Class with id {class_id} not found")
        
        # Get max_students from dict - FIXED for dict return type
        max_students = student_class.get('max_students', 40)
        class_name = student_class.get('display_name', 'Unknown')
        
        # Count existing approved applications
        approved_count = Application.objects.filter(
            applying_for_class_id=class_id,
            applying_for_session_id=session_id,
            status__in=[ApplicationStatus.APPROVED, ApplicationStatus.ENROLLED]
        ).count()
        
        # Count existing enrolled students
        enrolled_students = Student.objects.filter(
            current_class_id=class_id,
            status='active'
        ).count()
        
        total_taken = approved_count + enrolled_students
        
        if total_taken >= max_students:
            raise ClassFullError(
                f"{class_name} has reached maximum capacity "
                f"({max_students} students)"
            )
    
    @classmethod
    def validate_applicant_age(cls, date_of_birth: date, class_id: int):
        """
        Validate age is appropriate for target class
        """
        student_class = StudentClassSelector.get_by_id(class_id)
        if student_class:
            age = (date.today() - date_of_birth).days // 365
            # Get class name from dict - FIXED for dict return type
            class_name = student_class.get('name', '')
            StudentValidator.validate_class_for_age(class_name, age)


class DocumentValidator:
    """Validate uploaded documents"""
    
    @classmethod
    def validate_document_type(cls, file_extension: str):
        """Validate file extension"""
        if file_extension.lower() not in cls.ALLOWED_DOCUMENT_TYPES:
            raise DocumentTypeError(
                f"Invalid file type. Allowed: {', '.join(cls.ALLOWED_DOCUMENT_TYPES)}"
            )
    
    @classmethod
    def validate_file_size(cls, file_size: int):
        """Validate file size"""
        if file_size > cls.MAX_DOCUMENT_SIZE:
            size_mb = cls.MAX_DOCUMENT_SIZE / (1024 * 1024)
            raise DocumentSizeError(f"File size exceeds maximum of {size_mb}MB")
    
    @classmethod
    def validate_document_type_for_application(cls, doc_type: str, application_type: str):
        """
        Validate document type is appropriate for application type
        """
        required_for_new = ['passport', 'birth_certificate']
        required_for_transfer = ['passport', 'birth_certificate', 'transfer_certificate', 'report_card']
        
        if application_type == 'new' and doc_type in required_for_new:
            return True
        elif application_type == 'transfer' and doc_type in required_for_transfer:
            return True
        elif doc_type == 'other':
            return True
        
        raise DocumentTypeError(f"Document type not required for {application_type} applications")
        

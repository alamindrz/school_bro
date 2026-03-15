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
        """Check if admissions are currently open"""
        is_open = SiteConfigSelector.get_config_value(
            SiteConfigKey.ADMISSIONS_OPEN, 
            False
        )
        if not is_open:
            raise AdmissionsClosedError("Admissions are currently closed")
        
        # Check deadline
        deadline = SiteConfigSelector.get_config_value(
            SiteConfigKey.ADMISSION_DEADLINE,
            None
        )
        if deadline:
            try:
                from datetime import datetime
                deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                if date.today() > deadline_date:
                    raise DeadlineExceededError(
                        f"Application deadline of {deadline_date} has passed"
                    )
            except (ValueError, TypeError):
                pass  # Invalid deadline format, ignore
    
    @classmethod
    def validate_duplicate_application(cls, email: str, phone: str, session_id: int):
        """
        Check for existing active application with same email/phone
        """
        from .models import Application
        from .constants import ApplicationStatus
        
        existing = Application.objects.filter(
            email=email,
            applying_for_session_id=session_id,
            status__in=ApplicationStatus.ACTIVE_STATES
        ).exists()
        
        if existing:
            raise DuplicateApplicationError(
                "An active application already exists for this email address"
            )
        
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
        
        # Count existing approved applications
        approved_count = Application.objects.filter(
            applying_for_class_id=class_id,
            applying_for_session_id=session_id,
            status__in=[ApplicationStatus.APPROVED, ApplicationStatus.ENROLLED]
        ).count()
        
        # Count existing enrolled students
        enrolled_students = Student.objects.filter(
            current_class_id=class_id,
            enrollment_session_id=session_id,
            status='active'
        ).count()
        
        total_taken = approved_count + enrolled_students
        
        if total_taken >= student_class.max_students:
            raise ClassFullError(
                f"{student_class.display_name} has reached maximum capacity "
                f"({student_class.max_students} students)"
            )
    
    @classmethod
    def validate_applicant_age(cls, date_of_birth: date, class_id: int):
        """
        Validate age is appropriate for target class
        """
        student_class = StudentClassSelector.get_by_id(class_id)
        if student_class:
            age = (date.today() - date_of_birth).days // 365
            StudentValidator.validate_class_for_age(student_class.name, age)


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
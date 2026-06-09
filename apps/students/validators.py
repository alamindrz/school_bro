"""
Student Data Validators
Pure validation functions - NO model imports
DEPENDS ON: students/exceptions.py
"""

import re
from datetime import date, datetime
from typing import Optional, Dict, Any, List, Union
from django.utils.translation import gettext_lazy as _

from apps.corecode.constants import NigerianClassLevel
from apps.shared.validators import (
    NIGERIAN_PHONE_PATTERN,
    EMAIL_PATTERN,
    validate_status_transition as _shared_validate_status_transition,
    validate_csv_headers as _shared_validate_csv_headers,
    validate_batch_size as _shared_validate_batch_size,
    validate_date_of_birth as _shared_validate_dob,
)
from .exceptions import (
    StudentValidationError,
    AdmissionNumberFormatError,
    AdmissionNumberCollisionError,
    InvalidStatusTransitionError,
    GuardianLimitExceededError,
    PrimaryGuardianRequiredError,
    BulkOperationError,
)


class StudentValidator:
    """Validator for student data - PURE FUNCTIONS, no DB calls"""
    
    # Regular expressions
    ADMISSION_NUMBER_PATTERN = re.compile(r'^\d{2,20}/[A-Z0-9]{2,10}/\d{3,5}$')

    PHONE_PATTERN = NIGERIAN_PHONE_PATTERN
    EMAIL_PATTERN = EMAIL_PATTERN
    
    @classmethod
    def validate_admission_number_format(cls, admission_number: str) -> bool:
        """
        Validate admission number format: YYYY/CLASS/SEQUENCE
        Example: 2024/SS1/001
        """
        if not admission_number:
            raise AdmissionNumberFormatError("Admission number cannot be empty")
        
        if not cls.ADMISSION_NUMBER_PATTERN.match(admission_number):
            raise AdmissionNumberFormatError(
                f"Invalid admission number format: {admission_number}. "
                "Expected format: YYYY/CLASS/SEQUENCE (e.g., 2024/SS1/001)"
            )
        return True
    
    @classmethod
    def validate_email(cls, email: Optional[str]) -> Optional[bool]:
        """Validate email format if provided"""
        if not email:
            return None
        if not cls.EMAIL_PATTERN.match(email):
            raise StudentValidationError(
                message=f"Invalid email format: {email}",
                field_errors={'email': ['Enter a valid email address']}
            )
        return True
    
    @classmethod
    def validate_phone(cls, phone: Optional[str]) -> Optional[bool]:
        """Validate Nigerian phone number if provided"""
        if not phone:
            return None
        if not cls.PHONE_PATTERN.match(phone):
            raise StudentValidationError(
                message=f"Invalid phone number format: {phone}. "
                       "Expected: 08012345678 or +2348012345678",
                field_errors={'phone': ['Enter a valid Nigerian phone number']}
            )
        return True
    
    @classmethod
    def validate_date_of_birth(cls, dob: Union[str, date], min_age: int = 2, max_age: int = 25) -> date:
        """Validate date of birth and calculate age.

        Delegates core logic to ``apps.shared.validators.validate_date_of_birth``
        and wraps any ``ValidationError`` in the app-specific
        ``StudentValidationError``.
        """
        from django.core.exceptions import ValidationError
        try:
            return _shared_validate_dob(dob, min_age=min_age, max_age=max_age)
        except ValidationError as exc:
            raise StudentValidationError(
                message=str(exc.message if hasattr(exc, 'message') else exc),
                field_errors={'date_of_birth': [str(exc.message if hasattr(exc, 'message') else exc)]}
            )
    
    @classmethod
    def validate_class_for_age(cls, student_class_name: str, age: int) -> bool:
        """
        Validate that student age is appropriate for class level
        Nigerian standard age guidelines:
        - Nursery: 3-5 years
        - Primary: 6-11 years
        - JSS: 12-14 years
        - SSS: 15-17 years
        """
        age_ranges = {
            # Nursery
            NigerianClassLevel.NURSERY_1: (3, 4),
            NigerianClassLevel.NURSERY_2: (4, 5),
            NigerianClassLevel.NURSERY_3: (5, 6),
            # Primary
            NigerianClassLevel.PRIMARY_1: (6, 7),
            NigerianClassLevel.PRIMARY_2: (7, 8),
            NigerianClassLevel.PRIMARY_3: (8, 9),
            NigerianClassLevel.PRIMARY_4: (9, 10),
            NigerianClassLevel.PRIMARY_5: (10, 11),
            NigerianClassLevel.PRIMARY_6: (11, 12),
            # JSS
            NigerianClassLevel.JSS_1: (12, 13),
            NigerianClassLevel.JSS_2: (13, 14),
            NigerianClassLevel.JSS_3: (14, 15),
            # SSS
            NigerianClassLevel.SS_1: (15, 16),
            NigerianClassLevel.SS_2: (16, 17),
            NigerianClassLevel.SS_3: (17, 18),
        }
        
        expected_range = age_ranges.get(student_class_name)
        if expected_range:
            min_expected, max_expected = expected_range
            if age < min_expected or age > max_expected:
                raise StudentValidationError(
                    message=f"Age {age} is outside expected range ({min_expected}-{max_expected}) for this class",
                    field_errors={'date_of_birth': [f'Expected age: {min_expected}-{max_expected} years']}
                )
        return True
    
    @classmethod
    def validate_status_transition(cls, current_status: str, new_status: str) -> bool:
        """Validate student status transition"""
        from .constants import StudentStatus
        return _shared_validate_status_transition(
            current_status, new_status,
            StudentStatus.VALID_TRANSITIONS,
            error_class=InvalidStatusTransitionError,
        )


class GuardianValidator:
    """Validator for guardian data"""
    
    MAX_GUARDIANS_PER_STUDENT = 5
    MAX_PRIMARY_GUARDIANS = 2
    
    @classmethod
    def validate_guardian_limit(cls, current_count: int) -> bool:
        """Validate guardian count per student"""
        if current_count >= cls.MAX_GUARDIANS_PER_STUDENT:
            raise GuardianLimitExceededError(
                f"Maximum {cls.MAX_GUARDIANS_PER_STUDENT} guardians allowed per student"
            )
        return True
    
    @classmethod
    def validate_primary_guardian_count(cls, current_primary_count: int, is_primary: bool) -> bool:
        """Validate primary guardian count"""
        new_count = current_primary_count + (1 if is_primary else 0)
        if new_count > cls.MAX_PRIMARY_GUARDIANS:
            raise PrimaryGuardianRequiredError(
                f"Maximum {cls.MAX_PRIMARY_GUARDIANS} primary guardians allowed"
            )
        return True
    
    @classmethod
    def validate_relationship(cls, relationship: str) -> bool:
        """Validate guardian relationship"""
        from .constants import GuardianRelationship
        
        valid_relationships = [r[0] for r in GuardianRelationship.CHOICES]
        if relationship not in valid_relationships:
            raise StudentValidationError(
                message=f"Invalid relationship: {relationship}",
                field_errors={'relationship': [f'Must be one of: {", ".join(valid_relationships)}']}
            )
        return True


class BulkOperationValidator:
    """Validator for bulk operations — delegates to shared helpers."""

    @classmethod
    def validate_csv_headers(cls, headers: List[str], required_fields: List[str]) -> bool:
        from django.core.exceptions import ValidationError
        try:
            return _shared_validate_csv_headers(headers, required_fields)
        except ValidationError as exc:
            raise BulkOperationError(message=str(exc.message if hasattr(exc, 'message') else exc))

    @classmethod
    def validate_batch_size(cls, batch_size: int, max_batch: int = 1000) -> bool:
        from django.core.exceptions import ValidationError
        try:
            return _shared_validate_batch_size(batch_size, max_batch)
        except ValidationError as exc:
            raise BulkOperationError(message=str(exc.message if hasattr(exc, 'message') else exc))
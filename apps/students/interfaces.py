"""
THE CONTRACT LAYER
Defines how other apps are allowed to talk to the Students app.
NO model imports here. Pure interface definitions.

Other apps MUST use these service calls. No direct model access.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from django.utils import timezone


@dataclass
class StudentDataContract:
    """
    Data contract for creating/updating students.
    Other apps must provide data in this exact format.
    """
    # Required fields
    first_name: str
    last_name: str
    date_of_birth: str
    current_class_id: int
    gender: str
    
    # Optional fields
    middle_name: Optional[str] = None
    admission_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None  # ADDED
    state_of_origin: Optional[str] = None  # ADDED
    nationality: Optional[str] = 'Nigerian'  # ADDED
    enrollment_date: Optional[str] = None
    
    # Guardian info (for creating guardian alongside student)
    guardian_first_name: Optional[str] = None  # ADDED
    guardian_last_name: Optional[str] = None  # ADDED
    guardian_relationship: Optional[str] = None  # ADDED
    guardian_phone: Optional[str] = None  # ADDED
    guardian_email: Optional[str] = None  # ADDED
    guardian_address: Optional[str] = None  # ADDED
    guardian_occupation: Optional[str] = None  # ADDED
    
    # Academic context
    enrollment_session_id: Optional[int] = None  # ADD THIS
    
    
    # Metadata (set by caller)
    created_via: str = 'admission'
    created_by_id: Optional[int] = None
    application_id: Optional[int] = None  # ADDED
    application_number: Optional[str] = None  # ADDED
    
    def validate(self) -> bool:
        """Basic validation of required fields"""
        required_fields = ['first_name', 'last_name', 'date_of_birth', 'current_class_id', 'gender']
        for field in required_fields:
            if not getattr(self, field):
                raise ValueError(f"Missing required field: {field}")
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for service layer"""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class GuardianDataContract:
    """Contract for guardian data"""
    
    first_name: str
    last_name: str
    relationship: str
    phone: str
    
    email: Optional[str] = None
    address: Optional[str] = None
    occupation: Optional[str] = None
    is_primary: bool = True


class StudentServiceInterface:
    """
    Interface that other apps must use.
    NEVER import models directly - always call these methods.
    """
    
    @staticmethod
    def create_from_admission(applicant_data: Dict[str, Any]) -> Any:
        """
        The ONLY way admission becomes a student.
        Implementation in services.py
        """
        raise NotImplementedError("Use students.services.StudentService.create_from_admission")
    
    @staticmethod
    def get_student_by_id(student_id: int) -> Optional[Dict[str, Any]]:
        """
        Get student data by ID. Returns dict, not model instance.
        """
        raise NotImplementedError("Use students.selectors.StudentSelector.get_by_id")
    
    @staticmethod
    def update_student_status(student_id: int, new_status: str, reason: str = "") -> Dict[str, Any]:
        """
        Update student status with audit trail.
        """
        raise NotImplementedError("Use students.services.StudentService.update_status")
    
    @staticmethod
    def get_class_students(class_id: int, academic_session_id: int) -> List[Dict[str, Any]]:
        """
        Get all students in a class for a specific session.
        """
        raise NotImplementedError("Use students.selectors.StudentSelector.get_class_students")


# This is the ONLY public API for the students app
__all__ = [
    'StudentDataContract',
    'GuardianDataContract',
    'StudentServiceInterface',
]
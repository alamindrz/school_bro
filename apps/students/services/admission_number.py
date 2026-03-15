"""
Admission Number Generation Service
DEPENDS ON: students/exceptions.py, students/validators.py, corecode/selectors.py
"""

import re
from typing import Optional
from django.db import transaction
from django.db.models import Max

from apps.corecode.selectors import AcademicSessionSelector
from apps.corecode.exceptions import NoActiveSessionError

from ..exceptions import (
    AdmissionNumberGenerationError,
    AdmissionNumberCollisionError,
    AdmissionNumberFormatError,
)
from ..validators import StudentValidator
from ..models import Student




class AdmissionNumberService:
    """
    Service for generating and validating admission numbers.
    SINGLE SOURCE OF TRUTH for admission number logic.
    """
    
    # Class code mapping - Nigerian standard class codes
    CLASS_CODE_MAP = {
        # Nursery
        'NUR1': 'N01',
        'NUR2': 'N02',
        'NUR3': 'N03',
        # Primary
        'PRI1': 'P01',
        'PRI2': 'P02',
        'PRI3': 'P03',
        'PRI4': 'P04',
        'PRI5': 'P05',
        'PRI6': 'P06',
        # JSS
        'JSS1': 'J01',
        'JSS2': 'J02',
        'JSS3': 'J03',
        # SSS
        'SS1': 'S01',
        'SS2': 'S02',
        'SS3': 'S03',
    }
    
    @classmethod
    def generate_admission_number(
        cls,
        class_name: str,
        session_code: Optional[str] = None,
        sequence_length: int = 3
    ) -> str:
        """
        Generate a unique admission number.
        Format: {SESSION_YEAR}/{CLASS_CODE}/{SEQUENCE}
        Example: 2024/SS1/042
        
        Hierarchy:
        1. Get current session if not provided
        2. Map class name to standard code
        3. Generate next sequence number
        4. Format and validate
        """
        # 1. Get session
        if not session_code:
            current_session = AcademicSessionSelector.get_current_session()
            if not current_session:
                raise NoActiveSessionError(
                    "Cannot generate admission number: No active academic session"
                )
            session_code = current_session.code
        
        # 2. Map class code
        class_code = cls.CLASS_CODE_MAP.get(class_name)
        if not class_code:
            # Fallback to raw class name if not in map
            class_code = re.sub(r'[^A-Z0-9]', '', class_name)[:3]
        
        # 3. Generate sequence number
        sequence = cls._get_next_sequence(session_code, class_code, sequence_length)
        
        # 4. Format admission number
        admission_number = f"{session_code}/{class_code}/{sequence:0{sequence_length}d}"
        
        # 5. Validate format
        try:
            StudentValidator.validate_admission_number_format(admission_number)
        except AdmissionNumberFormatError as e:
            raise AdmissionNumberGenerationError(f"Generated invalid format: {e}")
        
        return admission_number
    
    @classmethod
    @transaction.atomic
    def _get_next_sequence(
        cls,
        session_code: str,
        class_code: str,
        sequence_length: int = 3
    ) -> int:
        """
        Atomically retrieves and increments the next sequence number.
        
        This method uses a pessimistic locking strategy (select_for_update) on 
        the AdmissionSequence table. This ensures that even if multiple 
        processes attempt to generate a number for the same class/session 
        simultaneously, they will be queued, preventing duplicate 
        admission numbers.
        
        Args:
            session_code: The identifier for the academic year.
            class_code: The mapped code for the student's level.
            sequence_length: Padding length for the numeric portion.
            
        Returns:
            int: The next available sequence number.
        """
        from apps.corecode.models import AdmissionSequence
        
        # select_for_update() locks the specific row until this transaction commits.
        # Other threads calling this same session/class will block here until we finish.
        sequence_obj, created = AdmissionSequence.objects.select_for_update().get_or_create(
            session_code=session_code,
            class_code=class_code
        )
        
        # Increment the stateful counter
        new_sequence = sequence_obj.last_value + 1
        sequence_obj.last_value = new_sequence
        sequence_obj.save()
        
        return new_sequence

    
    @classmethod
    @transaction.atomic
    def generate_batch_admission_numbers(
        cls,
        class_name: str,
        count: int,
        session_code: Optional[str] = None
    ) -> list:
        """
        Generate multiple admission numbers for bulk enrollment.
        Fetch base sequence once and increment in-memory.
        """
        if count <= 0:
            raise AdmissionNumberGenerationError("Count must be positive")
        
        if not session_code:
            current_session = AcademicSessionSelector.get_current_session()
            if not current_session:
                raise NoActiveSessionError("No active academic session")
            session_code = current_session.code
    
        class_code = cls.CLASS_CODE_MAP.get(class_name)
        if not class_code:
            class_code = re.sub(r'[^A-Z0-9]', '', class_name)[:3]
        
        # 1. Get the starting sequence once (locking the row)
        start_sequence = cls._get_next_sequence(session_code, class_code)
        
        numbers = []
        for i in range(count):
            # 2. Increment in-memory to avoid repeated DB lookups
            sequence = start_sequence + i
            admission_number = f"{session_code}/{class_code}/{sequence:03d}"
            
            # 3. Optional: Validate format for the first and last to be sure
            StudentValidator.validate_admission_number_format(admission_number)
            numbers.append(admission_number)
            
        return numbers

    
    @classmethod
    def validate_admission_number_unique(
        cls,
        admission_number: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Validate that admission number is unique.
        Used by forms and services before saving.
        """
        queryset = Student.objects.filter(admission_number=admission_number)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        
        if queryset.exists():
            raise AdmissionNumberCollisionError(
                f"Admission number '{admission_number}' is already in use"
            )
        
        return True
    
    @classmethod
    def parse_admission_number(cls, admission_number: str) -> dict:
        """
        Parse admission number into components.
        Returns: {
            'session_code': '2024',
            'class_code': 'SS1',
            'sequence': '042',
            'full': '2024/SS1/042'
        }
        """
        try:
            parts = admission_number.split('/')
            if len(parts) != 3:
                raise ValueError()
            
            return {
                'session_code': parts[0],
                'class_code': parts[1],
                'sequence': parts[2],
                'full': admission_number
            }
        except (ValueError, IndexError):
            raise AdmissionNumberFormatError(
                f"Cannot parse admission number: {admission_number}"
            )
    
    @classmethod
    def get_class_from_admission_number(cls, admission_number: str) -> Optional[str]:
        """Extract class name from admission number"""
        parsed = cls.parse_admission_number(admission_number)
        
        # Reverse mapping of class codes
        reverse_map = {v: k for k, v in cls.CLASS_CODE_MAP.items()}
        return reverse_map.get(parsed['class_code'])
    
    @classmethod
    def get_session_from_admission_number(cls, admission_number: str) -> str:
        """Extract session code from admission number"""
        parsed = cls.parse_admission_number(admission_number)
        return parsed['session_code']
"""
Student Class Services
Manages the Nigerian 6-3-3-4 class structure
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from typing import List, Optional, Dict, Any

from ..models import StudentClass
from ..selectors import StudentClassSelector
from ..constants import NigerianClassLevel, EducationLevel
from ..exceptions import ClassNotFoundError, InvalidClassProgressionError


class StudentClassService:
    """
    Student Class business operations
    Enforces Nigerian 6-3-3-4 education structure
    """
    
    @staticmethod
    @transaction.atomic
    def create_class(
        name: str,
        display_name: str,
        education_level: str,
        max_students: int = 40,
        sort_order: int = 0,
        is_active: bool = True
    ) -> StudentClass:
        """
        Create a new student class
        Must use NigerianClassLevel constants
        
        Args:
            name: Class code (e.g., 'SS1', 'JSS1')
            display_name: Human-readable name (e.g., 'SS 1')
            education_level: Level from EducationLevel constants
            max_students: Maximum capacity
            sort_order: Order for display
            is_active: Whether class is active
            
        Returns:
            StudentClass: Created class instance
            
        Raises:
            ValidationError: If class name is not in Nigerian standard
        """
        # Validate class name is Nigerian standard
        valid_names = [c[0] for c in NigerianClassLevel.CHOICES]
        if name not in valid_names:
            raise ValidationError(
                f"Invalid class name: {name}. Must use Nigerian standard classes: "
                f"{', '.join(valid_names[:5])}..."
            )
        
        # Validate education level matches class name
        expected_level = StudentClassService._get_education_level_for_class(name)
        if education_level != expected_level:
            raise ValidationError(
                f"Education level {education_level} does not match class {name}. "
                f"Expected: {expected_level}"
            )
        
        student_class = StudentClass(
            name=name,
            display_name=display_name,
            education_level=education_level,
            max_students=max_students,
            sort_order=sort_order,
            is_active=is_active
        )
        student_class.full_clean()
        student_class.save()
        
        return student_class
    
    @staticmethod
    @transaction.atomic
    def bulk_create_nigerian_classes() -> List[StudentClass]:
        """
        Create all standard Nigerian 6-3-3-4 classes
        
        Returns:
            List[StudentClass]: Created/updated classes
        """
        classes = []
        order = 0
        
        # Define complete Nigerian class structure
        class_definitions = [
            # Nursery (3 years)
            (NigerianClassLevel.NURSERY_1, "Nursery 1", EducationLevel.NURSERY, 25),
            (NigerianClassLevel.NURSERY_2, "Nursery 2", EducationLevel.NURSERY, 25),
            (NigerianClassLevel.NURSERY_3, "Nursery 3", EducationLevel.NURSERY, 25),
            
            # Primary (6 years)
            (NigerianClassLevel.PRIMARY_1, "Primary 1", EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_2, "Primary 2", EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_3, "Primary 3", EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_4, "Primary 4", EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_5, "Primary 5", EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_6, "Primary 6", EducationLevel.PRIMARY, 40),
            
            # Junior Secondary (3 years)
            (NigerianClassLevel.JSS_1, "JSS 1", EducationLevel.JSS, 45),
            (NigerianClassLevel.JSS_2, "JSS 2", EducationLevel.JSS, 45),
            (NigerianClassLevel.JSS_3, "JSS 3", EducationLevel.JSS, 45),
            
            # Senior Secondary (3 years)
            (NigerianClassLevel.SS_1, "SS 1", EducationLevel.SSS, 45),
            (NigerianClassLevel.SS_2, "SS 2", EducationLevel.SSS, 45),
            (NigerianClassLevel.SS_3, "SS 3", EducationLevel.SSS, 45),
        ]
        
        for name, display_name, level, max_students in class_definitions:
            cls, created = StudentClass.objects.update_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'education_level': level,
                    'max_students': max_students,
                    'sort_order': order,
                    'is_active': True,
                }
            )
            classes.append(cls)
            order += 1
        
        return classes
    
    @staticmethod
    @transaction.atomic
    def update_class_capacity(
        class_id: int,
        max_students: int,
        updated_by=None
    ) -> StudentClass:
        """
        Update maximum students for a class
        
        Args:
            class_id: ID of class to update
            max_students: New maximum capacity
            updated_by: User performing the update
            
        Returns:
            StudentClass: Updated class instance
            
        Raises:
            ClassNotFoundError: If class doesn't exist
            ValidationError: If capacity is invalid
        """
        try:
            student_class = StudentClass.objects.get(id=class_id)
        except StudentClass.DoesNotExist:
            raise ClassNotFoundError(f"Class with id {class_id} not found")
        
        if max_students < 1:
            raise ValidationError("Maximum students must be at least 1")
        
        if max_students > 100:
            raise ValidationError("Maximum students cannot exceed 100")
        
        student_class.max_students = max_students
        student_class.full_clean()
        student_class.save(update_fields=['max_students', 'updated_at'])
        
        return student_class
    
    @staticmethod
    @transaction.atomic
    def deactivate_class(class_id: int) -> StudentClass:
        """
        Deactivate a class (no new enrollments)
        
        Args:
            class_id: ID of class to deactivate
            
        Returns:
            StudentClass: Updated class instance
            
        Raises:
            ClassNotFoundError: If class doesn't exist
        """
        try:
            student_class = StudentClass.objects.get(id=class_id)
        except StudentClass.DoesNotExist:
            raise ClassNotFoundError(f"Class with id {class_id} not found")
        
        student_class.is_active = False
        student_class.save(update_fields=['is_active', 'updated_at'])
        
        return student_class
    
    @staticmethod
    @transaction.atomic
    def activate_class(class_id: int) -> StudentClass:
        """
        Activate a class (allow enrollments)
        
        Args:
            class_id: ID of class to activate
            
        Returns:
            StudentClass: Updated class instance
            
        Raises:
            ClassNotFoundError: If class doesn't exist
        """
        try:
            student_class = StudentClass.objects.get(id=class_id)
        except StudentClass.DoesNotExist:
            raise ClassNotFoundError(f"Class with id {class_id} not found")
        
        student_class.is_active = True
        student_class.save(update_fields=['is_active', 'updated_at'])
        
        return student_class
    
    @staticmethod
    def validate_class_progression(
        from_class_id: int,
        to_class_id: int
    ) -> bool:
        """
        Validate that a student can progress from one class to another
        
        Args:
            from_class_id: Current class ID
            to_class_id: Target class ID
            
        Returns:
            bool: True if valid progression
            
        Raises:
            ClassNotFoundError: If either class doesn't exist
            InvalidClassProgressionError: If progression is invalid
        """
        try:
            from_class = StudentClass.objects.get(id=from_class_id)
            to_class = StudentClass.objects.get(id=to_class_id)
        except StudentClass.DoesNotExist as e:
            raise ClassNotFoundError(str(e))
        
        # Check if to_class is the next class in progression
        expected_next = from_class.next_class
        if expected_next and expected_next.id == to_class.id:
            return True
        
        # Allow staying in same class (for repeaters)
        if from_class.id == to_class.id:
            return True
        
        # Check if it's a valid non-standard progression (e.g., within same level)
        if from_class.education_level == to_class.education_level:
            if from_class.sort_order < to_class.sort_order:
                return True
        
        raise InvalidClassProgressionError(
            f"Cannot progress from {from_class.display_name} to {to_class.display_name}"
        )
    
    @staticmethod
    def _get_education_level_for_class(class_name: str) -> str:
        """Get the education level for a given class name"""
        if class_name.startswith('NUR'):
            return EducationLevel.NURSERY
        elif class_name.startswith('PRI'):
            return EducationLevel.PRIMARY
        elif class_name.startswith('JSS'):
            return EducationLevel.JSS
        elif class_name.startswith('SS'):
            return EducationLevel.SSS
        else:
            return EducationLevel.TERTIARY
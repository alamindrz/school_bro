"""
Student Promotion Service
Handles class promotion, graduation, and progression logic
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import List, Dict, Any, Optional, Tuple
import logging

from ..models import Student, StudentHistory
from ..constants import StudentStatus
from ..exceptions import (
    StudentError,
    StudentNotFoundError,
    StudentNotEligibleError,
    InvalidClassProgressionError,
    BulkOperationError
)
from apps.corecode.selectors import (
    AcademicSessionSelector,
    AcademicTermSelector,
    StudentClassSelector
)
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog
from apps.corecode.constants import NigerianClassLevel

logger = logging.getLogger(__name__)


class PromotionService:
    """
    Student promotion and graduation business logic.
    Handles all class progression operations.
    """
    
    @staticmethod
    @transaction.atomic
    def promote_student(
        student_id: int,
        to_class_id: int,
        academic_session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        promoted_by_id: Optional[int] = None,
        notes: str = ""
    ) -> Student:
        """
        Promote a single student to the next class.
        
        Args:
            student_id: ID of student to promote
            to_class_id: Target class ID
            academic_session_id: Session for the promotion (defaults to current)
            term_id: Term for the promotion (defaults to current)
            promoted_by_id: User ID performing the promotion
            notes: Additional notes about the promotion
            
        Returns:
            Student: Updated student instance
            
        Raises:
            StudentNotFoundError: If student doesn't exist
            StudentNotEligibleError: If student is not eligible for promotion
            InvalidClassProgressionError: If target class is not valid progression
        """
        # Get student
        try:
            student = Student.objects.select_related('current_class').get(id=student_id)
        except Student.DoesNotExist:
            raise StudentNotFoundError(f"Student with id {student_id} not found")
        
        # Check if student is eligible for promotion
        if not PromotionService._is_eligible_for_promotion(student):
            raise StudentNotEligibleError(
                f"Student {student.admission_number} is not eligible for promotion. "
                f"Current status: {student.get_status_display()}"
            )
        
        # Get current academic context
        current_session = AcademicSessionSelector.get_current_session()
        if not current_session:
            raise ValidationError("No active academic session configured")
        
        academic_session_id = academic_session_id or current_session.id
        
        current_term = AcademicTermSelector.get_current_term()
        term_id = term_id or (current_term.id if current_term else None)
        
        # Validate class progression
        from_class = student.current_class
        to_class = StudentClassSelector.get_by_id(to_class_id)
        
        if not to_class:
            raise ValidationError(f"Target class with id {to_class_id} not found")
        
        # Check if progression is valid
        expected_next = from_class.next_class
        is_valid = (
            (expected_next and expected_next.id == to_class.id) or  # Normal progression
            (from_class.id == to_class.id) or  # Staying in same class (repeater)
            (from_class.education_level == to_class.education_level and 
             from_class.sort_order < to_class.sort_order)  # Within same level
        )
        
        if not is_valid:
            raise InvalidClassProgressionError(
                f"Cannot promote from {from_class.display_name} to {to_class.display_name}"
            )
        
        # Store old class for history
        old_class = student.current_class
        
        # Update student
        student.current_class = to_class
        student.save(update_fields=['current_class', 'updated_at'])
        
        # Check if this is graduation (promotion to SS3 or beyond)
        is_graduation = to_class.name == NigerianClassLevel.SS_3
        
        # Create history entry
        history = StudentHistory.objects.create(
            student=student,
            academic_session_id=academic_session_id,
            term=current_term.term if current_term else 1,
            class_at_time=to_class,
            status_at_time=student.status,
            action='GRADUATED' if is_graduation else 'PROMOTED',
            previous_class=old_class,
            notes=notes or f"Promoted from {old_class.display_name} to {to_class.display_name}",
            performed_by_id=promoted_by_id
        )
        
        # If graduated, update status
        if is_graduation:
            student.status = StudentStatus.GRADUATED
            student.save(update_fields=['status'])
        
        # Log the promotion
        SystemLogService.log_promotion(
            user=promoted_by_id,
            student=student,
            from_class=old_class,
            to_class=to_class,
            academic_session_id=academic_session_id,
            request=None
        )
        
        logger.info(
            f"Student {student.admission_number} promoted from {old_class.name} "
            f"to {to_class.name}"
        )
        
        return student
    
    @staticmethod
    @transaction.atomic
    def bulk_promote_students(
        student_ids: List[int],
        to_class_id: int,
        academic_session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        promoted_by_id: Optional[int] = None,
        notes: str = ""
    ) -> Tuple[List[Student], List[Dict[str, Any]]]:
        """
        Bulk promote multiple students to the next class.
        
        Args:
            student_ids: List of student IDs to promote
            to_class_id: Target class ID
            academic_session_id: Session for the promotion
            term_id: Term for the promotion
            promoted_by_id: User ID performing the promotion
            notes: Additional notes for all promotions
            
        Returns:
            Tuple of (successful_students, failed_attempts)
        """
        successful = []
        failed = []
        
        for student_id in student_ids:
            try:
                student = PromotionService.promote_student(
                    student_id=student_id,
                    to_class_id=to_class_id,
                    academic_session_id=academic_session_id,
                    term_id=term_id,
                    promoted_by_id=promoted_by_id,
                    notes=notes
                )
                successful.append(student)
            except Exception as e:
                failed.append({
                    'student_id': student_id,
                    'error': str(e)
                })
                logger.warning(f"Failed to promote student {student_id}: {e}")
        
        # Log bulk operation
        if successful:
            SystemLogService.log_action(
                user_id=promoted_by_id,
                action=SystemLog.ActionType.PROMOTION,
                app_label=SystemLog.AppLabel.STUDENTS,
                model_name='Student',
                object_id='bulk',
                object_repr=f'Bulk promotion of {len(successful)} students',
                changes={
                    'successful_count': len(successful),
                    'failed_count': len(failed),
                    'to_class_id': to_class_id,
                    'student_ids': student_ids
                }
            )
        
        if failed:
            raise BulkOperationError(
                message=f"Promoted {len(successful)} students with {len(failed)} failures",
                successful=successful,
                failed=failed
            )
        
        return successful, failed
    
    @staticmethod
    @transaction.atomic
    def promote_class(
        from_class_id: int,
        to_class_id: int,
        academic_session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        promoted_by_id: Optional[int] = None,
        exclude_student_ids: List[int] = None
    ) -> Tuple[List[Student], List[Dict[str, Any]]]:
        """
        Promote all eligible students in a class to the next class.
        
        Args:
            from_class_id: Source class ID
            to_class_id: Target class ID
            academic_session_id: Session for the promotion
            term_id: Term for the promotion
            promoted_by_id: User ID performing the promotion
            exclude_student_ids: Student IDs to exclude from promotion
            
        Returns:
            Tuple of (promoted_students, failed_attempts)
        """
        # Get all eligible students in the class
        students = Student.objects.filter(
            current_class_id=from_class_id,
            status=StudentStatus.ACTIVE
        )
        
        if exclude_student_ids:
            students = students.exclude(id__in=exclude_student_ids)
        
        student_ids = list(students.values_list('id', flat=True))
        
        return PromotionService.bulk_promote_students(
            student_ids=student_ids,
            to_class_id=to_class_id,
            academic_session_id=academic_session_id,
            term_id=term_id,
            promoted_by_id=promoted_by_id,
            notes=f"Class-wide promotion from {from_class_id} to {to_class_id}"
        )
    
    @staticmethod
    @transaction.atomic
    def graduate_graduating_class(
        class_id: int = None,
        academic_session_id: Optional[int] = None,
        graduated_by_id: Optional[int] = None
    ) -> List[Student]:
        """
        Graduate all students in a graduating class (SS3).
        
        Args:
            class_id: Class ID to graduate (defaults to current SS3 class)
            academic_session_id: Session of graduation
            graduated_by_id: User ID performing the graduation
            
        Returns:
            List of graduated students
        """
        # Find SS3 class
        if not class_id:
            ss3_class = StudentClassSelector.get_graduating_classes()
            if not ss3_class:
                raise ValidationError("No graduating class (SS3) found")
            class_id = ss3_class[0].id
        
        # Get all active SS3 students
        students = Student.objects.filter(
            current_class_id=class_id,
            status=StudentStatus.ACTIVE
        )
        
        graduated_students = []
        
        for student in students:
            student.status = StudentStatus.GRADUATED
            student.save(update_fields=['status'])
            
            # Record graduation history
            StudentHistory.objects.create(
                student=student,
                academic_session_id=academic_session_id or 
                                  AcademicSessionSelector.get_current_session().id,
                term=3,  # Third term graduation
                class_at_time=student.current_class,
                status_at_time=StudentStatus.GRADUATED,
                action='GRADUATED',
                notes='Completed secondary education',
                performed_by_id=graduated_by_id
            )
            
            graduated_students.append(student)
            
            logger.info(f"Student {student.admission_number} graduated")
        
        # Log graduation
        if graduated_students:
            SystemLogService.log_action(
                user_id=graduated_by_id,
                action=SystemLog.ActionType.PROMOTION,
                app_label=SystemLog.AppLabel.STUDENTS,
                model_name='Student',
                object_id='bulk',
                object_repr=f'Graduation of {len(graduated_students)} students',
                changes={
                    'graduated_count': len(graduated_students),
                    'class_id': class_id,
                    'academic_session_id': academic_session_id
                }
            )
        
        return graduated_students
    
    @staticmethod
    def _is_eligible_for_promotion(student: Student) -> bool:
        """
        Check if a student is eligible for promotion.
        
        Eligibility criteria:
        1. Status must be Active
        2. Must have complete results (to be implemented by results app)
        3. Must have financial clearance (to be implemented by finance app)
        4. Must have minimum attendance (to be implemented by attendance app)
        """
        # Basic eligibility - status must be Active
        if student.status != StudentStatus.ACTIVE:
            return False
        
        # TODO: Check results completion (requires results app)
        # TODO: Check financial clearance (requires finance app)
        # TODO: Check attendance (requires attendance app)
        
        return True
    
    @staticmethod
    def get_promotion_candidates(
        from_class_id: int,
        academic_session_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of students eligible for promotion from a class.
        
        Args:
            from_class_id: Source class ID
            academic_session_id: Academic session
            
        Returns:
            List of student dictionaries with eligibility info
        """
        students = Student.objects.filter(
            current_class_id=from_class_id,
            status=StudentStatus.ACTIVE
        ).select_related('current_class')
        
        candidates = []
        for student in students:
            candidates.append({
                'id': student.id,
                'admission_number': student.admission_number,
                'name': student.get_full_name,
                'current_class': student.current_class.display_name,
                'eligible': PromotionService._is_eligible_for_promotion(student),
                'obstacles': []  # TODO: Add reasons if not eligible
            })
        
        return candidates
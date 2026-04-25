"""
Qualification Service - Teacher subject qualification management
Replaces the old SubjectAssignment service with global qualifications.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from typing import Optional, List, Dict, Any
import logging

from ..models import TeacherSubjectQualification, Staff
from ..exceptions import StaffNotFoundError
from ..selectors import StaffSelector, TeacherQualificationSelector

from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class QualificationService:
    """
    Teacher qualification business operations.
    Handles global subject qualifications (what a teacher CAN teach).
    """
    
    @staticmethod
    @transaction.atomic
    def set_qualifications(
        teacher_id: int,
        subject_ids: List[int],
        primary_subject_id: Optional[int] = None,
        updated_by_id: Optional[int] = None,
        request=None
    ) -> Dict[str, Any]:
        """
        Set qualified subjects for a teacher.
        Replaces ALL existing qualifications with the new set.
        
        Args:
            teacher_id: Staff ID
            subject_ids: List of subject IDs the teacher is qualified to teach
            primary_subject_id: Optional primary subject ID
            updated_by_id: User ID performing the update
            request: HTTP request for audit logging
            
        Returns:
            Dictionary with summary of changes
        """
        # Validate teacher exists and is academic staff
        try:
            teacher = Staff.objects.get(
                id=teacher_id,
                staff_category='academic',
                employment_status='active'
            )
        except Staff.DoesNotExist:
            raise StaffNotFoundError(
                f"Teacher with ID {teacher_id} not found or not active academic staff"
            )
        
        # Validate primary subject is in subject_ids
        if primary_subject_id and primary_subject_id not in subject_ids:
            raise ValidationError("Primary subject must be one of the selected subjects")
        
        # Get existing qualifications for audit
        old_qualifications = list(
            TeacherSubjectQualification.objects.filter(
                teacher_id=teacher_id
            ).values_list('subject_id', flat=True)
        )
        
        # Clear existing
        deleted_count, _ = TeacherSubjectQualification.objects.filter(
            teacher_id=teacher_id
        ).delete()
        
        # Add new qualifications
        created_count = 0
        for subject_id in subject_ids:
            TeacherSubjectQualification.objects.create(
                teacher_id=teacher_id,
                subject_id=subject_id,
                is_primary=(subject_id == primary_subject_id),
                created_by_id=updated_by_id
            )
            created_count += 1
        
        # Audit log
        SystemLogService.log_action(
            user_id=updated_by_id,
            action=SystemLog.ActionType.UPDATE,
            app_label='staffs',
            model_name='TeacherSubjectQualification',
            object_id=str(teacher_id),
            object_repr=teacher.get_full_name,
            changes={
                'action': 'set_qualifications',
                'old_subject_ids': old_qualifications,
                'new_subject_ids': subject_ids,
                'primary_subject_id': primary_subject_id,
            },
            request=request
        )
        
        logger.info(
            f"Qualifications updated for teacher {teacher_id}: "
            f"deleted {deleted_count}, created {created_count}"
        )
        
        return {
            'teacher_id': teacher_id,
            'teacher_name': teacher.get_full_name,
            'deleted_count': deleted_count,
            'created_count': created_count,
            'subject_ids': subject_ids,
            'primary_subject_id': primary_subject_id,
        }
    
    @staticmethod
    @transaction.atomic
    def add_qualification(
        teacher_id: int,
        subject_id: int,
        is_primary: bool = False,
        updated_by_id: Optional[int] = None
    ) -> TeacherSubjectQualification:
        """
        Add a single qualification for a teacher.
        Does NOT clear existing qualifications.
        
        Args:
            teacher_id: Staff ID
            subject_id: Subject ID to add
            is_primary: Whether this is a primary subject
            updated_by_id: User ID performing the action
            
        Returns:
            Created TeacherSubjectQualification instance
        """
        # Validate teacher
        try:
            teacher = Staff.objects.get(
                id=teacher_id,
                staff_category='academic',
                employment_status='active'
            )
        except Staff.DoesNotExist:
            raise StaffNotFoundError(
                f"Teacher with ID {teacher_id} not found or not active academic staff"
            )
        
        # If setting as primary, unset other primary subjects
        if is_primary:
            TeacherSubjectQualification.objects.filter(
                teacher_id=teacher_id,
                is_primary=True
            ).update(is_primary=False)
        
        # Create or update qualification
        qualification, created = TeacherSubjectQualification.objects.update_or_create(
            teacher_id=teacher_id,
            subject_id=subject_id,
            defaults={
                'is_primary': is_primary,
                'created_by_id': updated_by_id
            }
        )
        
        action = "created" if created else "updated"
        logger.info(f"Qualification {action} for teacher {teacher_id}: subject {subject_id}")
        
        return qualification
    
    @staticmethod
    @transaction.atomic
    def remove_qualification(
        teacher_id: int,
        subject_id: int,
        deleted_by_id: Optional[int] = None
    ) -> bool:
        """
        Remove a single qualification from a teacher.
        
        Args:
            teacher_id: Staff ID
            subject_id: Subject ID to remove
            deleted_by_id: User ID performing the action
            
        Returns:
            True if deleted, False if not found
        """
        deleted_count, _ = TeacherSubjectQualification.objects.filter(
            teacher_id=teacher_id,
            subject_id=subject_id
        ).delete()
        
        if deleted_count > 0:
            logger.info(f"Qualification removed: teacher {teacher_id}, subject {subject_id}")
            return True
        
        return False
    
    @staticmethod
    @transaction.atomic
    def clear_all_qualifications(
        teacher_id: int,
        cleared_by_id: Optional[int] = None
    ) -> int:
        """
        Remove ALL qualifications for a teacher.
        
        Args:
            teacher_id: Staff ID
            cleared_by_id: User ID performing the action
            
        Returns:
            Number of qualifications deleted
        """
        deleted_count, _ = TeacherSubjectQualification.objects.filter(
            teacher_id=teacher_id
        ).delete()
        
        logger.info(f"Cleared {deleted_count} qualifications for teacher {teacher_id}")
        
        return deleted_count
    
    @staticmethod
    def get_qualifications(teacher_id: int) -> List[Dict[str, Any]]:
        """
        Get all qualifications for a teacher.
        Wrapper around selector for consistency.
        """
        return TeacherQualificationSelector.get_for_teacher(teacher_id)
    
    @staticmethod
    def get_qualified_teachers(subject_id: int) -> List[Dict[str, Any]]:
        """
        Get all teachers qualified to teach a subject.
        """
        return TeacherQualificationSelector.get_teachers_for_subject(subject_id)


# ============================================================================
# DEPRECATED: Old QualificationService (kept for backward compatibility)
# ============================================================================

class QualificationService:
    """
    DEPRECATED: Use QualificationService instead.
    Kept for backward compatibility during migration.
    """
    
    @staticmethod
    @transaction.atomic
    def assign_subject(*args, **kwargs):
        """
        DEPRECATED: Use QualificationService.set_qualifications() instead.
        """
        import warnings
        warnings.warn(
            "QualificationService.assign_subject() is deprecated. "
            "Use QualificationService.set_qualifications() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Forward to new service with compatibility mapping
        teacher_id = kwargs.get('staff_id', args[0] if args else None)
        subject_id = kwargs.get('subject_id', args[1] if len(args) > 1 else None)
        is_primary = kwargs.get('is_form_master', False)
        
        if teacher_id and subject_id:
            return QualificationService.add_qualification(
                teacher_id=teacher_id,
                subject_id=subject_id,
                is_primary=is_primary,
                updated_by_id=kwargs.get('assigned_by_id')
            )
        
        raise ValidationError("Invalid arguments for deprecated assign_subject")
    
    @staticmethod
    @transaction.atomic
    def assign_duty(*args, **kwargs):
        """
        Duty assignments remain unchanged.
        """
        from ..models import DutyAssignment
        
        duty = DutyAssignment.objects.create(
            staff_id=kwargs.get('staff_id'),
            duty_post=kwargs.get('duty_post'),
            academic_session_id=kwargs.get('session_id'),
            student_class_id=kwargs.get('class_id'),
            club_name=kwargs.get('club_name', ''),
            sport_name=kwargs.get('sport_name', ''),
            house_name=kwargs.get('house_name', ''),
            day_of_week=kwargs.get('day_of_week'),
            start_time=kwargs.get('start_time'),
            end_time=kwargs.get('end_time'),
            assigned_by_id=kwargs.get('assigned_by_id')
        )
        
        return duty
    
    @staticmethod
    @transaction.atomic
    def set_form_master(*args, **kwargs):
        """
        DEPRECATED: Form master is now handled via primary subject in qualifications.
        """
        import warnings
        warnings.warn(
            "QualificationService.set_form_master() is deprecated. "
            "Use QualificationService.set_qualifications() with primary_subject_id instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # No-op for now
        return None
    
    @staticmethod
    @transaction.atomic
    def assign_class_teacher(*args, **kwargs):
        """
        DEPRECATED: Class teacher is now handled separately or via primary subject.
        """
        import warnings
        warnings.warn(
            "QualificationService.assign_class_teacher() is deprecated.",
            DeprecationWarning,
            stacklevel=2
        )
        # No-op for now
        return None
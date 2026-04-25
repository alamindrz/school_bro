"""
Timetable Service - Core timetable operations
All write operations for timetable management.
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, List, Dict, Any
import logging

from ..models import Timetable, TimetableSlot, SchoolDay, TimetablePeriod
from ..selectors import TimetableSelector
from apps.corecode.selectors import AcademicSessionSelector, StudentClassSelector
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class TimetableService:
    """Core timetable business operations with audit trail"""
    
    @classmethod
    @transaction.atomic
    def create_timetable(
        cls,
        session_id: int,
        class_id: int,
        term_id: Optional[int] = None,
        created_by_id: Optional[int] = None,
        name: Optional[str] = None,
        request=None
    ) -> Timetable:
        """
        Create a new timetable with empty slots for all active days and teaching periods.
        
        Args:
            session_id: ID of the academic session
            class_id: ID of the student class
            term_id: Optional ID of the academic term
            created_by_id: ID of the user creating the timetable
            name: Optional custom name for the timetable
            request: HTTP request for audit logging
            
        Returns:
            Created Timetable instance
            
        Raises:
            ValidationError: If session or class not found
        """
        # Validate session exists
        session = AcademicSessionSelector.get_by_id(session_id)
        if not session:
            raise ValidationError(f"Academic session with ID {session_id} not found")
        
        # Validate class exists
        class_data = StudentClassSelector.get_by_id(class_id)
        if not class_data:
            raise ValidationError(f"Student class with ID {class_id} not found")
        
        class_name = class_data.get('display_name', 'Class')
        
        # Get version number
        existing_count = Timetable.objects.filter(
            academic_session_id=session_id,
            academic_term_id=term_id,
            student_class_id=class_id
        ).count()
        
        version = existing_count + 1
        
        # Create timetable
        timetable = Timetable.objects.create(
            academic_session_id=session_id,
            academic_term_id=term_id,
            student_class_id=class_id,
            name=name or f"{class_name} Timetable",
            version=version,
            is_current=(version == 1),  # First version is current by default
            created_by_id=created_by_id
        )
        
        # Create slots for all active days and ALL periods (not just teaching)
        # This ensures breaks/assemblies are also represented
        days = SchoolDay.objects.filter(is_active=True).order_by('order')
        periods = TimetablePeriod.objects.all().order_by('order')
        
        slots_created = 0
        slots_to_create = []
        for day in days:
            for period in periods:
                slots_to_create.append(TimetableSlot(
                    timetable=timetable,
                    day=day,
                    period=period,
                    created_by_id=created_by_id
                ))
        
        TimetableSlot.objects.bulk_create(slots_to_create)
        slots_created = len(slots_to_create)
        
        # Audit log
        SystemLogService.log_action(
            user=created_by_id,
            action=SystemLog.ActionType.CREATE,
            app_label=SystemLog.AppLabel.TIMETABLE,
            model_name='Timetable',
            object_id=str(timetable.id),
            object_repr=timetable.name,
            changes={
                'session_id': session_id,
                'session_name': session.name if hasattr(session, 'name') else None,
                'term_id': term_id,
                'class_id': class_id,
                'class_name': class_name,
                'version': version,
                'slots_created': slots_created,
            },
            request=request
        )
        
        logger.info(f"Created timetable '{timetable.name}' (v{version}) with {slots_created} slots")
        
        return timetable
    
    @classmethod
    @transaction.atomic
    def copy_timetable(
        cls,
        source_timetable_id: int,
        new_session_id: Optional[int] = None,
        new_term_id: Optional[int] = None,
        copied_by_id: Optional[int] = None,
        request=None
    ) -> Timetable:
        """
        Copy an existing timetable to a new session/term or create a new version.
        
        Args:
            source_timetable_id: ID of the timetable to copy
            new_session_id: Optional new session ID (uses source if not provided)
            new_term_id: Optional new term ID (uses source if not provided)
            copied_by_id: ID of the user performing the copy
            request: HTTP request for audit logging
            
        Returns:
            Newly created Timetable instance
            
        Raises:
            ValidationError: If source timetable not found
        """
        try:
            source = Timetable.objects.select_related(
                'student_class',
                'academic_session',
                'academic_term'
            ).get(id=source_timetable_id)
        except Timetable.DoesNotExist:
            raise ValidationError(f"Source timetable with ID {source_timetable_id} not found")
        
        # Determine new session/term
        session_id = new_session_id or source.academic_session_id
        term_id = new_term_id or source.academic_term_id
        
        # Get version number
        existing_count = Timetable.objects.filter(
            academic_session_id=session_id,
            academic_term_id=term_id,
            student_class_id=source.student_class_id
        ).count()
        
        version = existing_count + 1
        
        # Create new timetable
        new_timetable = Timetable.objects.create(
            academic_session_id=session_id,
            academic_term_id=term_id,
            student_class_id=source.student_class_id,
            name=f"{source.student_class.display_name} Timetable (v{version})",
            version=version,
            is_current=True,
            previous_version=source,
            created_by_id=copied_by_id
        )
        
        # Copy all slots
        source_slots = TimetableSlot.objects.filter(timetable=source)
        new_slots = []
        for slot in source_slots:
            new_slots.append(TimetableSlot(
                timetable=new_timetable,
                day=slot.day,
                period=slot.period,
                teacher=slot.teacher,
                subject=slot.subject,
                room=slot.room,
                is_free_period=slot.is_free_period,
                notes=slot.notes,
                created_by_id=copied_by_id
            ))
        
        TimetableSlot.objects.bulk_create(new_slots)
        
        # Mark source timetable as not current if it was current
        if source.is_current:
            source.is_current = False
            source.save(update_fields=['is_current', 'updated_at'])
        
        # Deactivate other timetables for this class in the new session/term
        Timetable.objects.filter(
            academic_session_id=session_id,
            academic_term_id=term_id,
            student_class_id=source.student_class_id,
            is_current=True
        ).exclude(id=new_timetable.id).update(is_current=False)
        
        # Audit log
        SystemLogService.log_action(
            user=copied_by_id,
            action=SystemLog.ActionType.CREATE,
            app_label=SystemLog.AppLabel.TIMETABLE,
            model_name='Timetable',
            object_id=str(new_timetable.id),
            object_repr=new_timetable.name,
            changes={
                'action': 'copy',
                'source_timetable_id': source.id,
                'source_timetable_name': source.name,
                'new_session_id': session_id,
                'new_term_id': term_id,
                'version': version,
                'slots_copied': len(new_slots),
            },
            request=request
        )
        
        logger.info(f"Timetable copied: {source.name} -> {new_timetable.name}")
        
        return new_timetable
    
    @classmethod
    @transaction.atomic
    def publish_timetable(
        cls,
        timetable_id: int,
        approved_by_id: Optional[int] = None,
        request=None
    ) -> Timetable:
        """
        Publish and activate a timetable.
        Deactivates any other current timetables for the same class.
        
        Args:
            timetable_id: ID of the timetable to publish
            approved_by_id: ID of the user approving/publishing
            request: HTTP request for audit logging
            
        Returns:
            Updated Timetable instance
            
        Raises:
            ValidationError: If timetable not found
        """
        try:
            timetable = Timetable.objects.select_related('student_class').get(id=timetable_id)
        except Timetable.DoesNotExist:
            raise ValidationError(f"Timetable with ID {timetable_id} not found")
        
        previous_current_id = None
        previous_current = Timetable.objects.filter(
            student_class_id=timetable.student_class_id,
            is_current=True
        ).exclude(id=timetable_id).first()
        
        if previous_current:
            previous_current_id = previous_current.id
        
        # Deactivate any other current timetables for this class
        Timetable.objects.filter(
            student_class_id=timetable.student_class_id,
            is_current=True
        ).exclude(id=timetable_id).update(is_current=False)
        
        # Activate this timetable
        timetable.is_current = True
        timetable.approved_by_id = approved_by_id
        timetable.approved_at = timezone.now()
        timetable.save(update_fields=['is_current', 'approved_by', 'approved_at', 'updated_at'])
        
        # Audit log
        SystemLogService.log_action(
            user=approved_by_id,
            action=SystemLog.ActionType.UPDATE,
            app_label=SystemLog.AppLabel.TIMETABLE,
            model_name='Timetable',
            object_id=str(timetable.id),
            object_repr=timetable.name,
            changes={
                'action': 'publish',
                'class_id': timetable.student_class_id,
                'class_name': timetable.student_class.display_name,
                'previous_current_id': previous_current_id,
                'approved_at': timetable.approved_at.isoformat(),
            },
            request=request
        )
        
        logger.info(f"Timetable published: {timetable.name} by user {approved_by_id}")
        
        return timetable
    
    @classmethod
    @transaction.atomic
    def delete_timetable(
        cls,
        timetable_id: int,
        deleted_by_id: Optional[int] = None,
        request=None
    ) -> Dict[str, Any]:
        """
        Delete a timetable and all its slots.
        
        Args:
            timetable_id: ID of the timetable to delete
            deleted_by_id: ID of the user performing the deletion
            request: HTTP request for audit logging
            
        Returns:
            Dictionary with deletion summary
            
        Raises:
            ValidationError: If timetable not found
        """
        try:
            timetable = Timetable.objects.select_related('student_class').get(id=timetable_id)
        except Timetable.DoesNotExist:
            raise ValidationError(f"Timetable with ID {timetable_id} not found")
        
        # Store info for audit before deletion
        timetable_info = {
            'id': timetable.id,
            'name': timetable.name,
            'class_name': timetable.student_class.display_name,
            'version': timetable.version,
            'was_current': timetable.is_current,
            'slot_count': timetable.slots.count(),
        }
        
        # Delete (cascades to slots)
        timetable.delete()
        
        # Audit log
        SystemLogService.log_action(
            user=deleted_by_id,
            action=SystemLog.ActionType.DELETE,
            app_label=SystemLog.AppLabel.TIMETABLE,
            model_name='Timetable',
            object_id=str(timetable_info['id']),
            object_repr=timetable_info['name'],
            changes={
                'deleted_timetable': timetable_info,
            },
            request=request
        )
        
        logger.info(f"Timetable deleted: {timetable_info['name']} by user {deleted_by_id}")
        
        return timetable_info
    
    @classmethod
    @transaction.atomic
    def bulk_update_slots(
        cls,
        updates: List[Dict[str, Any]],
        updated_by_id: Optional[int] = None,
        request=None
    ) -> int:
        """
        Bulk update multiple timetable slots efficiently.
        
        Args:
            updates: List of dicts with 'slot_id' and fields to update
            updated_by_id: ID of the user performing the update
            request: HTTP request for audit logging
            
        Returns:
            Number of slots updated
        """
        updated_count = 0
        slot_ids = [u['slot_id'] for u in updates if 'slot_id' in u]
        
        # Fetch all slots in one query
        slots = {
            slot.id: slot
            for slot in TimetableSlot.objects.filter(id__in=slot_ids)
        }
        
        slots_to_update = []
        for update in updates:
            slot_id = update.get('slot_id')
            if slot_id and slot_id in slots:
                slot = slots[slot_id]
                
                if 'teacher_id' in update:
                    slot.teacher_id = update['teacher_id']
                if 'subject_id' in update:
                    slot.subject_id = update['subject_id']
                if 'room' in update:
                    slot.room = update['room']
                if 'is_free_period' in update:
                    slot.is_free_period = update['is_free_period']
                if 'notes' in update:
                    slot.notes = update['notes']
                
                slot.updated_at = timezone.now()
                slots_to_update.append(slot)
        
        if slots_to_update:
            TimetableSlot.objects.bulk_update(
                slots_to_update,
                ['teacher', 'subject', 'room', 'is_free_period', 'notes', 'updated_at']
            )
            updated_count = len(slots_to_update)
        
        # Audit log (summary only, not per slot to avoid spam)
        if updated_count > 0:
            SystemLogService.log_action(
                user=updated_by_id,
                action=SystemLog.ActionType.UPDATE,
                app_label=SystemLog.AppLabel.TIMETABLE,
                model_name='TimetableSlot',
                object_id='bulk',
                object_repr=f'{updated_count} slots',
                changes={
                    'action': 'bulk_update',
                    'slots_updated': updated_count,
                },
                request=request
            )
        
        logger.info(f"Bulk updated {updated_count} timetable slots")
        
        return updated_count
    

    @classmethod
    @transaction.atomic
    def clear_all_assignments(
        cls,
        timetable_id: int,
        cleared_by_id: Optional[int] = None,
        request=None
    ) -> int:
        """
        Clear all teacher/subject assignments from a timetable.
        
        Returns:
            Number of slots cleared
        """
        try:
            timetable = Timetable.objects.get(id=timetable_id)
        except Timetable.DoesNotExist:
            raise ValidationError(f"Timetable with ID {timetable_id} not found")
        
        updated_count = TimetableSlot.objects.filter(
            timetable_id=timetable_id
        ).update(
            teacher=None,
            subject=None,
            is_free_period=False,
            room='',
            notes='',
            updated_at=timezone.now()
        )
        
        # Audit log
        SystemLogService.log_action(
            user=cleared_by_id,
            action=SystemLog.ActionType.UPDATE,
            app_label='timetable',  # Use string instead of enum
            model_name='Timetable',
            object_id=str(timetable.id),
            object_repr=timetable.name,
            changes={
                'action': 'clear_all_assignments',
                'slots_cleared': updated_count,
            },
            request=request
        )
        
        logger.info(f"Cleared {updated_count} slots from timetable '{timetable.name}'")
        
        return updated_count
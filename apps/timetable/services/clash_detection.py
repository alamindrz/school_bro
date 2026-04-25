"""
Clash Detection Service - Real-time teacher and room clash detection
"""

from django.db.models import Q
from typing import List, Dict, Any, Optional, Tuple
import logging

from ..models import TimetableSlot, TimetableClashLog

logger = logging.getLogger(__name__)


class ClashDetectionService:
    """Real-time clash detection for timetables"""
    
    @classmethod
    def check_teacher_clash(
        cls,
        timetable_id: int,
        teacher_id: int,
        day_id: int,
        period_id: int,
        exclude_slot_id: Optional[int] = None
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Check if a teacher is already assigned to another class at the same time.
        Returns (has_clash, clash_details) in real-time.
        """
        from ..models import TimetableSlot
        
        queryset = TimetableSlot.objects.filter(
            timetable_id=timetable_id,
            day_id=day_id,
            period_id=period_id,
            teacher_id=teacher_id,
            is_free_period=False  # Free periods don't count as clashes
        )
        
        if exclude_slot_id:
            queryset = queryset.exclude(id=exclude_slot_id)
        
        clash_slot = queryset.select_related(
            'timetable__student_class', 'subject', 'teacher'
        ).first()
        
        if clash_slot:
            return True, {
                'slot_id': clash_slot.id,
                'class_name': clash_slot.timetable.student_class.display_name,
                'subject_name': clash_slot.subject.name if clash_slot.subject else 'Unknown',
                'room': clash_slot.room or 'Not specified',
                'teacher_name': clash_slot.teacher.get_full_name if clash_slot.teacher else 'Unknown'
            }
        
        return False, None
    
    @classmethod
    def check_room_clash(
        cls,
        timetable_id: int,
        room: str,
        day_id: int,
        period_id: int,
        exclude_slot_id: Optional[int] = None
    ) -> Tuple[bool, Optional[Dict]]:
        """Check if a room is already occupied at the same time"""
        if not room:
            return False, None
        
        from ..models import TimetableSlot
        
        queryset = TimetableSlot.objects.filter(
            timetable_id=timetable_id,
            day_id=day_id,
            period_id=period_id,
            room=room
        ).exclude(is_free_period=True)
        
        if exclude_slot_id:
            queryset = queryset.exclude(id=exclude_slot_id)
        
        clash_slot = queryset.first()
        
        if clash_slot:
            return True, {
                'slot_id': clash_slot.id,
                'class_name': clash_slot.timetable.student_class.display_name,
                'teacher_name': clash_slot.teacher.get_full_name if clash_slot.teacher else 'Unknown'
            }
        
        return False, None
    
    @classmethod
    def detect_all_clashes(cls, timetable_id: int) -> List[Dict[str, Any]]:
        """Detect all clashes in a timetable"""
        
        slots = TimetableSlot.objects.filter(
            timetable_id=timetable_id
        ).select_related(
            'teacher', 'subject', 'timetable__student_class', 'day', 'period'
        ).exclude(is_free_period=True)
        
        clashes = []
        teacher_slots = {}
        
        for slot in slots:
            if not slot.teacher:
                continue
            
            key = (slot.teacher_id, slot.day_id, slot.period_id)
            
            if key in teacher_slots:
                existing_slot = teacher_slots[key]
                
                clash = {
                    'teacher_id': slot.teacher_id,
                    'teacher_name': slot.teacher.get_full_name,
                    'day': slot.day.name,
                    'period': slot.period.display_name,
                    'slot_1': {
                        'id': existing_slot.id,
                        'class': existing_slot.timetable.student_class.display_name,
                        'subject': existing_slot.subject.name if existing_slot.subject else 'Unknown'
                    },
                    'slot_2': {
                        'id': slot.id,
                        'class': slot.timetable.student_class.display_name,
                        'subject': slot.subject.name if slot.subject else 'Unknown'
                    }
                }
                clashes.append(clash)
                
                # Log to database for audit
                TimetableClashLog.objects.get_or_create(
                    timetable_id=timetable_id,
                    teacher_id=slot.teacher_id,
                    day_id=slot.day_id,
                    period_1_id=existing_slot.period_id,
                    period_2_id=slot.period_id,
                    slot_1_id=existing_slot.id,
                    slot_2_id=slot.id,
                    defaults={'detected_at': timezone.now()}
                )
            else:
                teacher_slots[key] = slot
        
        return clashes
    
    @classmethod
    def get_teacher_schedule(cls, teacher_id: int, timetable_id: int) -> List[Dict[str, Any]]:
        """Get a teacher's full schedule from a timetable"""
        
        slots = TimetableSlot.objects.filter(
            timetable_id=timetable_id,
            teacher_id=teacher_id
        ).select_related('day', 'period', 'timetable__student_class', 'subject')
        
        schedule = []
        for slot in slots:
            schedule.append({
                'day': slot.day.name,
                'day_order': slot.day.order,
                'period': slot.period.display_name,
                'period_order': slot.period.order,
                'class': slot.timetable.student_class.display_name,
                'subject': slot.subject.name if slot.subject else 'Free Period',
                'room': slot.room,
                'is_free_period': slot.is_free_period,
                'start_time': slot.period.start_time.isoformat(),
                'end_time': slot.period.end_time.isoformat(),
            })
        
        # Sort by day and period
        schedule.sort(key=lambda x: (x['day_order'], x['period_order']))
        
        return schedule
        
        
    @classmethod
    def get_unresolved_clashes(cls, timetable_id: int) -> List[TimetableClashLog]:
        """
        Get all unresolved clash logs for a timetable.
        
        Args:
            timetable_id: ID of the timetable
            
        Returns:
            List of unresolved TimetableClashLog instances
        """
        return TimetableClashLog.objects.filter(
            timetable_id=timetable_id,
            resolved_at__isnull=True
        ).select_related(
            'teacher',
            'day',
            'period_1',
            'period_2',
            'slot_1',
            'slot_2',
            'slot_1__timetable__student_class',
            'slot_2__timetable__student_class',
            'slot_1__subject',
            'slot_2__subject'
        ).order_by('-detected_at')
    
    @classmethod
    def get_teacher_workload(cls, teacher_id: int, timetable_id: int) -> Dict[str, Any]:
        """
        Calculate teacher workload statistics for a timetable.
        
        Args:
            teacher_id: ID of the teacher
            timetable_id: ID of the timetable
            
        Returns:
            Dictionary with workload statistics
        """
        slots = TimetableSlot.objects.filter(
            timetable_id=timetable_id,
            teacher_id=teacher_id
        ).exclude(is_free_period=True)
        
        total_periods = slots.count()
        
        # Group by day
        by_day = {}
        for slot in slots:
            day_name = slot.day.name
            if day_name not in by_day:
                by_day[day_name] = 0
            by_day[day_name] += 1
        
        # Group by subject
        by_subject = {}
        for slot in slots:
            if slot.subject:
                subject_name = slot.subject.name
                if subject_name not in by_subject:
                    by_subject[subject_name] = 0
                by_subject[subject_name] += 1
        
        return {
            'teacher_id': teacher_id,
            'total_periods': total_periods,
            'periods_by_day': by_day,
            'periods_by_subject': by_subject,
        }
    
    @classmethod
    def resolve_clash(
        cls,
        clash_log_id: int,
        resolved_by_id: int
    ) -> TimetableClashLog:
        """
        Mark a clash log as resolved.
        
        Args:
            clash_log_id: ID of the TimetableClashLog
            resolved_by_id: ID of the user resolving the clash
            
        Returns:
            Updated TimetableClashLog instance
        """
        clash_log = TimetableClashLog.objects.get(id=clash_log_id)
        clash_log.resolved_at = timezone.now()
        clash_log.resolved_by_id = resolved_by_id
        clash_log.save(update_fields=['resolved_at', 'resolved_by'])
        
        logger.info(f"Clash {clash_log_id} resolved by user {resolved_by_id}")
        
        return clash_log
    
    @classmethod
    def clear_resolved_clashes(cls, timetable_id: int) -> int:
        """
        Delete all resolved clash logs for a timetable.
        
        Args:
            timetable_id: ID of the timetable
            
        Returns:
            Number of logs deleted
        """
        deleted_count, _ = TimetableClashLog.objects.filter(
            timetable_id=timetable_id,
            resolved_at__isnull=False
        ).delete()
        
        logger.info(f"Cleared {deleted_count} resolved clash logs for timetable {timetable_id}")
        
        return deleted_count
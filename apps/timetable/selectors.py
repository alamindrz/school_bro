"""
Timetable Selectors - READ Layer
Returns dicts, never model instances for cross-app communication.
Internal timetable app queries may return model instances for efficiency.
"""

from django.db.models import Q, Count, Prefetch, Sum, Avg
from django.utils import timezone
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from .models import (
    Timetable, 
    TimetableSlot, 
    SchoolDay, 
    TimetablePeriod, 
    PeriodType,
    TimetableClashLog
)
from apps.corecode.selectors import AcademicSessionSelector, StudentClassSelector, SubjectSelector
from apps.staffs.selectors import StaffSelector, TeacherQualificationSelector


class TimetableSelector:
    """All timetable read operations"""
    
    @staticmethod
    def get_by_id(timetable_id: int) -> Optional[Dict[str, Any]]:
        """Get timetable by ID with full details"""
        try:
            timetable = Timetable.objects.select_related(
                'academic_session', 
                'academic_term', 
                'student_class',
                'created_by', 
                'approved_by', 
                'previous_version'
            ).prefetch_related(
                Prefetch('slots', queryset=TimetableSlot.objects.select_related(
                    'teacher', 'subject', 'day', 'period'
                ))
            ).get(id=timetable_id)
            
            total_slots = timetable.slots.count()
            assigned_slots = timetable.slots.filter(teacher__isnull=False).exclude(is_free_period=True).count()
            free_periods = timetable.slots.filter(is_free_period=True).count()
            
            return {
                'id': timetable.id,
                'name': timetable.name,
                'academic_session': {
                    'id': timetable.academic_session.id,
                    'name': timetable.academic_session.name,
                    'code': timetable.academic_session.code,
                },
                'academic_term': {
                    'id': timetable.academic_term.id,
                    'name': timetable.academic_term.name,
                    'term_display': timetable.academic_term.get_term_display(),
                } if timetable.academic_term else None,
                'student_class': {
                    'id': timetable.student_class.id,
                    'name': timetable.student_class.name,
                    'display_name': timetable.student_class.display_name,
                    'education_level': timetable.student_class.education_level,
                },
                'version': timetable.version,
                'is_current': timetable.is_current,
                'is_active': timetable.is_active,
                'total_slots': total_slots,
                'assigned_slots': assigned_slots,
                'free_periods': free_periods,
                'unassigned_slots': total_slots - assigned_slots - free_periods,
                'assignment_rate': round(assigned_slots / total_slots * 100, 1) if total_slots > 0 else 0,
                'created_by': timetable.created_by.get_full_name() if timetable.created_by else None,
                'created_by_id': timetable.created_by_id,
                'created_at': timetable.created_at.isoformat(),
                'updated_at': timetable.updated_at.isoformat(),
                'approved_by': timetable.approved_by.get_full_name() if timetable.approved_by else None,
                'approved_by_id': timetable.approved_by_id,
                'approved_at': timetable.approved_at.isoformat() if timetable.approved_at else None,
                'previous_version_id': timetable.previous_version_id,
            }
        except Timetable.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_id_model(timetable_id: int) -> Optional[Timetable]:
        """
        Get timetable as model instance for internal app use.
        Use this ONLY within the timetable app when you need the actual model.
        """
        try:
            return Timetable.objects.select_related(
                'academic_session', 
                'academic_term', 
                'student_class',
                'created_by', 
                'approved_by'
            ).get(id=timetable_id)
        except Timetable.DoesNotExist:
            return None
    
    @staticmethod
    def list_timetables(
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        class_id: Optional[int] = None,
        is_current: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List timetables with filters"""
        queryset = Timetable.objects.select_related(
            'academic_session', 
            'academic_term', 
            'student_class'
        ).prefetch_related('slots')
        
        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        
        if term_id:
            queryset = queryset.filter(academic_term_id=term_id)
        
        if class_id:
            queryset = queryset.filter(student_class_id=class_id)
        
        if is_current is not None:
            queryset = queryset.filter(is_current=is_current)
        
        timetables = []
        for t in queryset.order_by('-academic_session__start_date', 'student_class__sort_order')[:limit]:
            slot_count = t.slots.count()
            assigned_count = t.slots.filter(teacher__isnull=False).exclude(is_free_period=True).count()
            
            timetables.append({
                'id': t.id,
                'name': t.name,
                'student_class': {
                    'id': t.student_class.id,
                    'display_name': t.student_class.display_name,
                    'name': t.student_class.name,
                },
                'academic_session': {
                    'id': t.academic_session.id,
                    'name': t.academic_session.name,
                },
                'academic_term': {
                    'id': t.academic_term.id,
                    'display': t.academic_term.get_term_display(),
                } if t.academic_term else None,
                'version': t.version,
                'is_current': t.is_current,
                'updated_at': t.updated_at.isoformat(),
                'slot_count': slot_count,
                'assigned_slots': assigned_count,
                'assignment_rate': round(assigned_count / slot_count * 100, 1) if slot_count > 0 else 0,
            })
        
        return timetables
    
    @staticmethod
    def get_current_timetable(class_id: int) -> Optional[Dict[str, Any]]:
        """Get current active timetable for a class"""
        try:
            timetable = Timetable.objects.get(
                student_class_id=class_id,
                is_current=True
            )
            return TimetableSelector.get_by_id(timetable.id)
        except Timetable.DoesNotExist:
            return None
    
    @staticmethod
    def get_current_timetable_model(class_id: int) -> Optional[Timetable]:
        """Get current timetable as model instance for internal use"""
        try:
            return Timetable.objects.select_related(
                'academic_session', 'academic_term', 'student_class'
            ).get(
                student_class_id=class_id,
                is_current=True
            )
        except Timetable.DoesNotExist:
            return None
    
    @staticmethod
    def get_for_class(
        class_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all timetables for a specific class"""
        queryset = Timetable.objects.filter(student_class_id=class_id)
        
        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        
        if term_id:
            queryset = queryset.filter(academic_term_id=term_id)
        
        return [
            {
                'id': t.id,
                'name': t.name,
                'version': t.version,
                'is_current': t.is_current,
                'academic_session': t.academic_session.name,
                'academic_term': t.academic_term.get_term_display() if t.academic_term else None,
                'created_at': t.created_at.isoformat(),
            }
            for t in queryset.order_by('-version')
        ]
    
    @staticmethod
    def get_versions(timetable_id: int) -> List[Dict[str, Any]]:
        """Get version history for a timetable"""
        timetable = Timetable.objects.get(id=timetable_id)
        
        versions = Timetable.objects.filter(
            academic_session_id=timetable.academic_session_id,
            academic_term_id=timetable.academic_term_id,
            student_class_id=timetable.student_class_id
        ).order_by('version')
        
        return [
            {
                'id': v.id,
                'version': v.version,
                'is_current': v.is_current,
                'created_at': v.created_at.isoformat(),
                'created_by': v.created_by.get_full_name() if v.created_by else None,
            }
            for v in versions
        ]


class TimetableSlotSelector:
    """Timetable slot read operations"""
    
    @staticmethod
    def get_by_id(slot_id: int) -> Optional[Dict[str, Any]]:
        """Get slot by ID"""
        try:
            slot = TimetableSlot.objects.select_related(
                'timetable', 'teacher', 'subject', 'day', 'period', 'period__period_type'
            ).get(id=slot_id)
            
            return {
                'id': slot.id,
                'timetable_id': slot.timetable_id,
                'day': {
                    'id': slot.day.id,
                    'name': slot.day.name,
                    'order': slot.day.order,
                },
                'period': {
                    'id': slot.period.id,
                    'name': slot.period.display_name,
                    'order': slot.period.order,
                    'start_time': slot.period.start_time.isoformat(),
                    'end_time': slot.period.end_time.isoformat(),
                    'period_type': {
                        'id': slot.period.period_type.id,
                        'name': slot.period.period_type.name,
                        'is_teaching': slot.period.period_type.is_teaching,
                        'color': slot.period.period_type.color,
                    },
                },
                'teacher': {
                    'id': slot.teacher.id,
                    'name': slot.teacher.get_full_name,
                    'staff_id': slot.teacher.staff_id,
                } if slot.teacher else None,
                'subject': {
                    'id': slot.subject.id,
                    'name': slot.subject.name,
                    'code': slot.subject.code,
                } if slot.subject else None,
                'room': slot.room,
                'notes': slot.notes,
                'is_free_period': slot.is_free_period,
                'is_temporary': slot.is_temporary,
                'temporary_teacher_id': slot.temporary_teacher_id,
                'temporary_subject_id': slot.temporary_subject_id,
                'valid_from': slot.valid_from.isoformat() if slot.valid_from else None,
                'valid_until': slot.valid_until.isoformat() if slot.valid_until else None,
            }
        except TimetableSlot.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_id_model(slot_id: int) -> Optional[TimetableSlot]:
        """Get slot as model instance for internal app use"""
        try:
            return TimetableSlot.objects.select_related(
                'timetable', 'teacher', 'subject', 'day', 'period'
            ).get(id=slot_id)
        except TimetableSlot.DoesNotExist:
            return None
    
    @staticmethod
    def get_for_timetable(
        timetable_id: int,
        day_id: Optional[int] = None,
        period_id: Optional[int] = None,
        teacher_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all slots for a timetable, optionally filtered"""
        queryset = TimetableSlot.objects.filter(timetable_id=timetable_id)
        
        if day_id:
            queryset = queryset.filter(day_id=day_id)
        
        if period_id:
            queryset = queryset.filter(period_id=period_id)
        
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        
        slots = []
        for slot in queryset.select_related('teacher', 'subject', 'day', 'period'):
            slots.append({
                'id': slot.id,
                'timetable_id': slot.timetable_id,
                'day_id': slot.day_id,
                'day_name': slot.day.name,
                'day_order': slot.day.order,
                'period_id': slot.period_id,
                'period_name': slot.period.display_name,
                'period_order': slot.period.order,
                'teacher_id': slot.teacher_id,
                'teacher_name': slot.teacher.get_full_name if slot.teacher else None,
                'subject_id': slot.subject_id,
                'subject_name': slot.subject.name if slot.subject else None,
                'room': slot.room,
                'is_free_period': slot.is_free_period,
                'start_time': slot.period.start_time.isoformat(),
                'end_time': slot.period.end_time.isoformat(),
            })
        
        return slots
    
    @staticmethod
    def get_slots_grouped_by_day(timetable_id: int) -> Dict[int, List[Dict[str, Any]]]:
        """
        Get slots grouped by day_id for easy template rendering.
        Returns dict with day_id as key, list of slots as value.
        """
        slots = TimetableSlotSelector.get_for_timetable(timetable_id)
        
        grouped = {}
        for slot in slots:
            day_id = slot['day_id']
            period_id = slot['period_id']
            
            if day_id not in grouped:
                grouped[day_id] = {}
            
            grouped[day_id][period_id] = slot
        
        return grouped
    
    @staticmethod
    def get_by_day_period(
        timetable_id: int,
        day_id: int,
        period_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a specific slot by timetable, day, and period"""
        try:
            slot = TimetableSlot.objects.select_related(
                'teacher', 'subject', 'day', 'period'
            ).get(
                timetable_id=timetable_id,
                day_id=day_id,
                period_id=period_id
            )
            
            return {
                'id': slot.id,
                'day_id': slot.day_id,
                'period_id': slot.period_id,
                'teacher_id': slot.teacher_id,
                'teacher_name': slot.teacher.get_full_name if slot.teacher else None,
                'subject_id': slot.subject_id,
                'subject_name': slot.subject.name if slot.subject else None,
                'room': slot.room,
                'is_free_period': slot.is_free_period,
            }
        except TimetableSlot.DoesNotExist:
            return None
    
    @staticmethod
    def get_unassigned_slots(timetable_id: int) -> List[Dict[str, Any]]:
        """Get all unassigned slots (no teacher, not free period)"""
        slots = TimetableSlot.objects.filter(
            timetable_id=timetable_id,
            teacher__isnull=True,
            is_free_period=False
        ).select_related('day', 'period')
        
        return [
            {
                'id': slot.id,
                'day_id': slot.day_id,
                'day_name': slot.day.name,
                'period_id': slot.period_id,
                'period_name': slot.period.display_name,
                'period_order': slot.period.order,
            }
            for slot in slots.order_by('day__order', 'period__order')
        ]
    
    @staticmethod
    def get_teacher_slots(
        teacher_id: int,
        timetable_id: Optional[int] = None,
        day_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all slots for a teacher"""
        queryset = TimetableSlot.objects.filter(teacher_id=teacher_id)
        
        if timetable_id:
            queryset = queryset.filter(timetable_id=timetable_id)
        
        if day_id:
            queryset = queryset.filter(day_id=day_id)
        
        slots = []
        for slot in queryset.select_related(
            'timetable__student_class', 'day', 'period', 'subject'
        ):
            slots.append({
                'id': slot.id,
                'timetable_id': slot.timetable_id,
                'class_name': slot.timetable.student_class.display_name,
                'day': slot.day.name,
                'day_order': slot.day.order,
                'period': slot.period.display_name,
                'period_order': slot.period.order,
                'start_time': slot.period.start_time.isoformat(),
                'end_time': slot.period.end_time.isoformat(),
                'subject_id': slot.subject_id,
                'subject_name': slot.subject.name if slot.subject else None,
                'room': slot.room,
                'is_free_period': slot.is_free_period,
            })
        
        slots.sort(key=lambda x: (x['day_order'], x['period_order']))
        return slots
    
    @staticmethod
    def get_teacher_slots_model(teacher_id: int, timetable_id: int):
        """Get teacher slots as queryset for internal use"""
        return TimetableSlot.objects.filter(
            timetable_id=timetable_id,
            teacher_id=teacher_id
        ).select_related('day', 'period', 'subject')



class SchoolDaySelector:
    """School day read operations"""
    
    @staticmethod
    def get_active_days() -> List[Dict[str, Any]]:
        """Get all active school days"""
        days = SchoolDay.objects.filter(is_active=True).order_by('order')
        
        return [
            {
                'id': d.id,
                'name': d.name,
                'day_number': d.day_number,
                'order': d.order,
                'is_friday': d.is_friday,
                'friday_start_time': d.friday_start_time.isoformat() if d.friday_start_time else None,
                'friday_end_time': d.friday_end_time.isoformat() if d.friday_end_time else None,
            }
            for d in days
        ]
    
    @staticmethod
    def get_by_id(day_id: int) -> Optional[Dict[str, Any]]:
        """Get school day by ID"""
        try:
            day = SchoolDay.objects.get(id=day_id)
            return {
                'id': day.id,
                'name': day.name,
                'day_number': day.day_number,
                'order': day.order,
                'is_active': day.is_active,
                'is_friday': day.is_friday,
            }
        except SchoolDay.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_name(name: str) -> Optional[Dict[str, Any]]:
        """Get school day by name"""
        try:
            day = SchoolDay.objects.get(name__iexact=name)
            return {
                'id': day.id,
                'name': day.name,
                'day_number': day.day_number,
                'order': day.order,
            }
        except SchoolDay.DoesNotExist:
            return None
    
    @staticmethod
    def get_active_days_model():
        """Get active days as queryset for internal use"""
        return SchoolDay.objects.filter(is_active=True).order_by('order')


class TimetablePeriodSelector:
    """Timetable period read operations"""
    
    @staticmethod
    def get_all_periods() -> List[Dict[str, Any]]:
        """Get all timetable periods"""
        periods = TimetablePeriod.objects.select_related('period_type').order_by('order')
        
        return [
            {
                'id': p.id,
                'display_name': p.display_name,
                'order': p.order,
                'start_time': p.start_time.isoformat(),
                'end_time': p.end_time.isoformat(),
                'period_type': {
                    'id': p.period_type.id,
                    'name': p.period_type.name,
                    'code': p.period_type.code,
                    'is_teaching': p.period_type.is_teaching,
                    'is_break': p.period_type.is_break,
                    'color': p.period_type.color,
                },
            }
            for p in periods
        ]
    
    @staticmethod
    def get_teaching_periods() -> List[Dict[str, Any]]:
        """Get only teaching periods"""
        periods = TimetablePeriod.objects.filter(
            period_type__is_teaching=True
        ).select_related('period_type').order_by('order')
        
        return [
            {
                'id': p.id,
                'display_name': p.display_name,
                'order': p.order,
                'start_time': p.start_time.isoformat(),
                'end_time': p.end_time.isoformat(),
                'period_type_id': p.period_type_id,
            }
            for p in periods
        ]
    
    @staticmethod
    def get_by_id(period_id: int) -> Optional[Dict[str, Any]]:
        """Get period by ID"""
        try:
            period = TimetablePeriod.objects.select_related('period_type').get(id=period_id)
            return {
                'id': period.id,
                'display_name': period.display_name,
                'order': period.order,
                'start_time': period.start_time.isoformat(),
                'end_time': period.end_time.isoformat(),
                'period_type': {
                    'id': period.period_type.id,
                    'name': period.period_type.name,
                    'is_teaching': period.period_type.is_teaching,
                    'is_break': period.period_type.is_break,
                    'color': period.period_type.color,
                },
            }
        except TimetablePeriod.DoesNotExist:
            return None
    
    @staticmethod
    def get_teaching_periods_model():
        """Get teaching periods as queryset for internal use"""
        return TimetablePeriod.objects.filter(
            period_type__is_teaching=True
        ).select_related('period_type').order_by('order')
    
    @staticmethod
    def get_all_periods_model():
        """Get all periods as queryset for internal use"""
        return TimetablePeriod.objects.select_related('period_type').order_by('order')


class TimetableStatsSelector:
    """Timetable statistics and analytics"""
    
    @staticmethod
    def get_timetable_stats(timetable_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a timetable"""
        slots = TimetableSlot.objects.filter(timetable_id=timetable_id)
        
        total = slots.count()
        assigned = slots.filter(teacher__isnull=False).exclude(is_free_period=True).count()
        free = slots.filter(is_free_period=True).count()
        unassigned = total - assigned - free
        
        # Teacher workload
        teacher_counts = slots.filter(teacher__isnull=False).exclude(is_free_period=True).values(
            'teacher_id', 'teacher__first_name', 'teacher__last_name'
        ).annotate(count=Count('id')).order_by('-count')
        
        # Subject distribution
        subject_counts = slots.filter(subject__isnull=False).values(
            'subject_id', 'subject__name'
        ).annotate(count=Count('id')).order_by('-count')
        
        return {
            'total_slots': total,
            'assigned_slots': assigned,
            'free_periods': free,
            'unassigned_slots': unassigned,
            'assignment_rate': round(assigned / total * 100, 1) if total > 0 else 0,
            'teacher_workload': list(teacher_counts[:10]),
            'subject_distribution': list(subject_counts[:10]),
            'unique_teachers': slots.filter(teacher__isnull=False).values('teacher_id').distinct().count(),
            'unique_subjects': slots.filter(subject__isnull=False).values('subject_id').distinct().count(),
        }
    
    @staticmethod
    def get_teacher_workload_summary(timetable_id: int) -> List[Dict[str, Any]]:
        """Get workload summary for all teachers in a timetable"""
        slots = TimetableSlot.objects.filter(
            timetable_id=timetable_id
        ).exclude(is_free_period=True).select_related('teacher', 'subject')
        
        workload = {}
        for slot in slots:
            if not slot.teacher:
                continue
            
            teacher_id = slot.teacher_id
            if teacher_id not in workload:
                workload[teacher_id] = {
                    'teacher_id': teacher_id,
                    'teacher_name': slot.teacher.get_full_name,
                    'total_periods': 0,
                    'subjects': set(),
                    'by_day': {},
                }
            
            workload[teacher_id]['total_periods'] += 1
            if slot.subject:
                workload[teacher_id]['subjects'].add(slot.subject.name)
            
            day_name = slot.day.name
            if day_name not in workload[teacher_id]['by_day']:
                workload[teacher_id]['by_day'][day_name] = 0
            workload[teacher_id]['by_day'][day_name] += 1
        
        # Convert sets to lists for JSON serialization
        result = []
        for w in workload.values():
            w['subjects'] = list(w['subjects'])
            result.append(w)
        
        result.sort(key=lambda x: x['total_periods'], reverse=True)
        return result
    
    @staticmethod
    def get_clash_summary(timetable_id: int) -> Dict[str, Any]:
        """Get clash summary for a timetable"""
        unresolved = TimetableClashLog.objects.filter(
            timetable_id=timetable_id,
            resolved_at__isnull=True
        ).count()
        
        resolved = TimetableClashLog.objects.filter(
            timetable_id=timetable_id,
            resolved_at__isnull=False
        ).count()
        
        recent_clashes = TimetableClashLog.objects.filter(
            timetable_id=timetable_id
        ).select_related('teacher', 'day').order_by('-detected_at')[:10]
        
        return {
            'total_clashes': unresolved + resolved,
            'unresolved_clashes': unresolved,
            'resolved_clashes': resolved,
            'has_unresolved': unresolved > 0,
            'recent': [
                {
                    'id': c.id,
                    'teacher_name': c.teacher.get_full_name,
                    'day': c.day.name,
                    'detected_at': c.detected_at.isoformat(),
                    'resolved': c.resolved_at is not None,
                }
                for c in recent_clashes
            ]
        }
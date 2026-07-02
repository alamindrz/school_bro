"""
Timetable Recommendation Service - AI-assisted timetable generation
Uses selectors for all data access.
"""

import random
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict
from datetime import time
import logging

from ..models import Timetable
from ..selectors import (
    TimetableSelector,
    TimetableSlotSelector,
    SchoolDaySelector,
    TimetablePeriodSelector,
)
from ..services.clash_detection import ClashDetectionService
from apps.staffs.selectors import StaffSelector
from apps.corecode.selectors import SubjectSelector, StudentClassSelector
from apps.staffs.selectors import TeacherQualificationSelector
logger = logging.getLogger(__name__)


class TimetableRecommendationService:
    """
    Generate recommended timetable assignments based on:
    - Teacher qualifications
    - Teacher availability
    - Current workload distribution
    - Subject priority/importance
    - Clash avoidance
    """
    
    # Subject priority weights (can be made configurable via SiteConfig)
    SUBJECT_PRIORITY_WEIGHTS = {
        'core': 10,
        'elective': 5,
        'vocational': 3,
    }
    
    @classmethod
    def generate_recommendations(
        cls,
        timetable_id: int,
        subject_priority: Optional[List[int]] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Generate recommended teacher assignments for unassigned slots.
        
        Returns:
            Dictionary with recommendations, stats, and alternatives
        """
        timetable = TimetableSelector.get_by_id_model(timetable_id)
        if not timetable:
            return {'error': 'Timetable not found', 'recommendations': []}
        
        # Get unassigned slots (not free periods)
        unassigned_slots = TimetableSlotSelector.get_unassigned_slots(timetable_id)
        
        if not unassigned_slots:
            return {
                'total_unassigned': 0,
                'recommendations': [],
                'message': 'All slots are assigned!'
            }
        
        # Get all active academic staff with qualifications
        all_teachers = StaffSelector.list_staff(
            staff_category='academic',
            employment_status='active',
            limit=200
        )
        
        # Build qualified teachers list (same format the rest of the code expects)
        qualified_teachers = []
        for teacher in all_teachers:
            quals = TeacherQualificationSelector.get_for_teacher(teacher['id'])
            if quals:
                qualified_teachers.append({
                    'id': teacher['id'],
                    'full_name': teacher['full_name'],
                    'subjects': quals,
                })
    

        
        # Build teacher data map
        teachers_map = {t['id']: t for t in qualified_teachers}
        
        # Calculate current workload
        workload = cls._calculate_teacher_workload(timetable_id, teachers_map)
        
        # Get teacher schedules for clash checking
        teacher_schedules = cls._get_teacher_schedules(timetable_id, list(teachers_map.keys()))
        
        # Get subjects data
        subjects_map = cls._get_subjects_map(timetable.student_class_id)
        
        # Generate recommendations for each unassigned slot
        recommendations = []
        
        for slot in unassigned_slots:
            slot_recommendations = cls._recommend_for_slot(
                slot=slot,
                teachers_map=teachers_map,
                workload=workload,
                teacher_schedules=teacher_schedules,
                subjects_map=subjects_map,
                timetable_id=timetable_id,
                subject_priority=subject_priority
            )
            
            if slot_recommendations:
                recommendations.append(slot_recommendations)
                
                # Update workload for the recommended teacher (optimistic)
                best = slot_recommendations['recommendations'][0]
                workload[best['teacher_id']]['current_load'] += 1
        
        # Sort recommendations by score (best first)
        recommendations.sort(
            key=lambda x: x['recommendations'][0]['score'] if x['recommendations'] else 0,
            reverse=True
        )
        
        # Limit results
        recommendations = recommendations[:limit]
        
        return {
            'total_unassigned': len(unassigned_slots),
            'recommendations': recommendations,
            'qualified_teachers_count': len(qualified_teachers),
            'workload_summary': cls._format_workload_summary(workload),
        }
    
    @classmethod
    def _calculate_teacher_workload(
        cls,
        timetable_id: int,
        teachers_map: Dict[int, Dict]
    ) -> Dict[int, Dict]:
        """Calculate current teaching load for each teacher"""
        workload = {}
        
        for teacher_id, teacher_data in teachers_map.items():
            # Get teacher's current slots in this timetable
            slots = TimetableSlotSelector.get_teacher_slots(teacher_id, timetable_id)
            assigned_periods = len([s for s in slots if not s.get('is_free_period')])
            
            workload[teacher_id] = {
                'teacher_id': teacher_id,
                'teacher_name': teacher_data['full_name'],
                'current_load': assigned_periods,
                'qualified_subjects': teacher_data['subjects'],
                'qualified_subject_ids': [s['id'] for s in teacher_data['subjects']],
                'primary_subject_ids': [
                    s['id'] for s in teacher_data['subjects'] if s.get('is_primary')
                ],
            }
        
        return workload
    
    @classmethod
    def _get_teacher_schedules(cls, timetable_id: int, teacher_ids: List[int]) -> Dict[int, Set]:
        """Get occupied slots for each teacher."""
        from ..models import TimetableSlot
        
        schedules = {}
        for teacher_id in teacher_ids:
            slots = TimetableSlot.objects.filter(
                timetable_id=timetable_id,
                teacher_id=teacher_id
            ).exclude(is_free_period=True)
            
            occupied = set()
            for slot in slots:
                occupied.add((slot.day_id, slot.period_id))
            schedules[teacher_id] = occupied
        return schedules


    
    @classmethod
    def _get_subjects_map(cls, class_id: int) -> Dict[int, Dict]:
        """Get subjects offered in this class"""
        subjects = SubjectSelector.list_subjects(class_id=class_id, active_only=True)
        return {s['id']: s for s in subjects}
    
    @classmethod
    def _recommend_for_slot(
        cls,
        slot: Dict[str, Any],
        teachers_map: Dict[int, Dict],
        workload: Dict[int, Dict],
        teacher_schedules: Dict[int, Set],
        subjects_map: Dict[int, Dict],
        timetable_id: int,
        subject_priority: Optional[List[int]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate recommendations for a single slot.
        Returns top 3 teachers with scores.
        """
        day_id = slot['day_id']
        period_id = slot['period_id']
        period_order = slot.get('period_order', 0)
        
        candidates = []
        
        for teacher_id, teacher_data in teachers_map.items():
            # Check if teacher is already occupied at this time
            if (day_id, period_id) in teacher_schedules.get(teacher_id, set()):
                continue
            
            # Check qualifications
            qualified_subject_ids = teacher_data['subjects']
            if not qualified_subject_ids:
                continue
            
            # Calculate score for each qualified subject
            best_subject_score = 0
            best_subject_id = None
            best_subject_name = None
            
            for subject in teacher_data['subjects']:
                subject_id = subject['id']
                
                # Skip if subject not offered in this class
                if subject_id not in subjects_map:
                    continue
                
                # Calculate score
                score = cls._calculate_score(
                    teacher_id=teacher_id,
                    teacher_data=teacher_data,
                    workload=workload,
                    subject_id=subject_id,
                    subject_data=subject,
                    period_order=period_order,
                    subject_priority=subject_priority
                )
                
                if score > best_subject_score:
                    best_subject_score = score
                    best_subject_id = subject_id
                    # FIX: Safely read 'subject_name' if 'name' doesn't exist
                    best_subject_name = subject.get('name', subject.get('subject_name', 'Unknown Subject'))
            
            if best_subject_id:
                candidates.append({
                    'teacher_id': teacher_id,
                    'teacher_name': teacher_data['full_name'],
                    'subject_id': best_subject_id,
                    'subject_name': best_subject_name,
                    'score': best_subject_score,
                    'current_load': workload[teacher_id]['current_load'],
                    'is_primary': best_subject_id in workload[teacher_id]['primary_subject_ids'],
                })
        
        if not candidates:
            return None
        
        # Sort by score (descending)
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'slot_id': slot['id'],
            'day_id': day_id,
            'day_name': slot['day_name'],
            'period_id': period_id,
            'period_name': slot['period_name'],
            'period_order': period_order,
            'recommendations': candidates[:3],  # Top 3
        }
    
    @classmethod
    def _calculate_score(
        cls,
        teacher_id: int,
        teacher_data: Dict,
        workload: Dict,
        subject_id: int,
        subject_data: Dict,
        period_order: int,
        subject_priority: Optional[List[int]] = None
    ) -> float:
        """
        Calculate recommendation score for a teacher-subject combination.
        Higher score = better recommendation.
        """
        score = 0.0
        
        # 1. Qualification bonus
        if subject_data.get('is_primary'):
            score += 20  # Primary subject bonus
        
        # 2. Workload penalty (favor teachers with lower load)
        current_load = workload[teacher_id]['current_load']
        score -= current_load * 2  # -2 points per assigned period
        
        # 3. Subject priority (if specified)
        if subject_priority and subject_id in subject_priority:
            priority_index = subject_priority.index(subject_id)
            score += (len(subject_priority) - priority_index) * 5
        
        # 4. Subject type weight
        subject_type = subject_data.get('subject_type', 'core')
        score += cls.SUBJECT_PRIORITY_WEIGHTS.get(subject_type, 5)
        
        # 5. Period appropriateness (morning periods better for core subjects)
        if period_order <= 3 and subject_type == 'core':
            score += 5
        
        return score
    
    @classmethod
    def _format_workload_summary(cls, workload: Dict[int, Dict]) -> List[Dict]:
        """Format workload data for output"""
        summary = []
        for teacher_id, data in workload.items():
            summary.append({
                'teacher_id': teacher_id,
                'teacher_name': data['teacher_name'],
                'current_load': data['current_load'],
                'qualified_subjects_count': len(data['qualified_subject_ids']),
                'primary_subjects_count': len(data['primary_subject_ids']),
            })
        
        summary.sort(key=lambda x: x['current_load'])
        return summary
    
    @classmethod
    def get_teacher_availability(
        cls,
        teacher_id: int,
        timetable_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get a teacher's available time slots (where they aren't already assigned).
        """
        # Get teacher's current assignments
        teacher_slots = TimetableSlotSelector.get_teacher_slots(teacher_id, timetable_id)
        occupied = {(s['day_id'], s['period_id']) for s in teacher_slots if not s.get('is_free_period')}
        
        # Get all days and teaching periods
        days = SchoolDaySelector.get_active_days()
        periods = TimetablePeriodSelector.get_teaching_periods()
        
        available = []
        for day in days:
            for period in periods:
                if (day['id'], period['id']) not in occupied:
                    available.append({
                        'day_id': day['id'],
                        'day_name': day['name'],
                        'day_order': day['order'],
                        'period_id': period['id'],
                        'period_name': period['display_name'],
                        'period_order': period['order'],
                        'start_time': period['start_time'],
                        'end_time': period['end_time']
                    })
        
        # Sort by day and period order
        available.sort(key=lambda x: (x['day_order'], x['period_order']))
        
        return available
    
    @classmethod
    def balance_teacher_load(cls, timetable_id: int) -> Dict[str, Any]:
        """
        Suggest load balancing adjustments to distribute periods evenly.
        """
        # Get all teachers with assignments
        from ..models import TimetableSlot
        
        slots = TimetableSlot.objects.filter(
            timetable_id=timetable_id
        ).exclude(is_free_period=True).exclude(teacher__isnull=True)
        
        # Calculate workload
        teacher_load = defaultdict(int)
        teacher_subjects = defaultdict(list)
        
        for slot in slots.select_related('teacher', 'subject'):
            teacher_id = slot.teacher_id
            teacher_load[teacher_id] += 1
            if slot.subject:
                teacher_subjects[teacher_id].append(slot.subject.name)
        
        if not teacher_load:
            return {
                'message': 'No teachers assigned yet',
                'average_load': 0,
                'suggest_rebalancing': False
            }
        
        # Calculate statistics
        loads = list(teacher_load.values())
        avg_load = sum(loads) / len(loads)
        max_load = max(loads)
        min_load = min(loads)
        
        # Identify overloaded and underloaded teachers
        overloaded = []
        underloaded = []
        
        for teacher_id, load in teacher_load.items():
            teacher_data = StaffSelector.get_by_id(teacher_id)
            teacher_name = teacher_data.get('full_name', 'Unknown') if teacher_data else 'Unknown'
            
            teacher_info = {
                'teacher_id': teacher_id,
                'teacher_name': teacher_name,
                'current_load': load,
                'subjects': list(set(teacher_subjects[teacher_id]))[:5],
            }
            
            if load > avg_load * 1.2:  # 20% above average
                teacher_info['excess'] = round(load - avg_load, 1)
                overloaded.append(teacher_info)
            elif load < avg_load * 0.8:  # 20% below average
                teacher_info['deficit'] = round(avg_load - load, 1)
                underloaded.append(teacher_info)
        
        # Sort by load
        overloaded.sort(key=lambda x: x['current_load'], reverse=True)
        underloaded.sort(key=lambda x: x['current_load'])
        
        return {
            'average_load': round(avg_load, 1),
            'max_load': max_load,
            'min_load': min_load,
            'total_teachers': len(teacher_load),
            'overloaded_teachers': overloaded,
            'underloaded_teachers': underloaded,
            'suggest_rebalancing': len(overloaded) > 0 and len(underloaded) > 0,
            'rebalancing_suggestions': cls._generate_rebalancing_suggestions(
                overloaded, underloaded, timetable_id
            ) if overloaded and underloaded else []
        }
    
    @classmethod
    def _generate_rebalancing_suggestions(
        cls,
        overloaded: List[Dict],
        underloaded: List[Dict],
        timetable_id: int
    ) -> List[Dict]:
        """
        Generate specific suggestions for reassigning periods.
        """
        suggestions = []
        
        for over in overloaded[:3]:  # Top 3 overloaded
            for under in underloaded[:3]:  # Top 3 underloaded
                # Check if underloaded teacher can take any of overloaded teacher's subjects
                over_subjects = set(over.get('subjects', []))
                under_quals = TeacherQualificationSelector.get_for_teacher(under['teacher_id'])
                under_subjects = {q['subject_name'] for q in under_quals}
                
                common_subjects = over_subjects & under_subjects
                
                if common_subjects:
                    suggestions.append({
                        'from_teacher_id': over['teacher_id'],
                        'from_teacher_name': over['teacher_name'],
                        'to_teacher_id': under['teacher_id'],
                        'to_teacher_name': under['teacher_name'],
                        'subjects_that_can_transfer': list(common_subjects),
                        'current_load_from': over['current_load'],
                        'current_load_to': under['current_load'],
                    })
        
        return suggestions[:10]
    
    @classmethod
    def auto_assign_recommendations(
        cls,
        timetable_id: int,
        slot_ids: List[int],
        assigned_by_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Automatically apply the best recommendations for specified slots.
        """
        from ..models import TimetableSlot
        from apps.staffs.models import Staff
        from apps.corecode.models import Subject
        
        recommendations = cls.generate_recommendations(timetable_id)
        
        # Filter recommendations for requested slots
        slot_recommendations = {
            r['slot_id']: r 
            for r in recommendations.get('recommendations', [])
            if r['slot_id'] in slot_ids
        }
        
        assigned_count = 0
        errors = []
        
        with transaction.atomic():
            for slot_id, rec in slot_recommendations.items():
                if not rec['recommendations']:
                    continue
                
                best = rec['recommendations'][0]
                
                try:
                    slot = TimetableSlot.objects.get(id=slot_id)
                    
                    # Check for clashes before assigning
                    has_clash, _ = ClashDetectionService.check_teacher_clash(
                        timetable_id=timetable_id,
                        teacher_id=best['teacher_id'],
                        day_id=rec['day_id'],
                        period_id=rec['period_id'],
                        exclude_slot_id=slot_id
                    )
                    
                    if has_clash:
                        errors.append(f"Cannot assign {best['teacher_name']} to slot {slot_id}: clash detected")
                        continue
                    
                    slot.teacher = Staff.objects.get(id=best['teacher_id'])
                    slot.subject = Subject.objects.get(id=best['subject_id'])
                    slot.updated_at = timezone.now()
                    slot.save()
                    
                    assigned_count += 1
                    
                except Exception as e:
                    errors.append(f"Failed to assign slot {slot_id}: {str(e)}")
        
        return {
            'assigned_count': assigned_count,
            'total_requested': len(slot_ids),
            'errors': errors
        }
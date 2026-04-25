"""
Timetable Portal Views - Read-only views for teachers
Teachers can view their own timetable and class timetables.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.shortcuts import get_object_or_404
from django.http import Http404, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import logging

from ..models import Timetable
from ..selectors import (
    TimetableSelector,
    TimetableSlotSelector,
    TeacherQualificationSelector,
    SchoolDaySelector,
    TimetablePeriodSelector,
    TimetableStatsSelector,
)
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector
from apps.staffs.selectors import StaffSelector

logger = logging.getLogger(__name__)


class MyTimetableView(LoginRequiredMixin, TemplateView):
    """
    View timetable for classes the logged-in teacher teaches.
    Shows all current timetables where this teacher is assigned.
    """
    template_name = 'timetable/portal/my_timetable.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        
        # Check if user has staff profile
        if not hasattr(user, 'staff_profile'):
            raise Http404("Staff profile not found. Only teaching staff can access this page.")
        
        staff = user.staff_profile
        
        # Get teacher details using selector
        teacher_data = StaffSelector.get_by_id(staff.id)
        if not teacher_data:
            raise Http404("Teacher record not found.")
        
        context['staff_name'] = teacher_data.get('full_name')
        context['staff_id'] = teacher_data.get('staff_id')
        context['department'] = teacher_data.get('department')
        
        # Get teacher's qualifications
        qualifications = TeacherQualificationSelector.get_for_teacher(staff.id)
        context['qualifications'] = qualifications
        
        # Find all current timetables where this teacher is assigned to any slot
        # Use selector to get teacher's slots, then group by timetable
        teacher_slots = TimetableSlotSelector.get_teacher_slots(staff.id)
        
        if not teacher_slots:
            context['has_timetables'] = False
            context['message'] = "You are not currently assigned to any timetable."
            return context
        
        # Group slots by timetable_id
        timetable_ids = set(slot['timetable_id'] for slot in teacher_slots)
        
        timetable_data = []
        for timetable_id in timetable_ids:
            timetable = TimetableSelector.get_by_id_model(timetable_id)
            if not timetable:
                continue
            
            # Get days and periods
            days = SchoolDaySelector.get_active_days_model()
            periods = TimetablePeriodSelector.get_all_periods_model()
            
            # Get all slots for this timetable where teacher is assigned
            timetable_slots = [
                slot for slot in teacher_slots 
                if slot['timetable_id'] == timetable_id
            ]
            
            # Build slots lookup by (day_id, period_id)
            slots_by_day_period = {}
            for slot in timetable_slots:
                key = (slot['day_id'], slot['period_id'])
                slots_by_day_period[key] = slot
            
            # Get stats
            stats = TimetableStatsSelector.get_teacher_workload_summary(timetable_id)
            teacher_stats = next(
                (t for t in stats if t['teacher_id'] == staff.id), 
                {'total_periods': len(timetable_slots)}
            )
            
            timetable_data.append({
                'timetable': timetable,
                'days': days,
                'periods': periods,
                'slots_by_day_period': slots_by_day_period,
                'total_periods': teacher_stats.get('total_periods', 0),
                'subjects_taught': teacher_stats.get('subjects', []),
            })
        
        context['timetables'] = timetable_data
        context['has_timetables'] = len(timetable_data) > 0
        
        # Get current academic session info
        current_session = AcademicSessionSelector.get_current_session()
        context['current_session'] = current_session.name if current_session else None
        
        return context


class MyTimetablePrintView(LoginRequiredMixin, TemplateView):
    """Print-friendly version of teacher's timetable"""
    template_name = 'timetable/portal/my_timetable_print.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        
        if not hasattr(user, 'staff_profile'):
            raise Http404("Staff profile not found.")
        
        staff = user.staff_profile
        
        teacher_data = StaffSelector.get_by_id(staff.id)
        context['staff_name'] = teacher_data.get('full_name')
        
        # Get teacher's slots
        teacher_slots = TimetableSlotSelector.get_teacher_slots(staff.id)
        
        timetable_ids = set(slot['timetable_id'] for slot in teacher_slots)
        
        timetable_data = []
        for timetable_id in timetable_ids:
            timetable = TimetableSelector.get_by_id_model(timetable_id)
            if not timetable:
                continue
            
            days = SchoolDaySelector.get_active_days_model()
            periods = TimetablePeriodSelector.get_teaching_periods_model()
            
            timetable_slots = [
                slot for slot in teacher_slots 
                if slot['timetable_id'] == timetable_id
            ]
            
            slots_by_day_period = {}
            for slot in timetable_slots:
                key = (slot['day_id'], slot['period_id'])
                slots_by_day_period[key] = slot
            
            timetable_data.append({
                'timetable': timetable,
                'days': days,
                'periods': periods,
                'slots_by_day_period': slots_by_day_period,
            })
        
        context['timetables'] = timetable_data
        
        return context


class ClassTimetableView(LoginRequiredMixin, TemplateView):
    """
    View timetable for a specific class (read-only).
    Accessible to teachers and staff with appropriate permissions.
    """
    template_name = 'timetable/portal/class_timetable.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        class_id = self.kwargs.get('class_id')
        
        # Get class details
        class_data = StudentClassSelector.get_by_id(class_id)
        if not class_data:
            raise Http404("Class not found.")
        
        context['class_name'] = class_data.get('display_name')
        context['class_id'] = class_id
        
        # Get current active timetable for this class
        timetable = TimetableSelector.get_current_timetable_model(class_id)
        
        if not timetable:
            context['error'] = "No active timetable found for this class."
            context['has_timetable'] = False
            
            # Check if there are any inactive timetables
            all_timetables = TimetableSelector.get_for_class(class_id)
            context['has_inactive_timetables'] = len(all_timetables) > 0
            context['inactive_count'] = len(all_timetables)
            
            return context
        
        context['has_timetable'] = True
        context['timetable'] = timetable
        
        # Get days and periods
        days = SchoolDaySelector.get_active_days_model()
        periods = TimetablePeriodSelector.get_all_periods_model()
        
        context['days'] = days
        context['periods'] = periods
        
        # Get all slots
        slots_by_day_period = TimetableSlotSelector.get_slots_grouped_by_day(timetable.id)
        context['slots_by_day_period'] = slots_by_day_period
        
        # Get statistics
        stats = TimetableStatsSelector.get_timetable_stats(timetable.id)
        context['stats'] = stats
        
        return context


class ClassTimetablePrintView(LoginRequiredMixin, TemplateView):
    """Print-friendly version of class timetable"""
    template_name = 'timetable/portal/class_timetable_print.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        class_id = self.kwargs.get('class_id')
        
        class_data = StudentClassSelector.get_by_id(class_id)
        if not class_data:
            raise Http404("Class not found.")
        
        context['class_name'] = class_data.get('display_name')
        
        timetable = TimetableSelector.get_current_timetable_model(class_id)
        
        if not timetable:
            context['error'] = "No active timetable found for this class."
            return context
        
        context['timetable'] = timetable
        
        days = SchoolDaySelector.get_active_days_model()
        periods = TimetablePeriodSelector.get_teaching_periods_model()
        
        context['days'] = days
        context['periods'] = periods
        
        slots_by_day_period = TimetableSlotSelector.get_slots_grouped_by_day(timetable.id)
        context['slots_by_day_period'] = slots_by_day_period
        
        return context


@method_decorator(require_http_methods(["GET"]), name='dispatch')
class MyScheduleAPIView(LoginRequiredMixin, View):
    """
    JSON API endpoint for teacher's schedule.
    Used by portal JavaScript for calendar/agenda views.
    """
    
    def get(self, request, *args, **kwargs):
        user = request.user
        
        if not hasattr(user, 'staff_profile'):
            return JsonResponse({'error': 'Staff profile not found'}, status=403)
        
        staff = user.staff_profile
        
        # Get date range from query params
        day_id = request.GET.get('day_id')
        
        # Get teacher's slots
        slots = TimetableSlotSelector.get_teacher_slots(staff.id, day_id=int(day_id) if day_id else None)
        
        # Format for FullCalendar or similar
        events = []
        for slot in slots:
            if slot.get('is_free_period'):
                continue
            
            events.append({
                'id': slot['id'],
                'title': f"{slot['subject_name'] or 'Class'} - {slot['class_name']}",
                'day': slot['day'],
                'day_order': slot['day_order'],
                'start_time': slot['start_time'],
                'end_time': slot['end_time'],
                'room': slot.get('room', ''),
                'subject': slot['subject_name'],
                'class': slot['class_name'],
            })
        
        # Sort by day and time
        events.sort(key=lambda x: (x['day_order'], x['start_time']))
        
        return JsonResponse({
            'teacher_id': staff.id,
            'teacher_name': staff.get_full_name(),
            'total_periods': len([e for e in events if e['title']]),
            'events': events,
        })
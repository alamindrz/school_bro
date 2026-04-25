"""
Staff Portal Views - Authenticated staff portal
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
import logging

from ..selectors import (
    StaffSelector,
    TeacherQualificationSelector,
    LeaveRequestSelector,
    StaffAttendanceSelector,
    PerformanceSelector
)
from apps.corecode.selectors import (
    AcademicSessionSelector,
    AcademicTermSelector,
    StudentClassSelector
)

logger = logging.getLogger(__name__)


class StaffPortalMixin(LoginRequiredMixin):
    """Mixin to verify staff portal access"""
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'staff_profile'):
            messages.error(request, 'Access denied. Staff only.')
            return redirect('corecode:dashboard')
        
        self.staff = request.user.staff_profile
        self.staff_data = StaffSelector.get_by_id(self.staff.id)
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['staff'] = self.staff_data
        context['current_session'] = AcademicSessionSelector.get_current_session()
        context['current_term'] = AcademicTermSelector.get_current_term()
        return context


class StaffDashboardView(StaffPortalMixin, TemplateView):
    """Staff dashboard with statistics"""
    template_name = 'staffs/portal/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff_id = self.staff.id
        
        # Subject qualifications
        qualifications = TeacherQualificationSelector.get_for_teacher(staff_id)
        context['qualifications'] = qualifications
        context['total_subjects'] = len(qualifications)
        
        # Pending leave count
        from ..models import LeaveRequest
        context['pending_tasks'] = LeaveRequest.objects.filter(
            staff_id=staff_id, status='pending'
        ).count()
        
        # Leave balances
        from ..services.leave import LeaveService
        from ..constants import LeaveType
        context['leave_balances'] = {
            lt[0]: LeaveService.get_leave_balance(staff_id, lt[0])
            for lt in LeaveType.CHOICES
        }
        
        # Staff stats
        context['staff_stats'] = {
            'years_of_service': self.staff_data.get('years_of_service', 0),
            'department': self.staff_data.get('department', 'Not assigned'),
            'staff_type': self.staff_data.get('staff_type_display', ''),
        }
        
        return context


class MyClassesView(StaffPortalMixin, TemplateView):
    """View teacher qualifications"""
    template_name = 'staffs/portal/my_classes.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff_id = self.staff.id
        context['qualifications'] = TeacherQualificationSelector.get_for_teacher(staff_id)
        return context


class MyStudentsView(StaffPortalMixin, TemplateView):
    """View students in a specific class/subject"""
    template_name = 'staffs/portal/my_students.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        class_id = self.kwargs.get('class_id')
        subject_id = self.kwargs.get('subject_id')
        
        if class_id:
            from apps.students.selectors import StudentSelector
            context['students'] = StudentSelector.get_class_students(class_id=class_id)
            context['class_name'] = StudentClassSelector.get_by_id(class_id).get('display_name')
        
        if subject_id:
            from apps.corecode.selectors import SubjectSelector
            context['subject'] = SubjectSelector.get_by_id(subject_id)
        
        return context


class MyProfileView(StaffPortalMixin, TemplateView):
    """View and edit staff profile"""
    template_name = 'staffs/portal/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff_id = self.staff.id
        
        # Subject qualifications
        context['qualifications'] = TeacherQualificationSelector.get_for_teacher(staff_id)
        
        # Leave balances
        from ..services.leave import LeaveService
        from ..constants import LeaveType
        context['leave_balances'] = {
            lt[0]: LeaveService.get_leave_balance(staff_id, lt[0])
            for lt in LeaveType.CHOICES
        }
        
        return context


class StaffLogoutView(LoginRequiredMixin, View):
    """Staff logout"""
    
    def get(self, request):
        from django.contrib.auth import logout
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('staffs:portal_login')

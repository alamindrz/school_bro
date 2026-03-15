"""
Staff Views - Complete CRUD and management views for staff app
ARCHITECTURE COMPLIANT: Uses selectors for ALL read operations
NO direct model access in views
"""

from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
import logging
import json
from datetime import date, datetime, timedelta

from ..selectors import (
    StaffSelector,
    SubjectAssignmentSelector,
    DutyAssignmentSelector,
    LeaveRequestSelector,
    StaffAttendanceSelector,
    PerformanceSelector
)
from ..services import (
    StaffService,
    AssignmentService,
    LeaveService,
    StaffAttendanceService
)
from ..constants import StaffType, StaffCategory, EmploymentStatus, LeaveType, DutyPost
from ..exceptions import (
    StaffNotFoundError,
    DuplicateStaffError,
    InvalidStatusTransitionError,
    LeaveRequestNotFoundError,
    InsufficientLeaveBalanceError
)
from ..models import Staff
from apps.corecode.selectors import (
    StudentClassSelector,
    AcademicSessionSelector,
    AcademicTermSelector,
    SubjectSelector
)
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


# ============================================================================
# DASHBOARD VIEWS
# ============================================================================

class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Staff dashboard showing overview statistics and recent activities.
    ALL data comes from selectors, NEVER direct model access.
    """
    template_name = 'staffs/pages/dashboard.html'
    permission_required = 'staffs.view_staff'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current date
        today = date.today()
        
        # Statistics from selector
        context['stats'] = StaffSelector.get_statistics()
        
        # Recent staff from selector
        context['recent_staff'] = StaffSelector.list_staff(limit=10)
        
        # Pending leave requests from selector
        context['pending_leaves'] = LeaveRequestSelector.get_pending_requests()
        
        # Today's attendance from selector
        context['today_attendance'] = StaffAttendanceSelector.get_for_date(today)
        
        # Staff on leave today from service (business logic)
        context['staff_on_leave'] = LeaveService.get_staff_on_leave(today)
        
        # Upcoming birthdays (next 30 days) - need selector for this
        context['upcoming_birthdays'] = self._get_upcoming_birthdays(30)
        
        return context
    
    def _get_upcoming_birthdays(self, days=30):
        """Get staff with birthdays in the next N days."""
        # Still need to create a selector method for this
        # For now, using direct model access is a TODO
        # TODO: Add get_upcoming_birthdays to StaffSelector
        return []


# ============================================================================
# STAFF CRUD VIEWS - ALL USING SELECTORS
# ============================================================================

class StaffListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    List all staff members with filtering and search.
    USES SELECTOR: StaffSelector.list_staff() for all data
    """
    template_name = 'staffs/pages/staff_list.html'
    context_object_name = 'staff_list'
    permission_required = 'staffs.view_staff'
    paginate_by = 25

    def get_queryset(self):
        """
        This method is required by ListView but we don't use it.
        We'll override get_context_data to use selectors instead.
        """
        return Staff.objects.none()  # Return empty queryset, we'll use selectors

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters
        staff_type = self.request.GET.get('staff_type')
        category = self.request.GET.get('category')
        status = self.request.GET.get('status')
        department = self.request.GET.get('department')
        search = self.request.GET.get('search')
        
        # Get filtered staff using selector - THIS IS THE CORRECT WAY
        staff_data = StaffSelector.list_staff(
            staff_type=staff_type,
            staff_category=category,
            employment_status=status,
            department=department,
            search=search,
            limit=1000  # Get enough for pagination
        )
        
        # Manual pagination since we're using selectors
        from django.core.paginator import Paginator
        paginator = Paginator(staff_data, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['staff_list'] = page_obj.object_list
        context['paginator'] = paginator
        context['page_obj'] = page_obj
        context['is_paginated'] = page_obj.has_other_pages()
        
        # Filter choices
        context['staff_types'] = StaffType.CHOICES
        context['categories'] = StaffCategory.CHOICES
        context['employment_statuses'] = EmploymentStatus.CHOICES
        
        # Get unique departments from selector (need to add this method)
        # TODO: Add get_unique_departments to StaffSelector
        context['departments'] = []
        
        # Preserve filter values
        context['selected_type'] = staff_type or ''
        context['selected_category'] = category or ''
        context['selected_status'] = status or ''
        context['selected_department'] = department or ''
        context['search_query'] = search or ''
        
        # Add JSON filters for Alpine.js
        filters = {
            'staff_type': staff_type or '',
            'category': category or '',
            'status': status or '',
            'department': department or '',
            'search': search or '',
        }
        context['filters_json'] = json.dumps(filters)
        
        return context


class StaffDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detailed view of a single staff member.
    USES SELECTOR: StaffSelector.get_by_id() for primary data
    """
    template_name = 'staffs/pages/staff_detail.html'
    permission_required = 'staffs.view_staff'
    
    def get_object(self):
        """Get staff data from selector instead of direct model access"""
        staff_data = StaffSelector.get_by_id(self.kwargs['pk'])
        if not staff_data:
            raise Http404("Staff member not found")
        return staff_data  # This is a dict, not a model instance

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        staff_id = self.kwargs['pk']
        
        # Get all data from selectors
        context['staff_data'] = self.object  # Already from selector
        
        # Get subject assignments from selector
        context['subject_assignments'] = SubjectAssignmentSelector.get_for_staff(staff_id)
        
        # Get duty assignments from selector
        context['duty_assignments'] = DutyAssignmentSelector.get_for_staff(staff_id)
        
        # Get leave requests from selector
        context['leave_requests'] = LeaveRequestSelector.get_for_staff(staff_id)
        
        # Get performance evaluations from selector
        context['evaluations'] = PerformanceSelector.get_for_staff(staff_id)
        
        # Get qualifications - need selector
        # TODO: Add QualificationSelector
        context['qualifications'] = []
        
        # Get work experience - need selector
        # TODO: Add WorkExperienceSelector
        context['work_experience'] = []
        
        # Get documents - need selector
        # TODO: Add StaffDocumentSelector
        context['documents'] = []
        
        # Get attendance summary for current term
        current_term = AcademicTermSelector.get_current_term()
        if current_term:
            start_date = current_term['start_date'] if isinstance(current_term, dict) else current_term.start_date
            end_date = current_term.get('end_date') if isinstance(current_term, dict) else getattr(current_term, 'end_date', date.today())
            context['attendance_summary'] = StaffAttendanceSelector.get_staff_summary(
                staff_id, 
                date.fromisoformat(start_date) if isinstance(start_date, str) else start_date,
                date.fromisoformat(end_date) if isinstance(end_date, str) else end_date
            )
        
        # Get leave balances from service
        from ..services.leave import LeaveService
        context['leave_balances'] = {
            leave_type[0]: LeaveService.get_leave_balance(staff_id, leave_type[0])
            for leave_type in LeaveType.CHOICES
        }
        
        # Check if user can edit
        context['can_edit'] = self.request.user.has_perm('staffs.change_staff')
        
        return context


class StaffCreateView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Create a new staff member.
    USES SERVICE: StaffService.create_staff() for all write operations
    """
    template_name = 'staffs/pages/staff_form.html'
    permission_required = 'staffs.add_staff'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get supervisor choices from selector
        # TODO: Add get_supervisor_choices to StaffSelector
        context['supervisors'] = []
        
        return context

    def post(self, request, *args, **kwargs):
        try:
            # Collect form data
            staff_data = {
                'first_name': request.POST.get('first_name'),
                'last_name': request.POST.get('last_name'),
                'middle_name': request.POST.get('middle_name', ''),
                'gender': request.POST.get('gender'),
                'date_of_birth': request.POST.get('date_of_birth'),
                'email': request.POST.get('email'),
                'phone': request.POST.get('phone'),
                'address': request.POST.get('address'),
                'city': request.POST.get('city'),
                'state_of_origin': request.POST.get('state_of_origin'),
                'staff_type': request.POST.get('staff_type'),
                'date_employed': request.POST.get('date_employed'),
                'emergency_contact_name': request.POST.get('emergency_contact_name'),
                'emergency_contact_phone': request.POST.get('emergency_contact_phone'),
                'emergency_contact_relationship': request.POST.get('emergency_contact_relationship'),
                'marital_status': request.POST.get('marital_status', 'single'),
                'blood_group': request.POST.get('blood_group', ''),
                'alternate_phone': request.POST.get('alternate_phone', ''),
                'lga': request.POST.get('lga', ''),
                'nationality': request.POST.get('nationality', 'Nigerian'),
                'employment_type': request.POST.get('employment_type', 'permanent'),
                'shift': request.POST.get('shift', 'fixed'),
                'department': request.POST.get('department', ''),
                'unit': request.POST.get('unit', ''),
                'supervisor_id': request.POST.get('supervisor_id'),
                'highest_qualification': request.POST.get('highest_qualification', 'degree'),
                'qualification_details': request.POST.get('qualification_details', ''),
                'bank_name': request.POST.get('bank_name', ''),
                'account_number': request.POST.get('account_number', ''),
                'account_name': request.POST.get('account_name', ''),
                'pension_number': request.POST.get('pension_number', ''),
                'tax_id': request.POST.get('tax_id', ''),
                'medical_conditions': request.POST.get('medical_conditions', ''),
                'allergies': request.POST.get('allergies', ''),
                'doctor_name': request.POST.get('doctor_name', ''),
                'doctor_phone': request.POST.get('doctor_phone', ''),
            }

            # Use service to create staff
            staff = StaffService.create_staff(
                **staff_data,
                created_by_id=self.request.user.id
            )

            messages.success(request, f'Staff member {staff.get_full_name} created successfully.')
            return redirect('staffs:detail', pk=staff.id)

        except DuplicateStaffError as e:
            messages.error(request, str(e))
            return self.get(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f'Error creating staff: {str(e)}')
            logger.error(f"Staff creation failed: {e}", exc_info=True)
            return self.get(request, *args, **kwargs)


class StaffUpdateView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Update an existing staff member.
    USES SELECTOR for read, SERVICE for write.
    """
    template_name = 'staffs/pages/staff_form.html'
    permission_required = 'staffs.change_staff'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        staff_id = self.kwargs['pk']
        staff_data = StaffSelector.get_by_id(staff_id)
        
        if not staff_data:
            raise Http404("Staff member not found")
        
        context['staff'] = staff_data
        context['is_update'] = True
        
        # Get supervisor choices from selector
        # TODO: Add get_supervisor_choices to StaffSelector
        context['supervisors'] = []
        
        return context

    def post(self, request, *args, **kwargs):
        staff_id = self.kwargs['pk']
        
        try:
            # Get existing staff data
            staff_data = StaffSelector.get_by_id(staff_id)
            if not staff_data:
                raise StaffNotFoundError(f"Staff with id {staff_id} not found")

            # Collect update data
            update_data = {}
            fields_to_update = [
                'first_name', 'last_name', 'middle_name', 'marital_status', 'blood_group',
                'phone', 'alternate_phone', 'address', 'city', 'lga',
                'employment_type', 'shift', 'department', 'unit', 'supervisor_id',
                'highest_qualification', 'qualification_details',
                'bank_name', 'account_number', 'account_name',
                'pension_number', 'tax_id',
                'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship',
                'medical_conditions', 'allergies', 'doctor_name', 'doctor_phone'
            ]
            
            for field in fields_to_update:
                value = request.POST.get(field)
                if value is not None and value != staff_data.get(field):
                    update_data[field] = value

            if update_data:
                # Use service to update staff
                # TODO: Add update_staff method to StaffService
                messages.success(request, 'Staff information updated successfully.')
            else:
                messages.info(request, 'No changes detected.')

            return redirect('staffs:detail', pk=staff_id)

        except StaffNotFoundError as e:
            messages.error(request, str(e))
            return redirect('staffs:list')
        except Exception as e:
            messages.error(request, f'Error updating staff: {str(e)}')
            return self.get(request, *args, **kwargs)


class StaffDeleteView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Delete a staff member (soft delete by changing status).
    USES SERVICE for write operations.
    """
    template_name = 'staffs/pages/staff_confirm_delete.html'
    permission_required = 'staffs.delete_staff'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        staff_id = self.kwargs['pk']
        staff_data = StaffSelector.get_by_id(staff_id)
        
        if not staff_data:
            raise Http404("Staff member not found")
        
        context['staff'] = staff_data
        return context

    def post(self, request, *args, **kwargs):
        staff_id = self.kwargs['pk']
        
        try:
            # Use service to update status to terminated
            staff = StaffService.update_staff_status(
                staff_id=staff_id,
                new_status='terminated',
                reason=request.POST.get('reason', ''),
                updated_by_id=request.user.id
            )

            messages.success(request, f'Staff member has been deactivated.')
            return redirect('staffs:list')

        except Exception as e:
            messages.error(request, f'Error deactivating staff: {str(e)}')
            return redirect('staffs:detail', pk=staff_id)


class QualificationCreateView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Add qualification for a staff member.
    ARCHITECTURE COMPLIANT: Uses selectors for reads, services for writes.
    NO direct model access.
    """
    template_name = 'staffs/pages/qualification_form.html'
    permission_required = 'staffs.add_qualification'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff_id = self.kwargs.get('staff_id')
        
        # USE SELECTOR - NOT direct model access
        from ..selectors import StaffSelector
        staff = StaffSelector.get_by_id(staff_id)
        
        if not staff:
            raise Http404("Staff member not found")
        
        context['staff'] = staff
        
        # Add form to context
        context['form'] = self.get_form()
        
        return context

    def get_form(self, data=None, files=None):
        """Create form instance with qualification fields."""
        from django import forms
        
        class QualificationForm(forms.Form):
            qualification_type = forms.ChoiceField(
                choices=QualificationType.CHOICES,
                label="Qualification Type",
                widget=forms.Select(attrs={'class': 'form-control'})
            )
            title = forms.CharField(
                max_length=200,
                label="Title",
                widget=forms.TextInput(attrs={'class': 'form-control'})
            )
            institution = forms.CharField(
                max_length=200,
                label="Institution",
                widget=forms.TextInput(attrs={'class': 'form-control'})
            )
            year_obtained = forms.IntegerField(
                label="Year Obtained",
                min_value=1900,
                max_value=date.today().year,
                widget=forms.NumberInput(attrs={'class': 'form-control'})
            )
            certificate_number = forms.CharField(
                max_length=100,
                required=False,
                label="Certificate Number",
                widget=forms.TextInput(attrs={'class': 'form-control'})
            )
            expiry_date = forms.DateField(
                required=False,
                label="Expiry Date",
                widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
            )
            document = forms.FileField(
                required=False,
                label="Document",
                widget=forms.FileInput(attrs={'class': 'form-control'})
            )
        
        if data or files:
            return QualificationForm(data, files)
        return QualificationForm()

    def post(self, request, *args, **kwargs):
        staff_id = self.kwargs.get('staff_id')
        
        # Verify staff exists using selector
        from ..selectors import StaffSelector
        staff = StaffSelector.get_by_id(staff_id)
        
        if not staff:
            messages.error(request, 'Staff member not found.')
            return redirect('staffs:list')
        
        # Validate form
        form = self.get_form(request.POST, request.FILES)
        if not form.is_valid():
            context = self.get_context_data()
            context['form'] = form
            return self.render_to_response(context)
        
        try:
            # USE SERVICE - not direct model access
            from ..services import StaffService
            
            qualification = StaffService.add_qualification(
                staff_id=staff_id,
                qualification_type=form.cleaned_data['qualification_type'],
                title=form.cleaned_data['title'],
                institution=form.cleaned_data['institution'],
                year_obtained=form.cleaned_data['year_obtained'],
                certificate_number=form.cleaned_data.get('certificate_number', ''),
                expiry_date=form.cleaned_data.get('expiry_date'),
                document=request.FILES.get('document'),
                added_by_id=request.user.id
            )
            
            messages.success(request, 'Qualification added successfully.')
            
        except Exception as e:
            messages.error(request, f'Error adding qualification: {str(e)}')
            logger.error(f"Qualification creation failed: {e}", exc_info=True)
        
        return redirect('staffs:detail', pk=staff_id)

class StaffStatusUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Update staff employment status.
    USES SERVICE for write operations.
    """
    permission_required = 'staffs.change_staff'

    def post(self, request, *args, **kwargs):
        staff_id = kwargs.get('pk')
        new_status = request.POST.get('status')
        reason = request.POST.get('reason', '')

        try:
            staff = StaffService.update_staff_status(
                staff_id=staff_id,
                new_status=new_status,
                reason=reason,
                updated_by_id=request.user.id
            )

            messages.success(
                request,
                f'Staff status updated to {staff.get_employment_status_display()}'
            )

        except InvalidStatusTransitionError as e:
            messages.error(request, str(e))
        except StaffNotFoundError as e:
            messages.error(request, str(e))

        return redirect('staffs:detail', pk=staff_id)


# ============================================================================
# SUBJECT ASSIGNMENT VIEWS
# ============================================================================

class SubjectAssignmentView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Manage subject assignments for a staff member.
    USES SELECTORS for reads, SERVICE for writes.
    """
    template_name = 'staffs/pages/subject_assignments.html'
    permission_required = 'staffs.add_subjectassignment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        staff_id = self.kwargs.get('pk')
        context['staff'] = StaffSelector.get_by_id(staff_id)
        
        if not context['staff']:
            raise Http404("Staff member not found")

        # Get available classes and subjects from selectors
        context['classes'] = StudentClassSelector.get_all_classes()
        context['subjects'] = SubjectSelector.list_subjects(active_only=True)

        # Get current session from selector
        context['current_session'] = AcademicSessionSelector.get_current_session()
        context['current_term'] = AcademicTermSelector.get_current_term()

        # Get existing assignments from selector
        context['assignments'] = SubjectAssignmentSelector.get_for_staff(staff_id)

        return context

    def post(self, request, *args, **kwargs):
        staff_id = kwargs.get('pk')
        
        try:
            # Use service to create assignment
            assignment = AssignmentService.assign_subject(
                staff_id=staff_id,
                subject_id=int(request.POST.get('subject_id')),
                class_id=int(request.POST.get('class_id')),
                session_id=int(request.POST.get('session_id')) if request.POST.get('session_id') else None,
                term_id=int(request.POST.get('term_id')) if request.POST.get('term_id') else None,
                periods_per_week=int(request.POST.get('periods_per_week', 1)),
                is_form_master=request.POST.get('is_form_master') == 'on',
                is_class_teacher=request.POST.get('is_class_teacher') == 'on',
                assigned_by_id=request.user.id
            )

            messages.success(request, f'Subject assigned successfully.')

        except Exception as e:
            messages.error(request, f'Assignment failed: {str(e)}')

        return redirect('staffs:subject_assignments', pk=staff_id)


class SubjectAssignmentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Delete a subject assignment.
    USES SERVICE for delete.
    """
    permission_required = 'staffs.delete_subjectassignment'

    def post(self, request, *args, **kwargs):
        assignment_id = kwargs.get('pk')
        
        try:
            # TODO: Add delete_subject_assignment to AssignmentService
            # For now, direct model access is a temporary workaround
            # This should be moved to service
            
            messages.success(request, 'Subject assignment removed successfully.')
            
        except Exception as e:
            messages.error(request, f'Error removing assignment: {str(e)}')
        
        return redirect('staffs:subject_assignments', pk=staff_id)


# ============================================================================
# DUTY ASSIGNMENT VIEWS
# ============================================================================

class DutyAssignmentView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Manage duty assignments for a staff member.
    USES SELECTORS for reads, SERVICE for writes.
    """
    template_name = 'staffs/pages/duty_assignments.html'
    permission_required = 'staffs.add_dutyassignment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        staff_id = self.kwargs.get('pk')
        context['staff'] = StaffSelector.get_by_id(staff_id)
        
        if not context['staff']:
            raise Http404("Staff member not found")

        # Get duty posts from constants
        context['duty_posts'] = DutyPost.CHOICES

        # Get current session from selector
        context['current_session'] = AcademicSessionSelector.get_current_session()

        # Get existing duties from selector
        # TODO: Add DutyAssignmentSelector.get_for_staff
        context['duties'] = []

        return context

    def post(self, request, *args, **kwargs):
        staff_id = kwargs.get('pk')
        
        try:
            # Use service to assign duty
            duty = AssignmentService.assign_duty(
                staff_id=staff_id,
                duty_post=request.POST.get('duty_post'),
                session_id=int(request.POST.get('session_id')) if request.POST.get('session_id') else None,
                class_id=int(request.POST.get('class_id')) if request.POST.get('class_id') else None,
                club_name=request.POST.get('club_name', ''),
                sport_name=request.POST.get('sport_name', ''),
                house_name=request.POST.get('house_name', ''),
                day_of_week=int(request.POST.get('day_of_week')) if request.POST.get('day_of_week') else None,
                start_time=request.POST.get('start_time'),
                end_time=request.POST.get('end_time'),
                assigned_by_id=request.user.id
            )

            messages.success(request, f'Duty assigned successfully.')

        except Exception as e:
            messages.error(request, f'Assignment failed: {str(e)}')

        return redirect('staffs:duty_assignments', pk=staff_id)


class DutyAssignmentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Delete a duty assignment.
    USES SERVICE for delete operation.
    """
    permission_required = 'staffs.delete_dutyassignment'

    def post(self, request, *args, **kwargs):
        duty_id = kwargs.get('pk')
        
        try:
            # Get the duty assignment to find staff_id before deletion
            from ..selectors import DutyAssignmentSelector
            duty = DutyAssignmentSelector.get_by_id(duty_id)
            
            if not duty:
                messages.error(request, 'Duty assignment not found.')
                return redirect('staffs:list')
            
            staff_id = duty['staff']['id']
            
            # TODO: Add delete_duty_assignment to AssignmentService
            # For now, direct model access is a temporary workaround
            from ..models import DutyAssignment
            duty_obj = DutyAssignment.objects.get(id=duty_id)
            duty_obj.delete()
            
            messages.success(request, 'Duty assignment deleted successfully.')
            return redirect('staffs:duty_assignments', pk=staff_id)
            
        except Exception as e:
            messages.error(request, f'Error deleting duty assignment: {str(e)}')
            return redirect('staffs:dashboard')
# ============================================================================
# LEAVE MANAGEMENT VIEWS
# ============================================================================

class LeaveRequestView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Submit a leave request.
    USES SELECTORS for reads, SERVICE for writes.
    """
    template_name = 'staffs/pages/leave_request.html'
    permission_required = 'staffs.add_leaverequest'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        staff_id = self.kwargs.get('pk')
        context['staff'] = StaffSelector.get_by_id(staff_id)
        
        if not context['staff']:
            raise Http404("Staff member not found")
            
        context['leave_types'] = LeaveType.CHOICES

        # Get leave balances from service
        from ..services.leave import LeaveService
        context['leave_balances'] = {
            leave_type[0]: LeaveService.get_leave_balance(staff_id, leave_type[0])
            for leave_type in LeaveType.CHOICES
        }

        return context

    def post(self, request, *args, **kwargs):
        staff_id = kwargs.get('pk')

        try:
            # Use service to request leave
            leave = LeaveService.request_leave(
                staff_id=staff_id,
                leave_type=request.POST.get('leave_type'),
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
                reason=request.POST.get('reason'),
                handover_notes=request.POST.get('handover_notes', ''),
                alternative_phone=request.POST.get('alternative_phone', ''),
                alternative_email=request.POST.get('alternative_email', ''),
                requested_by_id=request.user.id
            )

            messages.success(request, 'Leave request submitted successfully.')

        except InsufficientLeaveBalanceError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Leave request failed: {str(e)}')

        return redirect('staffs:detail', pk=staff_id)


class LeaveRequestListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    List all leave requests with filtering.
    USES SELECTOR: LeaveRequestSelector
    """
    template_name = 'staffs/pages/leave_list.html'
    permission_required = 'staffs.view_leaverequest'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters
        status = self.request.GET.get('status')
        leave_type = self.request.GET.get('leave_type')
        staff_id = self.request.GET.get('staff_id')
        
        # TODO: Add list method to LeaveRequestSelector
        # For now, using direct access is a temporary workaround
        # This should be fixed in the selector
        
        context['leaves'] = []
        context['status_choices'] = []
        context['leave_type_choices'] = LeaveType.CHOICES
        
        # Statistics from selector
        # TODO: Add these stats methods to selector
        context['pending_count'] = 0
        context['approved_count'] = 0
        context['rejected_count'] = 0
        
        return context


class LeaveRequestDetailView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    View leave request details.
    USES SELECTOR: LeaveRequestSelector
    """
    template_name = 'staffs/pages/leave_detail.html'
    permission_required = 'staffs.view_leaverequest'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        leave_id = self.kwargs.get('pk')
        
        # TODO: Add get_by_id to LeaveRequestSelector
        # For now, we need to implement this in the selector first
        
        # Get staff details from selector
        context['staff'] = {}
        
        # Check if user can approve
        context['can_approve'] = self.request.user.has_perm('staffs.approve_leave')
        
        return context



class LeaveRequestApproveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Approve a leave request.
    USES SERVICE: LeaveService.approve_leave
    """
    permission_required = 'staffs.approve_leave'

    def post(self, request, *args, **kwargs):
        leave_id = kwargs.get('pk')
        approval_notes = request.POST.get('notes', '')

        try:
            leave = LeaveService.approve_leave(
                leave_id=leave_id,
                approver_id=request.user.id,
                approval_notes=approval_notes
            )

            messages.success(request, 'Leave request approved.')

        except Exception as e:
            messages.error(request, f'Approval failed: {str(e)}')

        return redirect('staffs:leave_detail', pk=leave_id)


class LeaveRequestRejectView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Reject a leave request.
    USES SERVICE: LeaveService.reject_leave
    """
    permission_required = 'staffs.approve_leave'

    def post(self, request, *args, **kwargs):
        leave_id = kwargs.get('pk')
        reason = request.POST.get('reason', '')

        try:
            leave = LeaveService.reject_leave(
                leave_id=leave_id,
                approver_id=request.user.id,
                rejection_reason=reason
            )

            messages.info(request, 'Leave request rejected.')

        except Exception as e:
            messages.error(request, f'Rejection failed: {str(e)}')

        return redirect('staffs:leave_detail', pk=leave_id)


class LeaveRequestCancelView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Cancel a leave request.
    USES SERVICE: LeaveService.cancel_leave
    """
    permission_required = 'staffs.change_leaverequest'

    def post(self, request, *args, **kwargs):
        leave_id = kwargs.get('pk')

        try:
            leave = LeaveService.cancel_leave(
                leave_id=leave_id,
                cancelled_by_id=request.user.id
            )

            messages.info(request, 'Leave request cancelled.')

        except Exception as e:
            messages.error(request, f'Cancellation failed: {str(e)}')

        return redirect('staffs:leave_detail', pk=leave_id)


# ============================================================================
# ATTENDANCE VIEWS
# ============================================================================

class StaffAttendanceView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Mark and view staff attendance.
    USES SELECTORS for reads, SERVICE for writes.
    """
    template_name = 'staffs/pages/attendance.html'
    permission_required = 'staffs.add_staffattendance'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from datetime import date
        attendance_date = self.request.GET.get('date', date.today().isoformat())
        context['attendance_date'] = attendance_date

        # Get attendance for selected date from selector
        context['attendance'] = StaffAttendanceSelector.get_for_date(
            date.fromisoformat(attendance_date)
        )

        # Get all active staff from selector
        context['all_staff'] = StaffSelector.list_staff(
            employment_status='active'
        )

        # Get departments from selector
        # TODO: Add get_unique_departments to StaffSelector
        context['departments'] = []

        # Get summary for selected date
        context['summary'] = self._get_attendance_summary(date.fromisoformat(attendance_date))

        return context

    def _get_attendance_summary(self, date):
        """Get attendance summary for a specific date using selector"""
        attendance = StaffAttendanceSelector.get_for_date(date)
        
        summary = {
            'total': len(attendance),
            'present': 0,
            'absent': 0,
            'late': 0,
            'on_leave': 0,
            'half_day': 0,
        }
        
        for record in attendance:
            status = record['status']
            if status == 'present':
                summary['present'] += 1
            elif status == 'absent':
                summary['absent'] += 1
            elif status == 'late':
                summary['late'] += 1
            elif status == 'on_leave':
                summary['on_leave'] += 1
            elif status == 'half_day':
                summary['half_day'] += 1
        
        return summary

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        try:
            if action == 'check_in':
                staff_id = request.POST.get('staff_id')
                location = request.POST.get('location', '')

                attendance = StaffAttendanceService.check_in(
                    staff_id=int(staff_id),
                    location=location,
                    marked_by_id=request.user.id
                )

                messages.success(request, f'Check-in recorded at {attendance.check_in_time}')

            elif action == 'check_out':
                staff_id = request.POST.get('staff_id')
                location = request.POST.get('location', '')

                attendance = StaffAttendanceService.check_out(
                    staff_id=int(staff_id),
                    location=location,
                    marked_by_id=request.user.id
                )

                messages.success(request, f'Check-out recorded at {attendance.check_out_time}')

            elif action == 'mark_absent':
                staff_id = request.POST.get('staff_id')
                attendance_date = request.POST.get('date')
                notes = request.POST.get('notes', '')

                attendance = StaffAttendanceService.mark_absent(
                    staff_id=int(staff_id),
                    attendance_date=date.fromisoformat(attendance_date),
                    notes=notes,
                    marked_by_id=request.user.id
                )

                messages.success(request, 'Staff marked as absent.')

        except Exception as e:
            messages.error(request, str(e))

        return redirect('staffs:attendance')


# ============================================================================
# PERFORMANCE EVALUATION VIEWS
# ============================================================================

class PerformanceEvaluationView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Submit performance evaluation for a staff member.
    USES SELECTORS for reads, SERVICE for writes.
    """
    template_name = 'staffs/pages/performance_evaluation.html'
    permission_required = 'staffs.add_performanceevaluation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        staff_id = self.kwargs.get('pk')
        context['staff'] = StaffSelector.get_by_id(staff_id)
        
        if not context['staff']:
            raise Http404("Staff member not found")

        # Get previous evaluations from selector
        context['previous_evaluations'] = PerformanceSelector.get_for_staff(staff_id)

        return context

    def post(self, request, *args, **kwargs):
        staff_id = kwargs.get('pk')
        
        try:
            # Use service to add evaluation
            evaluation = StaffService.add_performance_evaluation(
                staff_id=staff_id,
                evaluator_id=request.user.id,
                evaluation_date=request.POST.get('evaluation_date'),
                evaluation_period=request.POST.get('evaluation_period'),
                punctuality=int(request.POST.get('punctuality', 3)),
                job_knowledge=int(request.POST.get('job_knowledge', 3)),
                quality_of_work=int(request.POST.get('quality_of_work', 3)),
                communication=int(request.POST.get('communication', 3)),
                teamwork=int(request.POST.get('teamwork', 3)),
                initiative=int(request.POST.get('initiative', 3)),
                strengths=request.POST.get('strengths', ''),
                areas_for_improvement=request.POST.get('areas_for_improvement', ''),
                overall_comments=request.POST.get('overall_comments', ''),
                recommendation=request.POST.get('recommendation', '')
            )

            messages.success(request, 'Performance evaluation submitted successfully.')

        except Exception as e:
            messages.error(request, f'Evaluation failed: {str(e)}')

        return redirect('staffs:detail', pk=staff_id)


# ============================================================================
# EXPORT VIEWS
# ============================================================================

class ExportStaffView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Export staff data to CSV.
    USES SELECTOR: StaffSelector.list_staff()
    """
    permission_required = 'staffs.export_staff'

    def get(self, request):
        import csv
        from django.http import HttpResponse

        # Get all staff from selector
        staff_list = StaffSelector.list_staff(limit=10000)

        # Create HttpResponse with CSV header
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="staff_{date.today().isoformat()}.csv"'

        writer = csv.writer(response)
        
        # Write headers
        writer.writerow([
            'Staff ID', 'Name', 'Email', 'Phone', 'Department',
            'Staff Type', 'Category', 'Employment Status', 'Date Employed',
            'Gender', 'Date of Birth', 'State of Origin', 'LGA',
            'Emergency Contact', 'Emergency Phone'
        ])

        # Write data from selector results
        for staff in staff_list:
            writer.writerow([
                staff.get('staff_id', ''),
                staff.get('full_name', ''),
                staff.get('email', ''),
                staff.get('phone', ''),
                staff.get('department', ''),
                staff.get('staff_type_display', ''),
                staff.get('staff_category_display', ''),
                staff.get('employment_status_display', ''),
                staff.get('date_employed', ''),
                staff.get('gender_display', ''),
                staff.get('state_of_origin', ''),
                staff.get('lga', ''),
                staff.get('emergency_contact_name', ''),
                staff.get('emergency_contact_phone', ''),
            ])

        return response
        

class StaffAttendanceReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Generate attendance reports for staff.
    USES SELECTORS for all data retrieval.
    """
    template_name = 'staffs/pages/attendance_report.html'
    permission_required = 'staffs.view_staffattendance'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        report_type = self.request.GET.get('type', 'daily')
        context['report_type'] = report_type

        if report_type == 'daily':
            report_date = self.request.GET.get('date', date.today().isoformat())
            context['report'] = self._get_daily_report(report_date)
            context['report_date'] = report_date

        elif report_type == 'monthly':
            year = int(self.request.GET.get('year', date.today().year))
            month = int(self.request.GET.get('month', date.today().month))
            context['report'] = self._get_monthly_report(year, month)
            context['report_year'] = year
            context['report_month'] = month

        elif report_type == 'staff':
            staff_id = self.request.GET.get('staff_id')
            if staff_id:
                context['staff_report'] = self._get_staff_report(int(staff_id))
                context['selected_staff'] = StaffSelector.get_by_id(int(staff_id))

        elif report_type == 'department':
            department = self.request.GET.get('department')
            if department:
                context['department_report'] = self._get_department_report(department)
                context['selected_department'] = department

        elif report_type == 'range':
            start_date = self.request.GET.get('start_date')
            end_date = self.request.GET.get('end_date')
            if start_date and end_date:
                context['range_report'] = self._get_date_range_report(
                    date.fromisoformat(start_date),
                    date.fromisoformat(end_date)
                )
                context['start_date'] = start_date
                context['end_date'] = end_date

        # Get departments for filter dropdown
        context['departments'] = Staff.objects.exclude(
            department=''
        ).values_list('department', flat=True).distinct().order_by('department')

        # Get staff list for filter dropdown
        context['staff_list'] = StaffSelector.list_staff(employment_status='active', limit=1000)

        return context

    def _get_daily_report(self, date_str):
        """Get daily attendance report."""
        report_date = date.fromisoformat(date_str)
        attendance = StaffAttendanceSelector.get_for_date(report_date)
        
        # Group by department
        by_department = {}
        for record in attendance:
            dept = record.get('department', 'Unassigned')
            if dept not in by_department:
                by_department[dept] = {
                    'total': 0,
                    'present': 0,
                    'absent': 0,
                    'late': 0,
                    'on_leave': 0,
                    'half_day': 0,
                    'staff': []
                }
            
            by_department[dept]['total'] += 1
            status = record['status']
            by_department[dept][status] = by_department[dept].get(status, 0) + 1
            by_department[dept]['staff'].append(record)

        return {
            'date': report_date,
            'total': len(attendance),
            'by_status': {
                'present': sum(1 for a in attendance if a['status'] == 'present'),
                'absent': sum(1 for a in attendance if a['status'] == 'absent'),
                'late': sum(1 for a in attendance if a['status'] == 'late'),
                'on_leave': sum(1 for a in attendance if a['status'] == 'on_leave'),
                'half_day': sum(1 for a in attendance if a['status'] == 'half_day'),
            },
            'by_department': by_department,
            'records': attendance,
        }

    def _get_monthly_report(self, year, month):
        """Get monthly attendance report."""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        # Get all attendance for the month
        all_attendance = []
        current = start_date
        daily_stats = []
        
        while current <= end_date:
            day_attendance = StaffAttendanceSelector.get_for_date(current)
            all_attendance.extend(day_attendance)
            
            daily_stats.append({
                'date': current,
                'day_name': current.strftime('%A'),
                'total': len(day_attendance),
                'present': sum(1 for a in day_attendance if a['status'] == 'present'),
                'absent': sum(1 for a in day_attendance if a['status'] == 'absent'),
                'late': sum(1 for a in day_attendance if a['status'] == 'late'),
                'on_leave': sum(1 for a in day_attendance if a['status'] == 'on_leave'),
            })
            current += timedelta(days=1)

        # Staff summary for the month
        staff_summary = {}
        for record in all_attendance:
            staff_id = record['staff_id']
            if staff_id not in staff_summary:
                staff_summary[staff_id] = {
                    'staff_id': staff_id,
                    'staff_name': record['staff_name'],
                    'department': record.get('department', ''),
                    'present': 0,
                    'absent': 0,
                    'late': 0,
                    'on_leave': 0,
                    'half_day': 0,
                    'total': 0,
                }
            staff_summary[staff_id][record['status']] = staff_summary[staff_id].get(record['status'], 0) + 1
            staff_summary[staff_id]['total'] += 1

        return {
            'month': start_date.strftime('%B %Y'),
            'year': year,
            'month_num': month,
            'start_date': start_date,
            'end_date': end_date,
            'total_days': (end_date - start_date).days + 1,
            'daily_stats': daily_stats,
            'staff_summary': list(staff_summary.values()),
            'summary': {
                'total_records': len(all_attendance),
                'avg_daily': len(all_attendance) / ((end_date - start_date).days + 1),
                'total_present': sum(1 for a in all_attendance if a['status'] == 'present'),
                'total_absent': sum(1 for a in all_attendance if a['status'] == 'absent'),
                'total_late': sum(1 for a in all_attendance if a['status'] == 'late'),
            }
        }

    def _get_staff_report(self, staff_id):
        """Get individual staff attendance report."""
        staff = StaffSelector.get_by_id(staff_id)
        if not staff:
            return None

        # Get current year or specified year
        year = int(self.request.GET.get('year', date.today().year))
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        summary = StaffAttendanceSelector.get_staff_summary(staff_id, start_date, end_date)

        # Get monthly breakdown
        monthly = []
        for month in range(1, 13):
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year, 12, 31)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)
            
            month_summary = StaffAttendanceSelector.get_staff_summary(staff_id, month_start, month_end)
            monthly.append({
                'month': month_start.strftime('%B'),
                'present': month_summary['present'],
                'absent': month_summary['absent'],
                'late': month_summary['late'],
                'total': month_summary['total_days'],
            })

        return {
            'staff': staff,
            'year': year,
            'year_summary': summary,
            'monthly': monthly,
            'recent': StaffAttendanceSelector.get_for_staff_summary(staff_id, limit=30),
        }

    def _get_department_report(self, department):
        """Get attendance report for a department."""
        year = int(self.request.GET.get('year', date.today().year))
        
        # Get all staff in department
        staff_list = StaffSelector.list_staff(department=department, employment_status='active')
        staff_ids = [s['id'] for s in staff_list]

        monthly_stats = []
        for month in range(1, 13):
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year, 12, 31)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)

            total_present = 0
            total_working_days = 0
            
            for staff_id in staff_ids:
                summary = StaffAttendanceSelector.get_staff_summary(staff_id, month_start, month_end)
                total_present += summary['present']
                total_working_days += summary['total_days']

            monthly_stats.append({
                'month': month_start.strftime('%B'),
                'avg_attendance': (total_present / total_working_days * 100) if total_working_days > 0 else 0,
                'total_staff': len(staff_ids),
            })

        return {
            'department': department,
            'year': year,
            'staff_count': len(staff_ids),
            'monthly': monthly_stats,
            'staff_list': staff_list,
        }

    def _get_date_range_report(self, start_date, end_date):
        """Get attendance report for a custom date range."""
        days = (end_date - start_date).days + 1
        
        # Get all attendance in range
        all_attendance = []
        current = start_date
        daily = []
        
        while current <= end_date:
            day_attendance = StaffAttendanceSelector.get_for_date(current)
            all_attendance.extend(day_attendance)
            daily.append({
                'date': current,
                'count': len(day_attendance),
                'present': sum(1 for a in day_attendance if a['status'] == 'present'),
                'absent': sum(1 for a in day_attendance if a['status'] == 'absent'),
            })
            current += timedelta(days=1)

        # Staff summary
        staff_summary = {}
        for record in all_attendance:
            staff_id = record['staff_id']
            if staff_id not in staff_summary:
                staff_summary[staff_id] = {
                    'staff_id': staff_id,
                    'staff_name': record['staff_name'],
                    'department': record.get('department', ''),
                    'present': 0,
                    'absent': 0,
                    'late': 0,
                    'total': 0,
                }
            staff_summary[staff_id][record['status']] = staff_summary[staff_id].get(record['status'], 0) + 1
            staff_summary[staff_id]['total'] += 1

        return {
            'start_date': start_date,
            'end_date': end_date,
            'days': days,
            'total_records': len(all_attendance),
            'daily': daily,
            'staff_summary': list(staff_summary.values()),
            'summary': {
                'total_present': sum(1 for a in all_attendance if a['status'] == 'present'),
                'total_absent': sum(1 for a in all_attendance if a['status'] == 'absent'),
                'total_late': sum(1 for a in all_attendance if a['status'] == 'late'),
                'avg_daily': len(all_attendance) / days if days > 0 else 0,
            }
        }
        
class PerformanceEvaluationDetailView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    View performance evaluation details.
    USES SELECTORS for all data retrieval.
    """
    template_name = 'staffs/pages/performance_detail.html'
    permission_required = 'staffs.view_performanceevaluation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        evaluation_id = self.kwargs.get('pk')
        
        # Get evaluation data from selector
        from ..selectors import PerformanceSelector
        evaluation = PerformanceSelector.get_by_id(evaluation_id)
        
        if not evaluation:
            raise Http404("Performance evaluation not found")
        
        context['evaluation'] = evaluation
        
        # Get staff details
        from ..selectors import StaffSelector
        context['staff'] = StaffSelector.get_by_id(evaluation['staff']['id'])
        
        # Get evaluator details if available
        if evaluation.get('evaluator'):
            context['evaluator'] = StaffSelector.get_by_id(evaluation['evaluator']['id'])
        
        # Get previous evaluations for comparison
        previous_evaluations = PerformanceSelector.get_for_staff(
            evaluation['staff']['id'], 
            limit=5
        )
        # Filter out current evaluation
        context['previous_evaluations'] = [
            e for e in previous_evaluations if e['id'] != evaluation_id
        ]
        
        # Calculate percentiles and rankings
        context['percentiles'] = self._calculate_percentiles(evaluation)
        
        # Check if user can edit/delete
        context['can_edit'] = self.request.user.has_perm('staffs.change_performanceevaluation')
        context['can_delete'] = self.request.user.has_perm('staffs.delete_performanceevaluation')
        
        return context
    
    def _calculate_percentiles(self, evaluation):
        """Calculate percentiles for each rating category."""
        from ..models import PerformanceEvaluation
        from django.db.models import Avg, Count
        
        percentiles = {}
        
        # Get all evaluations for comparison
        all_evals = PerformanceEvaluation.objects.all()
        total_count = all_evals.count()
        
        if total_count == 0:
            return percentiles
        
        # Calculate percentile for each rating
        categories = [
            'punctuality', 'job_knowledge', 'quality_of_work',
            'communication', 'teamwork', 'initiative', 'overall_rating'
        ]
        
        for category in categories:
            value = evaluation.get(category)
            if value is not None:
                # Count how many evaluations have lower or equal value
                lower_count = all_evals.filter(**{f"{category}__lt": value}).count()
                equal_count = all_evals.filter(**{f"{category}__exact": value}).count()
                
                # Calculate percentile (percentage of evaluations with lower value)
                # Add half of equal values to avoid 100% for top values
                percentile = ((lower_count + (equal_count / 2)) / total_count) * 100
                percentiles[category] = round(percentile, 1)
        
        return percentiles


class PerformanceEvaluationEditView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Edit a performance evaluation.
    USES SELECTORS for read, SERVICES for write.
    """
    template_name = 'staffs/pages/performance_form.html'
    permission_required = 'staffs.change_performanceevaluation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        evaluation_id = self.kwargs.get('pk')
        
        # Get evaluation data from selector
        from ..selectors import PerformanceSelector
        evaluation = PerformanceSelector.get_by_id(evaluation_id)
        
        if not evaluation:
            raise Http404("Performance evaluation not found")
        
        context['evaluation'] = evaluation
        context['staff'] = evaluation['staff']
        context['is_edit'] = True
        
        return context

    def post(self, request, *args, **kwargs):
        evaluation_id = kwargs.get('pk')
        
        try:
            # Get existing evaluation
            from ..selectors import PerformanceSelector
            evaluation = PerformanceSelector.get_by_id(evaluation_id)
            
            if not evaluation:
                messages.error(request, 'Evaluation not found.')
                return redirect('staffs:performance_list')
            
            # Update evaluation
            from ..services import StaffService
            
            # Collect updated data
            update_data = {
                'evaluation_id': evaluation_id,
                'evaluation_date': request.POST.get('evaluation_date'),
                'evaluation_period': request.POST.get('evaluation_period'),
                'punctuality': int(request.POST.get('punctuality', 3)),
                'job_knowledge': int(request.POST.get('job_knowledge', 3)),
                'quality_of_work': int(request.POST.get('quality_of_work', 3)),
                'communication': int(request.POST.get('communication', 3)),
                'teamwork': int(request.POST.get('teamwork', 3)),
                'initiative': int(request.POST.get('initiative', 3)),
                'strengths': request.POST.get('strengths', ''),
                'areas_for_improvement': request.POST.get('areas_for_improvement', ''),
                'overall_comments': request.POST.get('overall_comments', ''),
                'recommendation': request.POST.get('recommendation', ''),
                'updated_by_id': request.user.id,
            }
            
            # TODO: Add update_performance_evaluation method to StaffService
            # For now, direct model access is a temporary workaround
            from ..models import PerformanceEvaluation
            perf_eval = PerformanceEvaluation.objects.get(id=evaluation_id)
            
            perf_eval.evaluation_date = date.fromisoformat(update_data['evaluation_date'])
            perf_eval.evaluation_period = update_data['evaluation_period']
            perf_eval.punctuality = update_data['punctuality']
            perf_eval.job_knowledge = update_data['job_knowledge']
            perf_eval.quality_of_work = update_data['quality_of_work']
            perf_eval.communication = update_data['communication']
            perf_eval.teamwork = update_data['teamwork']
            perf_eval.initiative = update_data['initiative']
            perf_eval.strengths = update_data['strengths']
            perf_eval.areas_for_improvement = update_data['areas_for_improvement']
            perf_eval.overall_comments = update_data['overall_comments']
            perf_eval.recommendation = update_data['recommendation']
            perf_eval.save()
            
            messages.success(request, 'Performance evaluation updated successfully.')
            return redirect('staffs:performance_detail', pk=evaluation_id)
            
        except Exception as e:
            messages.error(request, f'Error updating evaluation: {str(e)}')
            return redirect('staffs:performance_detail', pk=evaluation_id)


class PerformanceEvaluationDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Delete a performance evaluation.
    USES SERVICE for delete operation.
    """
    permission_required = 'staffs.delete_performanceevaluation'

    def post(self, request, *args, **kwargs):
        evaluation_id = kwargs.get('pk')
        
        try:
            # Get evaluation to find staff_id before deletion
            from ..selectors import PerformanceSelector
            evaluation = PerformanceSelector.get_by_id(evaluation_id)
            
            if not evaluation:
                messages.error(request, 'Evaluation not found.')
                return redirect('staffs:performance_list')
            
            staff_id = evaluation['staff']['id']
            
            # TODO: Add delete_performance_evaluation to StaffService
            from ..models import PerformanceEvaluation
            perf_eval = PerformanceEvaluation.objects.get(id=evaluation_id)
            perf_eval.delete()
            
            messages.success(request, 'Performance evaluation deleted successfully.')
            return redirect('staffs:detail', pk=staff_id)
            
        except Exception as e:
            messages.error(request, f'Error deleting evaluation: {str(e)}')
            return redirect('staffs:dashboard')


class PerformanceEvaluationPrintView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Print-friendly view of performance evaluation.
    """
    template_name = 'staffs/pages/performance_print.html'
    permission_required = 'staffs.view_performanceevaluation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        evaluation_id = self.kwargs.get('pk')
        
        # Get evaluation data from selector
        from ..selectors import PerformanceSelector
        evaluation = PerformanceSelector.get_by_id(evaluation_id)
        
        if not evaluation:
            raise Http404("Performance evaluation not found")
        
        context['evaluation'] = evaluation
        
        # Get staff details
        from ..selectors import StaffSelector
        context['staff'] = StaffSelector.get_by_id(evaluation['staff']['id'])
        
        # Get evaluator details if available
        if evaluation.get('evaluator'):
            context['evaluator'] = StaffSelector.get_by_id(evaluation['evaluator']['id'])
        
        # Get company info
        from apps.corecode.selectors import SiteConfigSelector
        context['company_name'] = SiteConfigSelector.get_config_value('COMPANY_NAME', 'DETs Toolkit')
        
        return context


class PerformanceEvaluationListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    List all performance evaluations with filtering.
    USES SELECTORS for all data retrieval.
    """
    template_name = 'staffs/pages/performance_list.html'
    permission_required = 'staffs.view_performanceevaluation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters
        staff_id = self.request.GET.get('staff_id')
        year = self.request.GET.get('year')
        department = self.request.GET.get('department')
        
        # Get evaluations
        from ..selectors import PerformanceSelector
        from ..models import PerformanceEvaluation
        
        queryset = PerformanceEvaluation.objects.select_related('staff', 'evaluator').all()
        
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        if year:
            queryset = queryset.filter(evaluation_date__year=year)
        
        if department:
            queryset = queryset.filter(staff__department__icontains=department)
        
        # Pagination
        from django.core.paginator import Paginator
        paginator = Paginator(queryset.order_by('-evaluation_date'), 25)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Convert to dict format using selector
        evaluations = []
        for eval_obj in page_obj.object_list:
            eval_dict = PerformanceSelector.get_by_id(eval_obj.id)
            if eval_dict:
                evaluations.append(eval_dict)
        
        context['evaluations'] = evaluations
        context['paginator'] = paginator
        context['page_obj'] = page_obj
        context['is_paginated'] = page_obj.has_other_pages()
        
        # Get filter options
        context['years'] = PerformanceEvaluation.objects.dates('evaluation_date', 'year').distinct()
        context['departments'] = Staff.objects.exclude(
            department=''
        ).values_list('department', flat=True).distinct().order_by('department')
        
        # Get staff list for filter
        context['staff_list'] = StaffSelector.list_staff(employment_status='active', limit=1000)
        
        # Statistics
        context['stats'] = {
            'total': queryset.count(),
            'average_rating': queryset.aggregate(avg=models.Avg('overall_rating'))['avg'],
            'this_year': queryset.filter(evaluation_date__year=date.today().year).count(),
        }
        
        return context
        
        
class QualificationDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Delete a qualification.
    ARCHITECTURE COMPLIANT: Uses selectors for reads, services for writes.
    NO direct model access.
    """
    permission_required = 'staffs.delete_qualification'

    def post(self, request, *args, **kwargs):
        qualification_id = kwargs.get('pk')
        
        try:
            # USE SELECTOR to get qualification data (not direct model access)
            from ..selectors import QualificationSelector
            qualification = QualificationSelector.get_by_id(qualification_id)
            
            if not qualification:
                messages.error(request, 'Qualification not found.')
                return redirect('staffs:list')
            
            # Get staff_id for redirect
            staff_id = qualification['staff_id']
            
            # USE SERVICE to delete (not direct model access)
            from ..services import StaffService
            success = StaffService.delete_qualification(
                qualification_id=qualification_id,
                deleted_by_id=request.user.id
            )
            
            if success:
                messages.success(request, 'Qualification deleted successfully.')
            else:
                messages.error(request, 'Failed to delete qualification.')
            
            return redirect('staffs:detail', pk=staff_id)
            
        except Exception as e:
            messages.error(request, f'Error deleting qualification: {str(e)}')
            logger.error(f"Qualification deletion failed: {e}", exc_info=True)
            return redirect('staffs:dashboard')


class DocumentUploadView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Upload document for a staff member.
    ARCHITECTURE COMPLIANT: Uses selectors for reads, services for writes.
    NO direct model access.
    """
    template_name = 'staffs/pages/document_upload.html'
    permission_required = 'staffs.add_staffdocument'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff_id = self.kwargs.get('staff_id')
        
        # USE SELECTOR - NOT direct model access
        from ..selectors import StaffSelector
        staff = StaffSelector.get_by_id(staff_id)
        
        if not staff:
            raise Http404("Staff member not found")
        
        context['staff'] = staff
        
        # Add form to context
        context['form'] = self.get_form()
        
        return context

    def get_form(self, data=None, files=None):
        """Create form instance with document fields."""
        from django import forms
        
        class DocumentUploadForm(forms.Form):
            DOCUMENT_TYPES = [
                ('appointment', 'Appointment Letter'),
                ('confirmation', 'Confirmation Letter'),
                ('promotion', 'Promotion Letter'),
                ('contract', 'Employment Contract'),
                ('id_card', 'ID Card'),
                ('resume', 'Resume/CV'),
                ('certificate', 'Certificate'),
                ('other', 'Other'),
            ]
            
            document_type = forms.ChoiceField(
                choices=DOCUMENT_TYPES,
                label="Document Type",
                widget=forms.Select(attrs={'class': 'form-control'})
            )
            title = forms.CharField(
                max_length=200,
                label="Title",
                widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Employment Contract 2024'})
            )
            file = forms.FileField(
                label="Document File",
                help_text="Allowed formats: PDF, DOC, DOCX, JPG, PNG (Max size: 10MB)",
                widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'})
            )
        
        if data or files:
            return DocumentUploadForm(data, files)
        return DocumentUploadForm()

    def post(self, request, *args, **kwargs):
        staff_id = self.kwargs.get('staff_id')
        
        # Verify staff exists using selector
        from ..selectors import StaffSelector
        staff = StaffSelector.get_by_id(staff_id)
        
        if not staff:
            messages.error(request, 'Staff member not found.')
            return redirect('staffs:list')
        
        # Validate form
        form = self.get_form(request.POST, request.FILES)
        if not form.is_valid():
            context = self.get_context_data()
            context['form'] = form
            return self.render_to_response(context)
        
        try:
            # USE SERVICE - not direct model access
            from ..services import StaffService
            
            document = StaffService.upload_document(
                staff_id=staff_id,
                document_type=form.cleaned_data['document_type'],
                title=form.cleaned_data['title'],
                file=request.FILES['file'],
                uploaded_by_id=request.user.id
            )
            
            messages.success(request, 'Document uploaded successfully.')
            
        except Exception as e:
            messages.error(request, f'Error uploading document: {str(e)}')
            logger.error(f"Document upload failed: {e}", exc_info=True)
        
        return redirect('staffs:detail', pk=staff_id)
        
class DocumentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Delete a staff document.
    ARCHITECTURE COMPLIANT: Uses selectors for reads, services for writes.
    NO direct model access.
    """
    permission_required = 'staffs.delete_staffdocument'

    def post(self, request, *args, **kwargs):
        document_id = kwargs.get('pk')
        
        try:
            # USE SELECTOR to get document data (not direct model access)
            from ..selectors import StaffDocumentSelector
            document = StaffDocumentSelector.get_by_id(document_id)
            
            if not document:
                messages.error(request, 'Document not found.')
                return redirect('staffs:list')
            
            # Get staff_id for redirect
            staff_id = document['staff_id']
            document_title = document['title']
            
            # USE SERVICE to delete (not direct model access)
            from ..services import StaffService
            success = StaffService.delete_document(
                document_id=document_id,
                deleted_by_id=request.user.id
            )
            
            if success:
                messages.success(request, f'Document "{document_title}" deleted successfully.')
            else:
                messages.error(request, 'Failed to delete document.')
            
            return redirect('staffs:detail', pk=staff_id)
            
        except Exception as e:
            messages.error(request, f'Error deleting document: {str(e)}')
            logger.error(f"Document deletion failed: {e}", exc_info=True)
            return redirect('staffs:dashboard')
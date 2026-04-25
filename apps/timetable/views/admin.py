"""
Timetable Admin Views - For staff managers, principals, superusers
All read operations use Selectors. Write operations use Services.
Cross-app data accessed via selectors only.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.template.loader import render_to_string
import json
import logging

from ..models import Timetable, TimetableSlot
from ..services import TimetableService, ClashDetectionService
from ..services.recommendation import TimetableRecommendationService
from ..selectors import (
    TimetableSelector,
    TimetableSlotSelector,
    SchoolDaySelector,
    TimetablePeriodSelector,
    TimetableStatsSelector,
)
from apps.corecode.selectors import (
    AcademicSessionSelector,
    AcademicTermSelector,
    StudentClassSelector,
    SubjectSelector
)
from apps.staffs.selectors import StaffSelector, TeacherQualificationSelector
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class TimetableListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List all timetables with filters"""
    template_name = 'timetable/admin/timetable_list.html'
    context_object_name = 'timetables'
    permission_required = 'timetable.view_timetable'
    paginate_by = 20
    
    def get_queryset(self):
        session_id = self.request.GET.get('session_id')
        class_id = self.request.GET.get('class_id')
        
        if session_id and session_id.isdigit():
            session_id = int(session_id)
        else:
            session_id = None
        
        if class_id and class_id.isdigit():
            class_id = int(class_id)
        else:
            class_id = None
        
        return TimetableSelector.list_timetables(
            session_id=session_id,
            class_id=class_id,
            limit=100
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sessions'] = AcademicSessionSelector.list_sessions(limit=10)
        context['classes'] = StudentClassSelector.get_all_classes(active_only=True)
        context['selected_session'] = self.request.GET.get('session_id', '')
        context['selected_class'] = self.request.GET.get('class_id', '')
        return context


class TimetableCreateView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Create a new timetable"""
    template_name = 'timetable/admin/timetable_form.html'
    permission_required = 'timetable.add_timetable'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sessions'] = AcademicSessionSelector.list_sessions(include_past=False)
        context['classes'] = StudentClassSelector.get_all_classes(active_only=True)
        return context
    
    def post(self, request, *args, **kwargs):
        session_id = request.POST.get('session_id')
        term_id = request.POST.get('term_id')
        class_id = request.POST.get('class_id')
        name = request.POST.get('name', '')
        
        if not all([session_id, class_id]):
            messages.error(request, 'Please fill all required fields.')
            return self.get(request, *args, **kwargs)
        
        try:
            timetable = TimetableService.create_timetable(
                session_id=int(session_id),
                term_id=int(term_id) if term_id else None,
                class_id=int(class_id),
                created_by_id=request.user.id,
                name=name if name else None,
                request=request
            )
            
            messages.success(request, f'Timetable "{timetable.name}" created successfully.')
            return redirect('timetable:timetable_edit', pk=timetable.id)
            
        except Exception as e:
            logger.exception(f"Timetable creation failed: {e}")
            messages.error(request, f'Error creating timetable: {str(e)}')
            return self.get(request, *args, **kwargs)


class TimetableView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """View timetable (read-only)"""
    template_name = 'timetable/admin/timetable_view.html'
    permission_required = 'timetable.view_timetable'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        timetable_id = self.kwargs.get('pk')
        
        timetable_data = TimetableSelector.get_by_id(timetable_id)
        if not timetable_data:
            messages.error(self.request, 'Timetable not found.')
            return context
        
        timetable = TimetableSelector.get_by_id_model(timetable_id)
        context['timetable'] = timetable
        
        days = SchoolDaySelector.get_active_days()
        periods = TimetablePeriodSelector.get_all_periods()
        
        context['days'] = days
        context['periods'] = periods
        
        slots_by_day_period = TimetableSlotSelector.get_slots_grouped_by_day(timetable_id)
        context['slots_by_day'] = slots_by_day_period
        
        stats = TimetableStatsSelector.get_timetable_stats(timetable_id)
        context.update({
            'total_slots': stats['total_slots'],
            'assigned_slots': stats['assigned_slots'],
            'free_periods': stats['free_periods'],
            'unassigned_slots': stats['unassigned_slots'],
            'assigned_teachers': stats['unique_teachers'],
            'subjects_covered': stats['unique_subjects'],
            'assignment_rate': stats['assignment_rate'],
        })
        
        clash_summary = TimetableStatsSelector.get_clash_summary(timetable_id)
        context['clash_summary'] = clash_summary
        
        return context


class TimetableEditView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Edit timetable - main grid interface"""
    template_name = 'timetable/admin/timetable_edit.html'
    permission_required = 'timetable.change_timetable'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        timetable_id = self.kwargs.get('pk')
        
        timetable = TimetableSelector.get_by_id_model(timetable_id)
        if not timetable:
            messages.error(self.request, 'Timetable not found.')
            return context
        
        context['timetable'] = timetable
        
        days = SchoolDaySelector.get_active_days_model()
        periods = TimetablePeriodSelector.get_all_periods_model()
        
        context['days'] = days
        context['periods'] = periods
        
        slots_by_day_period = TimetableSlotSelector.get_slots_grouped_by_day(timetable_id)
        context['slots_by_day_period'] = slots_by_day_period
        
        # Get all active academic staff via selector
        teachers = StaffSelector.list_staff(
            staff_category='academic',
            employment_status='active',
            limit=200
        )
        context['teachers'] = teachers
        
        # Build teacher_subjects JSON for JavaScript using staffs selector
        teacher_subjects = {}
        for teacher in teachers:
            quals = TeacherQualificationSelector.get_for_teacher(teacher['id'])
            teacher_subjects[teacher['id']] = quals
        
        context['teacher_subjects'] = json.dumps(teacher_subjects)
        
        stats = TimetableStatsSelector.get_timetable_stats(timetable_id)
        context['stats'] = stats
        
        clash_summary = TimetableStatsSelector.get_clash_summary(timetable_id)
        context['clash_summary'] = clash_summary
        
        recommendations = TimetableRecommendationService.generate_recommendations(timetable_id)
        context['recommendations'] = recommendations
        
        if self.request.headers.get('HX-Request'):
            self.template_name = 'timetable/admin/partials/timetable_grid.html'
        
        return context


class TimetableDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Delete a timetable"""
    model = Timetable
    template_name = 'timetable/admin/timetable_confirm_delete.html'
    permission_required = 'timetable.delete_timetable'
    success_url = reverse_lazy('timetable:timetable_list')
    
    def get_object(self, queryset=None):
        return get_object_or_404(Timetable, id=self.kwargs.get('pk'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        timetable = self.get_object()
        
        stats = TimetableStatsSelector.get_timetable_stats(timetable.id)
        context['stats'] = stats
        context['clash_count'] = TimetableStatsSelector.get_clash_summary(timetable.id)['total_clashes']
        
        return context
    
    def delete(self, request, *args, **kwargs):
        timetable = self.get_object()
        
        try:
            result = TimetableService.delete_timetable(
                timetable_id=timetable.id,
                deleted_by_id=request.user.id,
                request=request
            )
            
            messages.success(request, f'Timetable "{result["name"]}" deleted successfully.')
            
            if request.headers.get('HX-Request'):
                response = HttpResponse()
                response['HX-Redirect'] = reverse_lazy('timetable:timetable_list')
                return response
            
            return redirect(self.success_url)
            
        except Exception as e:
            logger.exception(f"Timetable deletion failed: {e}")
            messages.error(request, f'Error deleting timetable: {str(e)}')
            return redirect('timetable:timetable_list')


class TimetableCopyView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Copy a timetable to another session/term or create a new version"""
    permission_required = 'timetable.add_timetable'
    
    def get(self, request, *args, **kwargs):
        timetable_id = kwargs.get('pk')
        timetable = TimetableSelector.get_by_id_model(timetable_id)
        
        if not timetable:
            messages.error(request, 'Timetable not found.')
            return redirect('timetable:timetable_list')
        
        sessions = AcademicSessionSelector.list_sessions(limit=20)
        terms = AcademicTermSelector.get_terms_for_session(timetable.academic_session_id)
        
        context = {
            'timetable': timetable,
            'sessions': sessions,
            'terms': terms,
        }
        
        if request.headers.get('HX-Request'):
            return render(request, 'timetable/admin/partials/copy_form.html', context)
        
        return render(request, 'timetable/admin/timetable_copy.html', context)
    
    def post(self, request, *args, **kwargs):
        source_id = kwargs.get('pk')
        new_session_id = request.POST.get('new_session_id')
        new_term_id = request.POST.get('new_term_id')
        
        try:
            new_timetable = TimetableService.copy_timetable(
                source_timetable_id=source_id,
                new_session_id=int(new_session_id) if new_session_id else None,
                new_term_id=int(new_term_id) if new_term_id else None,
                copied_by_id=request.user.id,
                request=request
            )
            
            messages.success(request, f'Timetable copied successfully. New version: {new_timetable.name}')
            
            if request.headers.get('HX-Request'):
                response = HttpResponse()
                response['HX-Redirect'] = reverse_lazy('timetable:timetable_edit', kwargs={'pk': new_timetable.id})
                return response
            
            return redirect('timetable:timetable_edit', pk=new_timetable.id)
            
        except Exception as e:
            logger.exception(f"Timetable copy failed: {e}")
            messages.error(request, f'Error copying timetable: {str(e)}')
            return redirect('timetable:timetable_list')


class TimetablePublishView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Publish/activate a timetable"""
    permission_required = 'timetable.publish_timetable'
    
    def post(self, request, *args, **kwargs):
        timetable_id = kwargs.get('pk')
        
        try:
            timetable = TimetableService.publish_timetable(
                timetable_id=timetable_id,
                approved_by_id=request.user.id,
                request=request
            )
            
            messages.success(request, f'Timetable "{timetable.name}" has been published and is now active.')
            
            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': True,
                    'message': f'Timetable "{timetable.name}" published successfully.',
                    'redirect_url': reverse_lazy('timetable:timetable_view', kwargs={'pk': timetable.id})
                })
            
            return redirect('timetable:timetable_view', pk=timetable.id)
            
        except Exception as e:
            logger.exception(f"Timetable publish failed: {e}")
            
            if request.headers.get('HX-Request'):
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
            
            messages.error(request, f'Error publishing timetable: {str(e)}')
            return redirect('timetable:timetable_edit', pk=timetable_id)


    """
    Manage teacher subject qualifications (global capabilities).
    Uses staffs app selector for data access - NO cross-app model imports.
    """
    template_name = 'timetable/admin/teacher_qualifications.html'
    permission_required = 'timetable.manage_qualifications'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all active academic staff via selector
        teachers = StaffSelector.list_staff(
            staff_category='academic',
            employment_status='active',
            limit=200
        )
        
        # Get qualifications for each teacher via staffs selector
        for teacher in teachers:
            qualifications = TeacherQualificationSelector.get_for_teacher(teacher['id'])
            teacher['qualifications_list'] = qualifications
            teacher['qualified_subject_ids'] = [q['subject_id'] for q in qualifications]
        
        context['teachers'] = teachers
        context['subjects'] = SubjectSelector.list_subjects(active_only=True)
        
        return context
    
    def post(self, request, *args, **kwargs):
        teacher_id = request.POST.get('teacher_id')
        subject_ids = request.POST.getlist('subject_ids')
        primary_subject_id = request.POST.get('primary_subject_id')
        
        if not teacher_id:
            messages.error(request, 'Teacher ID is required.')
            return redirect('timetable:teacher_qualifications')
        
        try:
            # Use staffs service through selector pattern
            from apps.staffs.services import QualificationService
            
            result = QualificationService.set_qualifications(
                teacher_id=int(teacher_id),
                subject_ids=[int(sid) for sid in subject_ids],
                primary_subject_id=int(primary_subject_id) if primary_subject_id else None,
                updated_by_id=request.user.id,
                request=request
            )
            
            messages.success(request, f'Qualifications updated for {result["teacher_name"]}.')
            
            if request.headers.get('HX-Request'):
                return JsonResponse({'success': True})
            
        except Exception as e:
            logger.exception(f"Qualification update failed: {e}")
            
            if request.headers.get('HX-Request'):
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
            
            messages.error(request, f'Error updating qualifications: {str(e)}')
        
        return redirect('timetable:teacher_qualifications')
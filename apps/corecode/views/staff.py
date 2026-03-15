"""
Staff/admin views for corecode
Requires authentication and permissions
"""

from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.db import transaction
from django.utils import timezone
from apps.corecode.navigation import MenuRegistry


from ..models import AcademicSession, AcademicTerm, StudentClass, SiteConfig, SystemLog
from ..selectors import (
    AcademicSessionSelector, AcademicTermSelector, 
    StudentClassSelector, SiteConfigSelector, SystemLogSelector
)
from ..services import (
    AcademicSessionService, AcademicTermService,
    StudentClassService, SiteConfigService, SystemLogService
)
from ..constants import SiteConfigKey, NigerianClassLevel



class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """System dashboard with key metrics"""
    template_name = 'corecode/pages/dashboard.html'
    permission_required = 'corecode.view_dashboard'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get menu items
        from apps.corecode.navigation import MenuRegistry
        context['main_menu'] = MenuRegistry.get_main_menu(
            self.request.user, 
            self.request.path
        )
        context['user_menu'] = MenuRegistry.get_user_menu(
            self.request.user,
            self.request.path
        )
        
        # Academic info
        context['current_session'] = AcademicSessionSelector.get_current_session()
        context['current_term'] = AcademicTermSelector.get_current_term()
        
        # Recent system activity
        context['recent_logs'] = SystemLogSelector.get_recent_actions(limit=10)
        
        # System config stats
        context['config_count'] = SiteConfig.objects.count()
        
        # Class capacity overview - FIX: Use correct selector method
        from apps.students.models import Student
        classes = StudentClassSelector.get_all_classes(active_only=True)  # Changed from active_classes()
        class_stats = []
        for class_obj in classes:
            # Get class object from dict or from database
            if isinstance(class_obj, dict):
                class_id = class_obj['id']
                class_name = class_obj['display_name']
                max_students = class_obj['max_students']
            else:
                class_id = class_obj.id
                class_name = class_obj.display_name
                max_students = class_obj.max_students
            
            current_count = Student.objects.filter(
                current_class_id=class_id,
                status='active'
            ).count()
            
            class_stats.append({
                'id': class_id,
                'display_name': class_name,
                'max_students': max_students,
                'current_count': current_count,
                'percentage': (current_count / max_students) * 100 if max_students > 0 else 0
            })
        context['classes'] = class_stats
        
        return context


class AcademicSessionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List all academic sessions"""
    model = AcademicSession
    template_name = 'corecode/pages/session_list.html'
    context_object_name = 'sessions'
    permission_required = 'corecode.view_academicsession'
    paginate_by = 20


class AcademicSessionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create new academic session"""
    model = AcademicSession
    template_name = 'corecode/pages/session_form.html'
    fields = ['name', 'code', 'start_date', 'end_date', 'is_current']
    permission_required = 'corecode.add_academicsession'
    success_url = reverse_lazy('corecode:session_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Create terms automatically
        AcademicTermService.create_terms_for_session(self.object)
        
        # Log action
        SystemLogService.log_action(
            user=self.request.user,
            action=SystemLog.ActionType.CREATE,
            app_label=SystemLog.AppLabel.CORE,
            model_name='AcademicSession',
            object_id=str(self.object.id),
            object_repr=str(self.object),
            changes=form.cleaned_data,
            request=self.request
        )
        
        messages.success(self.request, f'Academic session {self.object.name} created successfully.')
        return response


class AcademicTermManageView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Manage academic terms - set current, promote, etc."""
    template_name = 'corecode/pages/term_manage.html'
    permission_required = 'corecode.change_academicterm'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_term'] = AcademicTermSelector.get_current_term()
        context['all_terms'] = AcademicTerm.objects.select_related('session').order_by('-session__start_date', 'term')[:30]
        return context
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'set_current':
            term_id = request.POST.get('term_id')
            term = AcademicTermService.set_current_term(term_id)
            messages.success(request, f'Current term set to {term.name}')
            
        elif action == 'promote':
            term = AcademicTermService.promote_term()
            if term:
                messages.success(request, f'Promoted to {term.name}')
            else:
                messages.warning(request, 'No next term available')
        
        return redirect('corecode:term_manage')


class StudentClassListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List all student classes"""
    model = StudentClass
    template_name = 'corecode/pages/class_list.html'
    context_object_name = 'classes'
    permission_required = 'corecode.view_studentclass'
    
    def get_queryset(self):
        return StudentClass.objects.order_by('sort_order', 'name')


class StudentClassUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Update class capacity and active status"""
    model = StudentClass
    template_name = 'corecode/pages/class_form.html'
    fields = ['max_students', 'is_active', 'display_name']
    permission_required = 'corecode.change_studentclass'
    success_url = reverse_lazy('corecode:class_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        SystemLogService.log_action(
            user=self.request.user,
            action=SystemLog.ActionType.UPDATE,
            app_label=SystemLog.AppLabel.CORE,
            model_name='StudentClass',
            object_id=str(self.object.id),
            object_repr=str(self.object),
            changes=form.cleaned_data,
            request=self.request
        )
        
        messages.success(self.request, f'Class {self.object.display_name} updated successfully.')
        return response


class SystemConfigView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """System configuration management"""
    template_name = 'corecode/pages/system_config.html'
    permission_required = 'corecode.change_siteconfig'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Group configs by category
        academic_configs = SiteConfig.objects.filter(key__in=[
            SiteConfigKey.TERMS_PER_SESSION,
            SiteConfigKey.CURRENT_SESSION,
            SiteConfigKey.CURRENT_TERM,
        ])
        
        admissions_configs = SiteConfig.objects.filter(key__in=[
            SiteConfigKey.ADMISSIONS_OPEN,
            SiteConfigKey.ADMISSION_DEADLINE,
            SiteConfigKey.AUTO_ENROLL_APPROVED,
        ])
        
        result_configs = SiteConfig.objects.filter(key__in=[
            SiteConfigKey.PASS_MARK,
            SiteConfigKey.DISTINCTION_MARK,
            SiteConfigKey.RESULT_TEMPLATE,
            SiteConfigKey.EXAM_CLEARANCE_REQUIRED,
        ])
        
        system_configs = SiteConfig.objects.filter(key__in=[
            SiteConfigKey.MAINTENANCE_MODE,
            SiteConfigKey.COMPANY_NAME,
            SiteConfigKey.COMPANY_EMAIL,
        ])
        
        context['academic_configs'] = academic_configs
        context['admissions_configs'] = admissions_configs
        context['result_configs'] = result_configs
        context['system_configs'] = system_configs
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle config updates"""
        for key in SiteConfigKey.ALL_KEYS:
            value = request.POST.get(key)
            if value is not None:
                SiteConfigService.set_config(
                    key=key,
                    value=value,
                    user=request.user,
                    description=f"Updated via admin interface on {timezone.now().date()}"
                )
        
        messages.success(request, 'System configuration updated successfully.')
        return redirect('corecode:system_config')


class SystemLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """View system audit logs"""
    model = SystemLog
    template_name = 'corecode/pages/log_list.html'
    context_object_name = 'logs'
    permission_required = 'corecode.view_systemlog'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = SystemLog.objects.select_related('user').order_by('-timestamp')
        
        # Filtering
        app = self.request.GET.get('app')
        if app:
            queryset = queryset.filter(app_label=app)
        
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_choices'] = SystemLog.AppLabel.choices
        context['action_choices'] = SystemLog.ActionType.choices
        context['selected_app'] = self.request.GET.get('app', '')
        context['selected_action'] = self.request.GET.get('action', '')
        return context
        
        
class SetCurrentSessionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Set a session as current"""
    permission_required = 'corecode.change_academicsession'
    
    def post(self, request, *args, **kwargs):
        session_id = kwargs.get('pk')
        try:
            from ..services import AcademicSessionService
            session = AcademicSessionService.set_current_session(session_id)
            messages.success(request, f'{session.name} is now the current session.')
        except Exception as e:
            messages.error(request, f'Error setting current session: {str(e)}')
        
        return redirect('corecode:session_list')


class PromoteTermView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Promote to next term"""
    permission_required = 'corecode.change_academicterm'
    
    def post(self, request, *args, **kwargs):
        try:
            from ..services import AcademicTermService
            new_term = AcademicTermService.promote_term()
            if new_term:
                messages.success(request, f'Promoted to {new_term.name}')
            else:
                messages.warning(request, 'No next term available')
        except Exception as e:
            messages.error(request, f'Error promoting term: {str(e)}')
        
        return redirect('corecode:term_manage')


class SetCurrentTermView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Set a specific term as current"""
    permission_required = 'corecode.change_academicterm'
    
    def post(self, request, *args, **kwargs):
        term_id = request.POST.get('term_id')
        if not term_id:
            messages.error(request, 'No term selected')
            return redirect('corecode:term_manage')
        
        try:
            from ..services import AcademicTermService
            term = AcademicTermService.set_current_term(term_id)
            messages.success(request, f'{term.name} is now the current term.')
        except Exception as e:
            messages.error(request, f'Error setting current term: {str(e)}')
        
        return redirect('corecode:term_manage')
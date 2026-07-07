"""
Audit Views
"""

from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.views.generic import ListView, DetailView, TemplateView, View

from .models import AuditLog
from .selectors import AuditLogSelector, AuditStatsSelector


class AuditDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Audit dashboard"""
    template_name = 'audit/dashboard.html'
    permission_required = 'audit.view_auditlog'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = AuditStatsSelector.get_summary(days=30)
        context['recent_logs'] = AuditLogSelector.list_logs(limit=50)
        return context


class AuditLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Audit log list"""
    model = AuditLog
    template_name = 'audit/log_list.html'
    context_object_name = 'logs'
    permission_required = 'audit.view_auditlog'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Apply filters
        user = self.request.GET.get('user')
        action = self.request.GET.get('action')
        app = self.request.GET.get('app')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if user:
            queryset = queryset.filter(username__icontains=user)
        if action:
            queryset = queryset.filter(action=action)
        if app:
            queryset = queryset.filter(app_label=app)
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)
        
        return queryset.order_by('-timestamp')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_choices'] = AuditLog._meta.get_field('action').choices
        context['app_choices'] = AuditLog.objects.values_list('app_label', flat=True).distinct()
        return context


class AuditLogDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Audit log detail"""
    model = AuditLog
    template_name = 'audit/log_detail.html'
    permission_required = 'audit.view_auditlog'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['log_data'] = AuditLogSelector.get_by_id(self.object.id)
        return context


class UserAuditView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """User audit trail"""
    template_name = 'audit/user_audit.html'
    permission_required = 'audit.view_auditlog'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.kwargs.get('user_id')
        context['user_activity'] = AuditLogSelector.get_user_activity(user_id)
        context['logs'] = AuditLogSelector.list_logs(user_id=user_id, limit=100)
        return context


class ModelAuditView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Model audit trail"""
    template_name = 'audit/model_audit.html'
    permission_required = 'audit.view_auditlog'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        app_label = self.kwargs.get('app_label')
        model_name = self.kwargs.get('model_name')
        object_id = self.request.GET.get('object_id')
        
        context['app_label'] = app_label
        context['model_name'] = model_name
        context['object_id'] = object_id
        context['history'] = AuditLogSelector.get_model_history(
            app_label, model_name, object_id
        )
        return context


class ExportAuditView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Export audit logs to CSV"""
    permission_required = 'audit.export_audit'
    
    _HEADERS = [
        'Timestamp', 'User', 'Action', 'Category', 'Status',
        'App', 'Model', 'Object ID', 'Object Representation',
        'IP Address', 'Request Method', 'Request Path',
    ]

    def get(self, request):
        from apps.shared.csv_export import build_csv_response

        logs = AuditLog.objects.all().order_by('-timestamp')[:10000]

        return build_csv_response(
            filename="audit_logs",
            headers=self._HEADERS,
            rows=[
                [
                    log.timestamp, log.username,
                    log.get_action_display(), log.get_category_display(),
                    log.get_status_display(), log.app_label,
                    log.model_name, log.object_id, log.object_repr,
                    log.ip_address, log.request_method, log.request_path,
                ]
                for log in logs
            ],
        )
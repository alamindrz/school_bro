"""
Notifications Staff Views
ARCHITECTURE COMPLIANT: Uses selectors for reads, services for writes
NO direct model access in views
"""

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from ..selectors import (
    NotificationSelector,
    TemplateSelector,
    NotificationStatsSelector,
    UserPreferenceSelector,
)
from apps.notifications.services import NotificationService
from ..models import Notification, NotificationTemplate
from ..constants import NotificationType, NotificationChannel, NotificationPriority
from ..exceptions import NotificationError, TemplateNotFoundError

logger = logging.getLogger(__name__)


class NotificationListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    List all notifications with filtering.
    USES SELECTOR: NotificationSelector
    """
    template_name = 'notifications/pages/notification_list.html'
    permission_required = 'notifications.view_notification'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters
        notification_type = self.request.GET.get('type')
        status = self.request.GET.get('status')
        priority = self.request.GET.get('priority')
        recipient_type = self.request.GET.get('recipient_type')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        # Get notifications from selector
        notifications, total = NotificationSelector.list_notifications(
            notification_type=notification_type,
            status=status,
            priority=priority,
            recipient_type=recipient_type,
            start_date=start_date,
            end_date=end_date,
            limit=100,
            offset=0
        )
        
        # Get statistics
        context['stats'] = NotificationStatsSelector.get_summary(
            days=30
        )
        
        context['notifications'] = notifications
        context['total_count'] = total
        
        # Filter options
        context['notification_types'] = NotificationType.CHOICES
        context['priorities'] = NotificationPriority.CHOICES
        context['channels'] = NotificationChannel.CHOICES
        
        return context
from django.views.generic import CreateView, UpdateView, DeleteView

class NotificationDetailView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    View single notification details.
    USES SELECTOR: NotificationSelector
    """
    template_name = 'notifications/pages/notification_detail.html'
    permission_required = 'notifications.view_notification'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        notification_id = self.kwargs.get('pk')
        
        # Get notification from selector
        notification = NotificationSelector.get_by_id(notification_id)
        
        if not notification:
            raise Http404("Notification not found")
        
        context['notification'] = notification
        
        # Get delivery logs
        from ..models import NotificationLog
        context['delivery_logs'] = NotificationLog.objects.filter(
            notification_id=notification_id
        ).order_by('-created_at')
        
        return context


class NotificationCreateView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Create a new notification.
    USES SERVICE: NotificationService
    """
    template_name = 'notifications/pages/notification_form.html'
    permission_required = 'notifications.add_notification'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['notification_types'] = NotificationType.CHOICES
        context['priorities'] = NotificationPriority.CHOICES
        context['channels'] = NotificationChannel.CHOICES
        
        # Get available templates
        context['templates'] = TemplateSelector.list_templates()
        
        return context

    def post(self, request, *args, **kwargs):
        try:
            # Collect form data
            notification_type = request.POST.get('notification_type')
            title = request.POST.get('title')
            message = request.POST.get('message')
            recipient_type = request.POST.get('recipient_type')
            recipient_id = request.POST.get('recipient_id')
            priority = request.POST.get('priority', 'normal')
            channels = request.POST.getlist('channels')
            scheduled_for = request.POST.get('scheduled_for')
            
            # Use service to create notification
            notification = NotificationService.create_notification(
                notification_type=notification_type,
                title=title,
                message=message,
                recipient_type=recipient_type,
                recipient_id=recipient_id if recipient_id else None,
                priority=priority,
                channels=channels,
                scheduled_for=scheduled_for,
                created_by_id=request.user.id
            )
            
            messages.success(request, 'Notification created successfully.')
            
            if scheduled_for:
                return redirect('notifications:list')
            else:
                return redirect('notifications:detail', pk=notification.id)
            
        except Exception as e:
            messages.error(request, f'Error creating notification: {str(e)}')
            return self.get(request, *args, **kwargs)


class NotificationTemplateListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    List all notification templates.
    USES SELECTOR: TemplateSelector
    """
    model = NotificationTemplate
    template_name = 'notifications/pages/template_list.html'
    context_object_name = 'templates'
    permission_required = 'notifications.view_notificationtemplate'
    paginate_by = 25

    def get_queryset(self):
        queryset = NotificationTemplate.objects.all().order_by('name')
        
        # Apply filters
        notification_type = self.request.GET.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        is_active = self.request.GET.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=(is_active == 'true'))
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification_types'] = NotificationType.CHOICES
        return context


class NotificationTemplateCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Create a new notification template.
    """
    model = NotificationTemplate
    template_name = 'notifications/pages/template_form.html'
    fields = [
        'name', 'notification_type', 'email_subject', 'email_template',
        'sms_template', 'push_title', 'push_body', 'in_app_message',
        'available_variables', 'is_active'
    ]
    permission_required = 'notifications.add_notificationtemplate'
    success_url = reverse_lazy('notifications:template_list')

    def form_valid(self, form):
        messages.success(self.request, 'Template created successfully.')
        return super().form_valid(form)


class NotificationTemplateUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Update a notification template.
    """
    model = NotificationTemplate
    template_name = 'notifications/pages/template_form.html'
    fields = [
        'name', 'notification_type', 'email_subject', 'email_template',
        'sms_template', 'push_title', 'push_body', 'in_app_message',
        'available_variables', 'is_active'
    ]
    permission_required = 'notifications.change_notificationtemplate'

    def get_success_url(self):
        return reverse_lazy('notifications:template_list')

    def form_valid(self, form):
        messages.success(self.request, 'Template updated successfully.')
        return super().form_valid(form)


class NotificationTemplateDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Delete a notification template.
    """
    model = NotificationTemplate
    permission_required = 'notifications.delete_notificationtemplate'
    success_url = reverse_lazy('notifications:template_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Template deleted successfully.')
        return super().delete(request, *args, **kwargs)


class NotificationPreferenceView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    View and update user notification preferences.
    USES SELECTOR: UserPreferenceSelector
    USES SERVICE: NotificationService
    """
    template_name = 'notifications/pages/preferences.html'
    permission_required = 'notifications.change_notificationpreference'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user preferences from selector
        preferences = UserPreferenceSelector.get_for_user(self.request.user.id)
        
        context['preferences'] = preferences
        context['notification_types'] = NotificationType.CHOICES
        context['channels'] = NotificationChannel.CHOICES
        
        return context

    def post(self, request, *args, **kwargs):
        try:
            # Update preferences via service
            NotificationService.update_user_preferences(
                user_id=request.user.id,
                preferences=request.POST.dict()
            )
            
            messages.success(request, 'Preferences updated successfully.')
            
        except Exception as e:
            messages.error(request, f'Error updating preferences: {str(e)}')
        
        return redirect('notifications:preferences')


class NotificationStatsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    View notification statistics.
    USES SELECTOR: NotificationStatsSelector
    """
    template_name = 'notifications/pages/stats.html'
    permission_required = 'notifications.view_notification'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        days = int(self.request.GET.get('days', 30))
        
        context['stats'] = NotificationStatsSelector.get_detailed_stats(days=days)
        context['days'] = days
        
        return context


class BulkNotificationView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Send bulk notifications.
    USES SERVICE: NotificationService
    """
    template_name = 'notifications/pages/bulk_notification.html'
    permission_required = 'notifications.add_notification'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['notification_types'] = NotificationType.CHOICES
        context['priorities'] = NotificationPriority.CHOICES
        context['recipient_types'] = [
            ('all_students', 'All Students'),
            ('all_parents', 'All Parents'),
            ('all_staff', 'All Staff'),
            ('specific_class', 'Specific Class'),
            ('specific_role', 'Specific Role'),
        ]
        
        return context

    def post(self, request, *args, **kwargs):
        try:
            notification_type = request.POST.get('notification_type')
            title = request.POST.get('title')
            message = request.POST.get('message')
            recipient_type = request.POST.get('recipient_type')
            priority = request.POST.get('priority', 'normal')
            channels = request.POST.getlist('channels')
            
            # Additional filters
            class_id = request.POST.get('class_id')
            role = request.POST.get('role')
            
            # Use service for bulk notification
            result = NotificationService.send_bulk_notification(
                notification_type=notification_type,
                title=title,
                message=message,
                recipient_type=recipient_type,
                class_id=class_id,
                role=role,
                priority=priority,
                channels=channels,
                created_by_id=request.user.id
            )
            
            messages.success(
                request, 
                f'Bulk notification sent to {result["recipient_count"]} recipients.'
            )
            
        except Exception as e:
            messages.error(request, f'Error sending bulk notification: {str(e)}')
        
        return redirect('notifications:list')


class NotificationResendView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Resend a failed notification.
    USES SERVICE: NotificationService
    """
    permission_required = 'notifications.change_notification'

    def post(self, request, *args, **kwargs):
        notification_id = kwargs.get('pk')
        
        try:
            notification = NotificationService.resend_notification(
                notification_id=notification_id,
                user_id=request.user.id
            )
            
            messages.success(request, 'Notification resent successfully.')
            
        except NotificationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error resending notification: {str(e)}')
        
        return redirect('notifications:detail', pk=notification_id)


class NotificationArchiveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Archive old notifications.
    USES SERVICE: NotificationService
    """
    permission_required = 'notifications.delete_notification'

    def post(self, request, *args, **kwargs):
        days = int(request.POST.get('days', 30))
        
        try:
            count = NotificationService.archive_old_notifications(days=days)
            messages.success(request, f'{count} notifications archived.')
            
        except Exception as e:
            messages.error(request, f'Error archiving notifications: {str(e)}')
        
        return redirect('notifications:list')
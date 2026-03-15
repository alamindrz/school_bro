from django.urls import path
from .views import staff, api

app_name = 'notifications'

urlpatterns = [
    # Staff views
    path('', staff.NotificationListView.as_view(), name='list'),
    path('create/', staff.NotificationCreateView.as_view(), name='create'),
    path('bulk/', staff.BulkNotificationView.as_view(), name='bulk'),
    path('<int:pk>/', staff.NotificationDetailView.as_view(), name='detail'),
    path('<int:pk>/resend/', staff.NotificationResendView.as_view(), name='resend'),
    
    # Templates
    path('templates/', staff.NotificationTemplateListView.as_view(), name='template_list'),
    path('templates/create/', staff.NotificationTemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/edit/', staff.NotificationTemplateUpdateView.as_view(), name='template_edit'),
    path('templates/<int:pk>/delete/', staff.NotificationTemplateDeleteView.as_view(), name='template_delete'),
    
    # Preferences
    path('preferences/', staff.NotificationPreferenceView.as_view(), name='preferences'),
    
    # Statistics
    path('stats/', staff.NotificationStatsView.as_view(), name='stats'),
    path('archive/', staff.NotificationArchiveView.as_view(), name='archive'),
    
    # API endpoints (AJAX/HTMX)
    path('api/unread/', api.get_unread_count, name='api_unread'),
    path('api/recent/', api.get_recent_notifications, name='api_recent'),
    path('api/mark-read/', api.mark_as_read, name='api_mark_read'),
    path('api/mark-all-read/', api.mark_all_as_read, name='api_mark_all_read'),
    path('api/preferences/', api.get_notification_preferences, name='api_preferences'),
    path('api/preferences/update/', api.update_notification_preferences, name='api_update_preferences'),
    path('api/test/', api.send_test_notification, name='api_test'),
    path('api/stats/', api.get_notification_stats, name='api_stats'),
    path('api/check/', api.check_notifications, name='api_check'),
]
from django.urls import path
from .views import public, staff, ajax

app_name = 'corecode'

urlpatterns = [
    # Public endpoints
    path('api/health/', public.HealthCheckView.as_view(), name='health_check'),
    path('api/academic-info/', public.CurrentAcademicInfoView.as_view(), name='academic_info'),
    
    # Staff/admin views
    path('', staff.DashboardView.as_view(), name='dashboard'),
    
    # Session URLs
    path('sessions/', staff.AcademicSessionListView.as_view(), name='session_list'),
    path('sessions/create/', staff.AcademicSessionCreateView.as_view(), name='session_create'),
    path('sessions/<int:pk>/set-current/', staff.SetCurrentSessionView.as_view(), name='session_set_current'),
    path('academicsession/', staff.AcademicSessionListView.as_view(), name='academicsession_list'),  # Alias
    
    # Term URLs
    path('terms/', staff.AcademicTermManageView.as_view(), name='term_manage'),
    path('terms/promote/', staff.PromoteTermView.as_view(), name='term_promote'),
    path('terms/set-current/', staff.SetCurrentTermView.as_view(), name='term_set_current'),
    
    # Class URLs
    path('classes/', staff.StudentClassListView.as_view(), name='class_list'),
    path('classes/<int:pk>/edit/', staff.StudentClassUpdateView.as_view(), name='class_edit'),
    path('studentclass/', staff.StudentClassListView.as_view(), name='studentclass_list'),  # Alias
    
    # Configuration
    path('config/', staff.SystemConfigView.as_view(), name='system_config'),
    path('logs/', staff.SystemLogListView.as_view(), name='log_list'),
    
    # User profile URLs (temporary)
    path('profile/', staff.DashboardView.as_view(), name='profile'),
    path('settings/', staff.DashboardView.as_view(), name='settings'),
    path('help/', staff.DashboardView.as_view(), name='help'),
    
    # AJAX/HTMX endpoints
    path('ajax/search-classes/', ajax.search_classes, name='ajax_search_classes'),
    path('ajax/term-details/', ajax.load_term_details, name='ajax_term_details'),
    path('ajax/update-config/', ajax.update_config_ajax, name='ajax_update_config'),
    path('ajax/recent-logs/', ajax.load_recent_logs, name='ajax_recent_logs'),
    path('ajax/session-status/', ajax.check_session_status, name='ajax_session_status'),
    path('ajax/class-capacity/', ajax.get_class_capacity, name='ajax_class_capacity'),
    path('ajax/quick-stats/', ajax.quick_stats, name='ajax_quick_stats'),
]
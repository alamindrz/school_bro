from django.urls import path
from .views import staff, public, ajax

app_name = 'students'

urlpatterns = [
    # Staff CRUD URLs
    path('', staff.StudentListView.as_view(), name='list'),
    path('dashboard/', staff.StudentListView.as_view(), name='dashboard'),
    path('create/', staff.StudentCreateView.as_view(), name='create'),
    path('<int:pk>/', staff.StudentDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', staff.StudentUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', staff.StudentDeleteView.as_view(), name='delete'),
    path('<int:pk>/status/', staff.StudentStatusUpdateView.as_view(), name='status_update'),
    path('<int:pk>/generate-user/', staff.StudentGenerateUserView.as_view(), name='generate_user'),
    
    # Guardian management
    path('<int:student_id>/guardians/add/', staff.GuardianCreateView.as_view(), name='guardian_create'),
    path('guardians/<int:pk>/edit/', staff.GuardianUpdateView.as_view(), name='guardian_edit'),
    path('guardians/<int:pk>/delete/', staff.GuardianDeleteView.as_view(), name='guardian_delete'),
    
    # Bulk operations
    path('promotion/', staff.StudentPromotionView.as_view(), name='promotion'),
    path('bulk-import/', staff.StudentBulkImportView.as_view(), name='bulk_import'),
    path('export/', ajax.export_students, name='export'),
    
    # ========== AJAX ENDPOINTS ==========
    
    # Search endpoints
    path('ajax/search/', ajax.search_students, name='ajax_search'),
    path('ajax/search-htmx/', ajax.search_students_htmx, name='ajax_search_htmx'),
    path('ajax/details/', ajax.get_student_details, name='ajax_details'),
    path('ajax/quick-info/', ajax.get_student_quick_info, name='ajax_quick_info'),
    
    # Filter endpoints
    path('ajax/filter/', ajax.filter_students, name='ajax_filter'),
    path('ajax/filter-options/', ajax.get_filter_options, name='ajax_filter_options'),
    
    # Class-related endpoints
    path('ajax/class-students/', ajax.get_class_students, name='ajax_class_students'),
    path('ajax/student-counts/', ajax.get_student_counts, name='ajax_student_counts'),
    
    # Student data endpoints
    path('ajax/timeline/', ajax.get_student_timeline, name='ajax_timeline'),
    path('ajax/check-admission/', ajax.check_admission_number, name='ajax_check_admission'),
    
    # Bulk actions
    path('ajax/bulk-action/', ajax.bulk_action, name='ajax_bulk_action'),
]
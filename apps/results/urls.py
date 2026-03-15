from django.urls import path
from .views import staff, api

app_name = 'results'

urlpatterns = [
    # Dashboard
    path('', staff.DashboardView.as_view(), name='dashboard'),

    # Subject management
    path('subjects/', staff.SubjectListView.as_view(), name='subject_list'),
    path('subjects/create/', staff.SubjectCreateView.as_view(), name='subject_create'),
    path('subjects/<int:pk>/edit/', staff.SubjectUpdateView.as_view(), name='subject_edit'),

    # Result sheets
    path('sheets/', staff.ResultSheetListView.as_view(), name='sheet_list'),
    path('sheets/create/', staff.ResultSheetCreateView.as_view(), name='sheet_create'),
    path('sheets/<int:pk>/', staff.ResultSheetDetailView.as_view(), name='sheet_detail'),
    path('sheets/<int:pk>/enter/', staff.ResultEntryView.as_view(), name='result_entry'),
    path('sheets/<int:pk>/bulk/', staff.BulkResultUploadView.as_view(), name='bulk_upload'),
    path('sheets/<int:pk>/submit/', staff.SubmitSheetView.as_view(), name='submit_sheet'),
    path('sheets/<int:pk>/approve/', staff.ApproveSheetView.as_view(), name='approve_sheet'),
    path('sheets/<int:pk>/publish/', staff.PublishSheetView.as_view(), name='publish_sheet'),
    path('sheets/<int:pk>/performance/', staff.ClassPerformanceView.as_view(), name='class_performance'),

    # Reports
    path('report/<int:student_id>/<int:session_id>/<int:term_id>/', staff.ReportCardView.as_view(), name='report_card'),
    path('cumulative/<int:student_id>/', staff.CumulativeRecordView.as_view(), name='cumulative_record'),

    # API endpoints
    path('api/search-subjects/', api.search_subjects, name='api_search_subjects'),
    path('api/sheet-status/<int:sheet_id>/', api.get_sheet_status, name='api_sheet_status'),
    path('api/student-results/<int:student_id>/', api.get_student_results, name='api_student_results'),
    path('api/check-clearance/<int:student_id>/', api.check_clearance, name='api_check_clearance'),
    path('api/update-result/', api.update_result_ajax, name='api_update_result'),
    path('api/cumulative-chart/<int:student_id>/', api.get_cumulative_chart, name='api_cumulative_chart'),
    path('api/grade-distribution/<int:sheet_id>/', api.get_grade_distribution, name='api_grade_distribution'),
    path('api/download-template/<int:sheet_id>/', api.download_template, name='api_download_template'),
]
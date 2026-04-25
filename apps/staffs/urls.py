from django.urls import path
from .views import staff, api, invite, auth, portal

app_name = 'staffs'

urlpatterns = [
    # Dashboard
    path('', staff.DashboardView.as_view(), name='dashboard'),
    
    # Staff management
    path('list/', staff.StaffListView.as_view(), name='list'),
    path('create/', staff.StaffCreateView.as_view(), name='create'),
    path('<int:pk>/', staff.StaffDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', staff.StaffUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', staff.StaffDeleteView.as_view(), name='delete'),
    path('<int:pk>/status/', staff.StaffStatusUpdateView.as_view(), name='status_update'),
    path('<int:pk>/send-invite/', staff.SendInviteView.as_view(), name='send_invite'),
    
    # Subject Qualifications (formerly Subject Assignments)
    path('<int:pk>/qualifications/', staff.SubjectAssignmentView.as_view(), name='subject_assignments'),
    path('qualifications/<int:pk>/delete/', staff.SubjectAssignmentDeleteView.as_view(), name='subject_assignment_delete'),
    
    # Duty Assignments
    path('<int:pk>/duties/', staff.DutyAssignmentView.as_view(), name='duty_assignments'),
    path('duty-assignments/<int:pk>/delete/', staff.DutyAssignmentDeleteView.as_view(), name='duty_assignment_delete'),
    
    # Leave Management
    path('leave-request/', staff.LeaveRequestView.as_view(), name='leave_request'),
    path('<int:pk>/leave-request/', staff.LeaveRequestView.as_view(), name='leave_request'),
    path('leave-requests/', staff.LeaveRequestListView.as_view(), name='leave_list'),
    path('leave-requests/<int:pk>/', staff.LeaveRequestDetailView.as_view(), name='leave_detail'),
    path('leave-requests/<int:pk>/approve/', staff.LeaveRequestApproveView.as_view(), name='approve_leave'),
    path('leave-requests/<int:pk>/reject/', staff.LeaveRequestRejectView.as_view(), name='reject_leave'),
    path('leave-requests/<int:pk>/cancel/', staff.LeaveRequestCancelView.as_view(), name='cancel_leave'),
    
    # Attendance
    path('attendance/', staff.StaffAttendanceView.as_view(), name='attendance'),
    path('attendance/report/', staff.StaffAttendanceReportView.as_view(), name='attendance_report'),
    
    # Performance
    path('<int:pk>/evaluate/', staff.PerformanceEvaluationView.as_view(), name='performance_evaluation'),
    path('evaluations/<int:pk>/', staff.PerformanceEvaluationDetailView.as_view(), name='performance_detail'),
    path('evaluations/<int:pk>/edit/', staff.PerformanceEvaluationEditView.as_view(), name='performance_edit'),
    path('evaluations/<int:pk>/delete/', staff.PerformanceEvaluationDeleteView.as_view(), name='performance_delete'),
    path('evaluations/<int:pk>/print/', staff.PerformanceEvaluationPrintView.as_view(), name='performance_print'),
    path('evaluations/list/', staff.PerformanceEvaluationListView.as_view(), name='performance_list'),
    
    # Qualifications (Educational)
    path('<int:staff_id>/qualifications/add/', staff.QualificationCreateView.as_view(), name='qualification_add'),
    path('qualifications/<int:pk>/delete/', staff.QualificationDeleteView.as_view(), name='qualification_delete'),
    
    # Documents
    path('<int:staff_id>/documents/upload/', staff.DocumentUploadView.as_view(), name='document_upload'),
    path('documents/<int:pk>/delete/', staff.DocumentDeleteView.as_view(), name='document_delete'),
    
    # Export
    path('export/', staff.ExportStaffView.as_view(), name='export'),
    
    # Portal URLs
    path('portal/login/', auth.StaffLoginView.as_view(), name='portal_login'),
    path('portal/logout/', auth.StaffLogoutView.as_view(), name='portal_logout'),
    path('portal/password-reset/', auth.StaffPasswordResetRequestView.as_view(), name='password_reset'),
    path('portal/password-reset/sent/', auth.PasswordResetSentView.as_view(), name='password_reset_sent'),
    path('portal/password-reset/<uuid:token>/', auth.StaffPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('portal/dashboard/', portal.StaffDashboardView.as_view(), name='portal_dashboard'),
    path('portal/my-classes/', portal.MyClassesView.as_view(), name='my_classes'),
    path('portal/my-classes/<int:class_id>/', portal.MyStudentsView.as_view(), name='my_students'),
    path('portal/my-classes/<int:class_id>/<int:subject_id>/', portal.MyStudentsView.as_view(), name='my_students_subject'),
    path('portal/profile/', portal.MyProfileView.as_view(), name='portal_profile'),
    
    # Invite URLs
    path('invite/<uuid:token>/', invite.AcceptInviteView.as_view(), name='accept_invite'),
    path('magic/<uuid:token>/', invite.MagicLinkLoginView.as_view(), name='magic_link_login'),
    
    # API endpoints
    path('api/search/', api.search_staff, name='api_search'),
    path('api/stats/', api.get_staff_stats, name='api_stats'),
    path('api/pending-leaves/', api.get_pending_leaves, name='api_pending_leaves'),
    path('api/today-attendance/', api.get_today_attendance, name='api_today_attendance'),
    path('api/attendance/<int:staff_id>/', api.get_staff_attendance, name='api_staff_attendance'),
    path('api/teaching-load/<int:staff_id>/', api.get_teaching_load, name='api_teaching_load'),
    path('api/quick-checkin/', api.quick_check_in, name='api_quick_checkin'),
    path('api/update-status/', api.update_staff_status_ajax, name='api_update_status'),
    path('api/performance/<int:staff_id>/', api.get_performance_chart, name='api_performance'),
    path('api/birthdays/', api.get_birthdays, name='api_birthdays'),
    path('ajax/class-form-master/', api.get_class_form_master, name='ajax_class_form_master'),
]
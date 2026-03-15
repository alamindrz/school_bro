from django.urls import path
from .views import staff, api

app_name = 'attendance'

urlpatterns = [
    # Dashboard
    path('', staff.DashboardView.as_view(), name='dashboard'),
    
    # Register management
    path('registers/', staff.RegisterListView.as_view(), name='register_list'),
    path('registers/create/', staff.RegisterCreateView.as_view(), name='register_create'),
    path('registers/<int:pk>/', staff.RegisterDetailView.as_view(), name='register_detail'),
    path('registers/<int:pk>/close/', staff.CloseRegisterView.as_view(), name='close_register'),
    
    # Attendance marking
    path('registers/<int:pk>/mark/', staff.MarkAttendanceView.as_view(), name='mark_attendance'),
    path('registers/<int:pk>/bulk/', staff.BulkMarkView.as_view(), name='bulk_mark'),
    path('records/<int:pk>/update/', staff.UpdateAttendanceView.as_view(), name='update_record'),
    
    # QR codes
    path('qrcodes/', staff.QRCodeView.as_view(), name='qrcodes'),
    path('qrcodes/generate/', staff.GenerateQRCodeView.as_view(), name='generate_qrcode'),
    path('qrcodes/scan/', staff.ScanQRCodeView.as_view(), name='scan_qrcode'),
    
    # Reports
    path('reports/', staff.ReportView.as_view(), name='reports'),
    path('reports/export/', staff.ExportReportView.as_view(), name='export_report'),
    
    # API endpoints
    path('api/daily-summary/', api.daily_summary, name='api_daily_summary'),
    path('api/student-summary/<int:student_id>/', api.student_summary, name='api_student_summary'),
    path('api/class-summary/<int:class_id>/', api.class_summary, name='api_class_summary'),
    path('api/process-qr/', api.process_qr_code, name='api_process_qr'),
]
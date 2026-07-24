from django.urls import path
from .views import staff, ajax, public

app_name = 'finance'

urlpatterns = [
    # Dashboard
    path('', staff.DashboardView.as_view(), name='dashboard'),
    
    # Invoice management
    path('invoices/', staff.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/create/', staff.InvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/bulk/', staff.BulkInvoiceCreateView.as_view(), name='bulk_invoice'),
    path('invoices/generate/', staff.GenerateInvoicesFromStructureView.as_view(), name='generate_invoices'),
    path('invoices/<int:pk>/', staff.InvoiceDetailView.as_view(), name='invoice_detail'),
    
    # Student financial view
    path('student/<int:student_id>/', staff.StudentFinancialView.as_view(), name='student_financial'),
    path('payments/pending/', staff.PendingPaymentsView.as_view(), name='pending_payments'),
    
    path('payments/<int:pk>/verify/', staff.VerifyPaymentView.as_view(), name='verify_payment'),
    
    # Payments
    path('payments/record/', staff.RecordPaymentView.as_view(), name='record_payment'),
    path('payments/bulk/', staff.BulkPaymentView.as_view(), name='bulk_payment'),
    path('payments/receipt/<int:pk>/', staff.ReceiptView.as_view(), name='receipt'),
    
    # Waivers
    path('waivers/<int:pk>/request/', staff.WaiverRequestView.as_view(), name='waiver_request'),
    path('waivers/<int:pk>/approve/', staff.WaiverApproveView.as_view(), name='waiver_approve'),
    path('waivers/<int:pk>/reject/', staff.WaiverRejectView.as_view(), name='waiver_reject'),
    
    # Reports
    path('export/', staff.ExportTransactionsView.as_view(), name='export_transactions'),
    
    # Public webhook (CRITICAL - must be accessible without auth)
    path('webhook/paystack/', public.PaystackWebhookView.as_view(), name='paystack_webhook'),
    
    # AJAX endpoints
    path('ajax/search/', ajax.search_invoices, name='ajax_search'),
    path('ajax/stats/', ajax.load_statistics, name='ajax_stats'),
    path('ajax/student-balance/', ajax.get_student_balance, name='ajax_student_balance'),
    path('ajax/exam-clearance/', ajax.check_exam_clearance, name='ajax_exam_clearance'),
    path('ajax/fee-structure/', ajax.get_fee_structure, name='ajax_fee_structure'),
    path('ajax/invoice-details/', ajax.get_invoice_details, name='ajax_invoice_details'),
    path('ajax/update-status/', ajax.update_invoice_status_ajax, name='ajax_update_status'),
    path('ajax/revenue-chart/', ajax.get_revenue_chart_data, name='ajax_revenue_chart'),
    path('ajax/outstanding-chart/', ajax.get_outstanding_chart_data, name='ajax_outstanding_chart'),
    path('ajax/verify-payment/', ajax.verify_payment_status, name='ajax_verify_payment'),
    path('ajax/calculate-partial/', ajax.calculate_partial_payment, name='ajax_calculate_partial'),
    path('ajax/pending-waivers/', ajax.get_pending_waivers, name='ajax_pending_waivers'),
    path('ajax/verify-payment/<int:pk>/', ajax.verify_payment_htmx, name='verify_payment_htmx'),
]
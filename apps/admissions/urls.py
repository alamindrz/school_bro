from django.urls import path
from .views import staff, public, ajax

app_name = 'admissions'

urlpatterns = [
    # Staff URLs
    path('', staff.ApplicationListView.as_view(), name='list'),
    
    
    path('create/', staff.ApplicationCreateView.as_view(), name='create'),
    path('update/<int:pk>', staff.ApplicationUpdateView.as_view(), name='edit'),
    path('<int:pk>/', staff.ApplicationDetailView.as_view(), name='detail'),
    path('<int:pk>/review/', staff.ApplicationReviewView.as_view(), name='review'),
    path('<int:pk>/enroll/', staff.ApplicationEnrollView.as_view(), name='enroll'),
    path('<int:pk>/notes/', staff.ApplicationAddNoteView.as_view(), name='add_note'),
    path('<int:pk>/pay/', staff.PaymentInitializeView.as_view(), name='initiate_payment'),
    
    # Payment callbacks and webhooks
    path('payment/callback/', staff.PaymentCallbackView.as_view(), name='payment_callback'),
    path('payment/webhook/', public.PaystackWebhookView.as_view(), name='paystack_webhook'),  # CRITICAL
    

    # Bulk operations
    path('bulk-enroll/', staff.BulkEnrollView.as_view(), name='bulk_enroll'),
    
    # Public URLs (application portal)
    path('apply/', public.PublicApplicationCreateView.as_view(), name='public_apply'),
    path('apply/<str:application_number>/', public.PublicApplicationStatusView.as_view(), name='public_status'),
    
    # AJAX endpoints
    path('ajax/search/', ajax.search_applications, name='ajax_search'),
    path('ajax/stats/', ajax.load_statistics, name='ajax_stats'),
    path('ajax/update-status/', ajax.update_status_ajax, name='ajax_update_status'),
    path('ajax/admissions-status/', ajax.check_admissions_status, name='ajax_admissions_status'),
    path('ajax/class-availability/', ajax.get_class_availability, name='ajax_class_availability'),
]
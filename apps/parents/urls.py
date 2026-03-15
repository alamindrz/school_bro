from django.urls import path
from .views import portal, api

app_name = 'parents'

urlpatterns = [
    # Public access (no login required)
    path('login/', portal.ParentLoginView.as_view(), name='login'),
    path('login/sent/', portal.LoginSentView.as_view(), name='login_sent'),
    path('access/<str:session_key>/', portal.MagicLinkView.as_view(), name='magic_link'),
    path('logout/', portal.LogoutView.as_view(), name='logout'),
    
    # Protected portal pages (require valid session)
    path('dashboard/', portal.DashboardView.as_view(), name='dashboard'),
    
    # Children management
    path('children/', portal.ChildrenView.as_view(), name='children'),
    path('children/<int:student_id>/', portal.ChildDetailView.as_view(), name='child_detail'),
    
    # Financial
    path('fees/', portal.FeesView.as_view(), name='fees'),
    path('payments/', portal.PaymentsView.as_view(), name='payments'),
    
    # Notifications
    path('notifications/', portal.NotificationsView.as_view(), name='notifications'),
    path('notifications/<int:notification_id>/read/', portal.MarkNotificationReadView.as_view(), name='mark_read'),
    path('notifications/read-all/', portal.MarkAllNotificationsReadView.as_view(), name='mark_all_read'),
    
    # Messages
    path('messages/', portal.MessagesView.as_view(), name='messages'),
    path('messages/<int:student_id>/', portal.MessageThreadView.as_view(), name='message_thread'),
    path('messages/send/', portal.SendMessageView.as_view(), name='send_message'),
    
    # Profile
    path('profile/', portal.ProfileView.as_view(), name='profile'),
    
    # API endpoints (for AJAX/HTMX)
    path('api/notifications/unread/', api.unread_count, name='api_unread_count'),
    path('api/notifications/recent/', api.recent_notifications, name='api_recent_notifications'),
    path('api/children/', api.children_list, name='api_children'),
    path('api/balance/<int:student_id>/', api.student_balance, name='api_student_balance'),
]
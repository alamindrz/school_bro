"""
Audit URLs
"""

from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('logs/', views.AuditLogListView.as_view(), name='log_list'),
    path('logs/<int:pk>/', views.AuditLogDetailView.as_view(), name='log_detail'),
    path('user/<int:user_id>/', views.UserAuditView.as_view(), name='user_audit'),
    path('model/<str:app_label>/<str:model_name>/', views.ModelAuditView.as_view(), name='model_audit'),
    path('export/', views.ExportAuditView.as_view(), name='export'),
    path('dashboard/', views.AuditDashboardView.as_view(), name='dashboard'),
]
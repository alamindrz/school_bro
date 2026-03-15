"""
Audit Admin
"""

from django.contrib import admin
from django.utils.html import format_html
import json

from .models import AuditLog, AuditArchive, AuditRetentionPolicy


class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'model_name', 'object_repr', 'ip_address']
    list_filter = ['action', 'category', 'status', 'app_label', 'model_name', 'timestamp']
    search_fields = ['username', 'user_email', 'object_repr', 'ip_address']
    readonly_fields = ['audit_id', 'timestamp', 'created_at']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Identification', {
            'fields': ('audit_id', 'timestamp')
        }),
        ('User Information', {
            'fields': ('user', 'username', 'user_email', 'user_role')
        }),
        ('Action Details', {
            'fields': ('action', 'category', 'status')
        }),
        ('Target', {
            'fields': ('app_label', 'model_name', 'object_id', 'object_repr')
        }),
        ('Changes', {
            'fields': ('old_value', 'new_value', 'changes'),
            'classes': ('collapse',)
        }),
        ('Request Context', {
            'fields': ('ip_address', 'user_agent', 'request_method', 'request_path', 'request_id'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class AuditArchiveAdmin(admin.ModelAdmin):
    list_display = ['archive_date', 'record_count', 'date_from', 'date_to']
    list_filter = ['archive_date']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        return False


class AuditRetentionPolicyAdmin(admin.ModelAdmin):
    list_display = ['app_label', 'model_name', 'retention_days', 'is_active']
    list_filter = ['is_active']
    search_fields = ['app_label', 'model_name']
    list_editable = ['retention_days', 'is_active']


admin.site.register(AuditLog, AuditLogAdmin)
admin.site.register(AuditArchive, AuditArchiveAdmin)
admin.site.register(AuditRetentionPolicy, AuditRetentionPolicyAdmin)
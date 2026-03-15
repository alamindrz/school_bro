"""
Notifications Admin
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import NotificationTemplate, Notification, NotificationPreference, NotificationLog


class NotificationLogInline(admin.TabularInline):
    model = NotificationLog
    extra = 0
    fields = ['channel', 'status', 'created_at']
    readonly_fields = ['created_at']
    can_delete = False


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'notification_type', 'is_active', 'created_at']
    list_filter = ['notification_type', 'is_active']
    search_fields = ['name']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'notification_type', 'is_active')
        }),
        ('Email Template', {
            'fields': ('email_subject', 'email_template'),
            'classes': ('wide',)
        }),
        ('SMS Template', {
            'fields': ('sms_template',),
        }),
        ('Push Notification', {
            'fields': ('push_title', 'push_body'),
            'classes': ('collapse',)
        }),
        ('In-App Message', {
            'fields': ('in_app_message',),
        }),
        ('Variables', {
            'fields': ('available_variables',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'recipient_summary', 'priority', 'status', 'created_at']
    list_filter = ['notification_type', 'priority', 'status', 'recipient_type']
    search_fields = ['title', 'message']
    readonly_fields = ['notification_id', 'created_at', 'updated_at']
    inlines = [NotificationLogInline]
    
    fieldsets = (
        ('Identification', {
            'fields': ('notification_id',)
        }),
        ('Content', {
            'fields': ('notification_type', 'title', 'message', 'priority')
        }),
        ('Action', {
            'fields': ('action_url', 'action_text'),
            'classes': ('collapse',)
        }),
        ('Recipient', {
            'fields': ('recipient_type', 'recipient_id', 'recipient_group', 'class_id', 'role')
        }),
        ('Delivery', {
            'fields': ('channels', 'status', 'sent_at', 'delivered_at', 'read_at')
        }),
        ('Error Tracking', {
            'fields': ('error_message', 'retry_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('data', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def recipient_summary(self, obj):
        if obj.recipient_type == 'student' and obj.recipient_id:
            return f"Student #{obj.recipient_id}"
        elif obj.recipient_type == 'parent' and obj.recipient_id:
            return f"Parent #{obj.recipient_id}"
        elif obj.recipient_type == 'staff' and obj.recipient_id:
            return f"Staff #{obj.recipient_id}"
        elif obj.recipient_type == 'all_students':
            return "All Students"
        elif obj.recipient_type == 'all_parents':
            return "All Parents"
        elif obj.recipient_type == 'all_staff':
            return "All Staff"
        elif obj.recipient_type == 'specific_class' and obj.class_id:
            return f"Class #{obj.class_id}"
        elif obj.recipient_type == 'specific_role' and obj.role:
            return f"Role: {obj.role}"
        return obj.recipient_type
    recipient_summary.short_description = 'Recipient'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled']
    list_filter = ['email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled']
    search_fields = ['user__email', 'user__username']
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Channel Settings', {
            'fields': ('email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled')
        }),
        ('Quiet Hours', {
            'fields': ('quiet_hours_start', 'quiet_hours_end'),
            'classes': ('collapse',)
        }),
        ('Per-Type Preferences', {
            'fields': ('preferences',),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['notification', 'channel', 'status', 'created_at']
    list_filter = ['channel', 'status']
    search_fields = ['notification__title']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
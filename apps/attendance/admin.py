"""
Attendance App Admin Configuration
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import AttendanceRegister, AttendanceRecord, AttendanceSummary, QRCode


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    fields = ['student_id', 'student_name', 'status', 'check_in_time', 'remarks']
    readonly_fields = ['student_name']
    can_delete = False


@admin.register(AttendanceRegister)
class AttendanceRegisterAdmin(admin.ModelAdmin):
    list_display = ['register_number', 'student_class', 'date', 'session_type', 'total_students', 'present_count', 'is_closed']
    list_filter = ['session_type', 'is_closed', 'date', 'academic_session']
    search_fields = ['register_number', 'student_class__name']
    readonly_fields = ['register_number', 'total_students', 'present_count', 'absent_count', 'late_count', 'excused_count']
    inlines = [AttendanceRecordInline]
    raw_id_fields = ['student_class', 'academic_session', 'academic_term', 'marked_by', 'closed_by']
    
    fieldsets = (
        ('Register Information', {
            'fields': ('register_number', 'student_class', 'date', 'session_type')
        }),
        ('Academic Context', {
            'fields': ('academic_session', 'academic_term')
        }),
        ('Statistics', {
            'fields': ('total_students', 'present_count', 'absent_count', 'late_count', 'excused_count')
        }),
        ('Status', {
            'fields': ('is_closed', 'closed_at', 'closed_by', 'marked_by', 'marking_method')
        }),
    )


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'register', 'status', 'check_in_time', 'marked_at']
    list_filter = ['status', 'register__date', 'register__session_type']
    search_fields = ['student_name', 'student_id']
    raw_id_fields = ['register', 'marked_by']
    readonly_fields = ['marked_at', 'updated_at']


@admin.register(AttendanceSummary)
class AttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'academic_session', 'academic_term', 'total_days', 'present_percentage', 'attendance_alert']
    list_filter = ['attendance_alert', 'academic_session', 'academic_term']
    search_fields = ['student_name']
    raw_id_fields = ['academic_session', 'academic_term']
    readonly_fields = ['last_calculated']
    
    def alert_colored(self, obj):
        if obj.attendance_alert:
            return format_html('<span style="color: red;">⚠️ Alert</span>')
        return format_html('<span style="color: green;">✓ OK</span>')
    alert_colored.short_description = 'Alert Status'


@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'code_short', 'is_active', 'use_count', 'last_used', 'created_at']
    list_filter = ['is_active']
    search_fields = ['student_name', 'code']
    readonly_fields = ['code', 'use_count', 'last_used', 'created_at', 'updated_at']
    
    def code_short(self, obj):
        return obj.code[:20] + '...' if len(obj.code) > 20 else obj.code
    code_short.short_description = 'Code'
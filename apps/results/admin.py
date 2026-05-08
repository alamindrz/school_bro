"""
Results App Admin Configuration
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import ScoreSheet, ScoreEntry, CumulativeRecord


class ScoreEntryInline(admin.TabularInline):
    model = ScoreEntry
    extra = 0
    fields = ['student_name', 'ca1', 'ca2', 'ca3', 'exam', 'total_score', 'grade', 'position']
    readonly_fields = ['student_name', 'total_score', 'grade', 'position']
    can_delete = False


@admin.register(ScoreSheet)
class ScoreSheetAdmin(admin.ModelAdmin):
    list_display = ['subject', 'student_class', 'academic_session', 'academic_term', 'status', 'completion_display']
    list_filter = ['status', 'academic_session', 'academic_term', 'student_class']
    search_fields = ['subject__name', 'student_class__display_name']
    readonly_fields = ['created_at', 'updated_at', 'submitted_at']
    inlines = [ScoreEntryInline]
    raw_id_fields = ['subject', 'student_class', 'academic_session', 'academic_term', 'created_by', 'submitted_by']

    fieldsets = (
        ('Context', {
            'fields': ('subject', 'student_class', 'academic_session', 'academic_term')
        }),
        ('Status', {
            'fields': ('status', 'created_by', 'submitted_by', 'submitted_at', 'created_at', 'updated_at')
        }),
    )

    def completion_display(self, obj):
        filled = obj.entries.filter(total_score__isnull=False).count()
        total = obj.entries.count()
        pct = round(filled / total * 100, 1) if total > 0 else 0
        color = 'green' if pct == 100 else 'yellow' if pct >= 50 else 'red'
        return format_html(
            '<span style="color: {};">{}/{} ({}%)</span>',
            color, filled, total, pct
        )
    completion_display.short_description = 'Completion'


@admin.register(ScoreEntry)
class ScoreEntryAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'score_sheet', 'ca1', 'ca2', 'ca3', 'exam', 'total_score', 'grade', 'position']
    list_filter = ['score_sheet__academic_session', 'score_sheet__academic_term', 'grade']
    search_fields = ['student_name', 'score_sheet__subject__name']
    readonly_fields = ['total_score', 'grade', 'position']
    raw_id_fields = ['score_sheet', 'entered_by']

    fieldsets = (
        ('Student', {
            'fields': ('student_name', 'student_id')
        }),
        ('Scores', {
            'fields': ('ca1', 'ca2', 'ca3', 'exam')
        }),
        ('Calculated', {
            'fields': ('total_score', 'grade', 'position')
        }),
        ('Meta', {
            'fields': ('score_sheet', 'entered_by', 'updated_at')
        }),
    )


@admin.register(CumulativeRecord)
class CumulativeRecordAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'academic_session', 'term1_average', 'term2_average', 'term3_average', 'session_average', 'promoted_to_next_class']
    list_filter = ['academic_session', 'promoted_to_next_class']
    search_fields = ['student_name']
    readonly_fields = ['session_average', 'last_updated']
    raw_id_fields = ['academic_session']
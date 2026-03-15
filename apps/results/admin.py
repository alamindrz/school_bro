"""
Results App Admin Configuration
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.corecode.models import Subject

from .models import ResultSheet, ResultSheetSubject, Result, ResultComment, CumulativeRecord


class ResultSheetSubjectInline(admin.TabularInline):
    model = ResultSheetSubject
    extra = 0
    fields = ['subject', 'teacher_name', 'pass_mark']
    raw_id_fields = ['subject']


class ResultInline(admin.TabularInline):
    model = Result
    extra = 0
    fields = ['student_id', 'student_name', 'subject', 'total_score', 'grade', 'position']
    readonly_fields = ['student_name', 'total_score', 'grade', 'position']
    raw_id_fields = ['subject']
    can_delete = False
    ordering = ['student_name']


class ResultCommentInline(admin.TabularInline):
    model = ResultComment
    extra = 0
    fields = ['student_name', 'teacher_comment', 'class_teacher_comment']
    readonly_fields = ['student_name']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'subject_type', 'is_nigerian_core', 'is_active']
    list_filter = ['subject_type', 'is_nigerian_core', 'is_active']
    search_fields = ['name', 'code']
    filter_horizontal = ['offered_in_classes']
    
    fieldsets = (
        ('Subject Information', {
            'fields': ('name', 'code', 'subject_type', 'description')
        }),
        ('Availability', {
            'fields': ('offered_in_classes', 'is_active', 'is_nigerian_core')
        }),
    )


@admin.register(ResultSheet)
class ResultSheetAdmin(admin.ModelAdmin):
    list_display = ['sheet_number', 'student_class', 'academic_session', 'academic_term', 'status', 'created_at']
    list_filter = ['status', 'academic_session', 'academic_term']
    search_fields = ['sheet_number', 'student_class__name']
    raw_id_fields = ['student_class', 'academic_session', 'academic_term', 'created_by', 'submitted_by', 'approved_by', 'published_by']
    readonly_fields = ['sheet_number', 'created_at', 'updated_at']
    inlines = [ResultSheetSubjectInline, ResultInline, ResultCommentInline]
    
    fieldsets = (
        ('Sheet Information', {
            'fields': ('sheet_number', 'student_class', 'academic_session', 'academic_term')
        }),
        ('Status', {
            'fields': ('status', 'submitted_by', 'submitted_at', 'approved_by', 'approved_at', 'published_by', 'published_at')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student_class', 'academic_session', 'academic_term'
        )


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'subject', 'result_sheet', 'total_score', 'grade', 'position']
    list_filter = ['grade', 'result_sheet__academic_session', 'result_sheet__academic_term']
    search_fields = ['student_name', 'student_id']
    raw_id_fields = ['result_sheet', 'subject', 'entered_by']
    readonly_fields = ['total_score', 'grade', 'grade_point', 'position', 'entered_at', 'updated_at']
    
    fieldsets = (
        ('Student', {
            'fields': ('student_id', 'student_name')
        }),
        ('Subject', {
            'fields': ('result_sheet', 'subject')
        }),
        ('Scores', {
            'fields': ('ca1_score', 'ca2_score', 'ca3_score', 'exam_score', 'practical_score', 'project_score')
        }),
        ('Calculated Fields', {
            'fields': ('total_score', 'grade', 'grade_point', 'position'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('entered_by', 'entered_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ResultComment)
class ResultCommentAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'result_sheet', 'created_at']
    list_filter = ['result_sheet__academic_session', 'result_sheet__academic_term']
    search_fields = ['student_name']
    raw_id_fields = ['result_sheet', 'created_by']
    
    fieldsets = (
        ('Student', {
            'fields': ('student_id', 'student_name', 'result_sheet')
        }),
        ('Comments', {
            'fields': ('teacher_comment', 'class_teacher_comment', 'principal_comment', 'next_term_recommendation')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CumulativeRecord)
class CumulativeRecordAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'academic_session', 'session_average', 'promoted_to_next_class']
    list_filter = ['academic_session', 'promoted_to_next_class']
    search_fields = ['student_name']
    raw_id_fields = ['academic_session']
    readonly_fields = ['last_updated']
    
    fieldsets = (
        ('Student', {
            'fields': ('student_id', 'student_name', 'academic_session')
        }),
        ('Term 1', {
            'fields': ('term1_total', 'term1_average', 'term1_position'),
            'classes': ('collapse',)
        }),
        ('Term 2', {
            'fields': ('term2_total', 'term2_average', 'term2_position'),
            'classes': ('collapse',)
        }),
        ('Term 3', {
            'fields': ('term3_total', 'term3_average', 'term3_position'),
            'classes': ('collapse',)
        }),
        ('Session Totals', {
            'fields': ('session_total', 'session_average', 'session_position', 'promoted_to_next_class')
        }),
    )
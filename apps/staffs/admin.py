"""
Staffs App Admin Configuration
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Staff, SubjectAssignment, DutyAssignment, LeaveRequest,
    StaffAttendance, Qualification, WorkExperience,
    PerformanceEvaluation, StaffDocument
)


class SubjectAssignmentInline(admin.TabularInline):
    model = SubjectAssignment
    extra = 0
    fields = ['subject', 'student_class', 'academic_session', 'periods_per_week', 'is_form_master']
    raw_id_fields = ['subject', 'student_class', 'academic_session', 'academic_term']


class DutyAssignmentInline(admin.TabularInline):
    model = DutyAssignment
    extra = 0
    fields = ['duty_post', 'academic_session', 'is_active', 'day_of_week', 'start_time', 'end_time']
    raw_id_fields = ['academic_session', 'student_class']


class QualificationInline(admin.TabularInline):
    model = Qualification
    extra = 0
    fields = ['qualification_type', 'title', 'institution', 'year_obtained', 'verified']


class WorkExperienceInline(admin.TabularInline):
    model = WorkExperience
    extra = 0
    fields = ['employer', 'position', 'start_date', 'end_date', 'is_current']


# In apps/staffs/admin.py, update the PerformanceEvaluationInline class:

class PerformanceEvaluationInline(admin.TabularInline):
    model = PerformanceEvaluation
    extra = 0
    fk_name = 'staff'  # Specify which ForeignKey to use
    fields = ['evaluation_period', 'evaluation_date', 'overall_rating']
    readonly_fields = ['overall_rating']

class StaffDocumentInline(admin.TabularInline):
    model = StaffDocument
    extra = 0
    fields = ['document_type', 'title', 'uploaded_at']


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'get_full_name', 'staff_type', 'department', 'employment_status', 'email', 'phone']
    list_filter = ['staff_type', 'staff_category', 'employment_status', 'employment_type', 'department', 'gender']
    search_fields = ['staff_id', 'first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['staff_id', 'staff_category', 'created_at', 'updated_at']
    raw_id_fields = ['user', 'supervisor', 'created_by']
    inlines = [
        SubjectAssignmentInline, DutyAssignmentInline, QualificationInline,
        WorkExperienceInline, PerformanceEvaluationInline, StaffDocumentInline
    ]

    fieldsets = (
        ('Identification', {
            'fields': ('staff_id', 'user', 'first_name', 'last_name', 'middle_name', 'passport_photograph')
        }),
        ('Personal Information', {
            'fields': ('gender', 'date_of_birth', 'marital_status', 'blood_group')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'alternate_phone', 'address', 'city', 'state_of_origin', 'lga', 'nationality')
        }),
        ('Employment Details', {
            'fields': ('staff_type', 'staff_category', 'employment_status', 'employment_type',
                      'shift', 'date_employed', 'date_confirmed', 'retirement_date',
                      'department', 'unit', 'supervisor')
        }),
        ('Qualifications', {
            'fields': ('highest_qualification', 'qualification_details'),
            'classes': ('collapse',)
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_number', 'account_name', 'pension_number', 'tax_id'),
            'classes': ('collapse',)
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship')
        }),
        ('Medical Information', {
            'fields': ('medical_conditions', 'allergies', 'doctor_name', 'doctor_phone'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_full_name(self, obj):
        return obj.get_full_name
    get_full_name.short_description = 'Full Name'
    get_full_name.admin_order_field = 'last_name'


@admin.register(SubjectAssignment)
class SubjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ['staff', 'subject', 'student_class', 'academic_session', 'periods_per_week', 'is_form_master']
    list_filter = ['academic_session', 'student_class', 'is_form_master']
    search_fields = ['staff__first_name', 'staff__last_name', 'subject__name']
    raw_id_fields = ['staff', 'subject', 'student_class', 'academic_session', 'academic_term', 'assigned_by']


@admin.register(DutyAssignment)
class DutyAssignmentAdmin(admin.ModelAdmin):
    list_display = ['staff', 'duty_post', 'academic_session', 'is_active', 'day_of_week']
    list_filter = ['duty_post', 'is_active', 'academic_session']
    search_fields = ['staff__first_name', 'staff__last_name', 'club_name', 'house_name']
    raw_id_fields = ['staff', 'academic_session', 'student_class', 'assigned_by']


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['staff', 'leave_type', 'start_date', 'end_date', 'days', 'status']
    list_filter = ['leave_type', 'status', 'start_date']
    search_fields = ['staff__first_name', 'staff__last_name', 'reason']
    raw_id_fields = ['staff', 'approved_by']

    def days(self, obj):
        return obj.days_requested
    days.short_description = 'Days'


@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'date', 'status', 'check_in_time', 'check_out_time']
    list_filter = ['status', 'date']
    search_fields = ['staff__first_name', 'staff__last_name']
    raw_id_fields = ['staff', 'marked_by']


@admin.register(PerformanceEvaluation)
class PerformanceEvaluationAdmin(admin.ModelAdmin):
    list_display = ['staff', 'evaluation_period', 'evaluation_date', 'overall_rating']
    list_filter = ['evaluation_date']
    search_fields = ['staff__first_name', 'staff__last_name']
    raw_id_fields = ['staff', 'evaluator']


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ['staff', 'qualification_type', 'title', 'year_obtained', 'verified']
    list_filter = ['qualification_type', 'verified', 'year_obtained']
    search_fields = ['staff__first_name', 'staff__last_name', 'title']
    raw_id_fields = ['staff', 'verified_by']


@admin.register(WorkExperience)
class WorkExperienceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'employer', 'position', 'start_date', 'end_date', 'is_current']
    list_filter = ['is_current']
    search_fields = ['staff__first_name', 'staff__last_name', 'employer']
    raw_id_fields = ['staff']


@admin.register(StaffDocument)
class StaffDocumentAdmin(admin.ModelAdmin):
    list_display = ['staff', 'document_type', 'title', 'uploaded_at']
    list_filter = ['document_type']
    search_fields = ['staff__first_name', 'staff__last_name', 'title']
    raw_id_fields = ['staff', 'uploaded_by']
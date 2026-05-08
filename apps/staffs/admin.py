"""
Staffs Admin Configuration
Registers models with Django admin interface.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .models import (
    Staff,
    TeacherSubjectQualification,  # NEW: Replaces SubjectAssignment
    DutyAssignment,
    LeaveRequest,
    StaffAttendance,
    Qualification,
    WorkExperience,
    PerformanceEvaluation,
    StaffDocument,
    PortalSession,
)
from .constants import EmploymentStatus, StaffCategory

from apps.corecode.models import Subject

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    search_fields = ['name', 'code']
    list_display = ['name', 'code', 'subject_type', 'is_active']
# ============================================================================
# INLINE MODELS
# ============================================================================

class TeacherSubjectQualificationInline(admin.TabularInline):
    """Inline for managing teacher subject qualifications"""
    model = TeacherSubjectQualification
    extra = 1
    fields = ('subject', 'is_primary', 'created_at')
    readonly_fields = ('created_at',)
    raw_id_fields = ('subject',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('subject')


class DutyAssignmentInline(admin.TabularInline):
    """Inline for managing duty assignments"""
    model = DutyAssignment
    extra = 0
    fields = ('duty_post', 'academic_session', 'is_active')
    readonly_fields = ()


class QualificationInline(admin.TabularInline):
    """Inline for educational qualifications"""
    model = Qualification
    extra = 0
    fields = ('qualification_type', 'title', 'institution', 'year_obtained', 'verified')
    readonly_fields = ()


class WorkExperienceInline(admin.TabularInline):
    """Inline for work experience"""
    model = WorkExperience
    extra = 0
    fields = ('employer', 'position', 'start_date', 'end_date', 'is_current')


class PerformanceEvaluationInline(admin.TabularInline):
    """Inline for performance evaluations"""
    model = PerformanceEvaluation
    extra = 0
    fk_name = 'staff'
    fields = ('evaluation_date', 'evaluation_period', 'overall_rating')
    readonly_fields = ('overall_rating',)
    can_delete = False


class StaffDocumentInline(admin.TabularInline):
    """Inline for staff documents"""
    model = StaffDocument
    extra = 0
    fields = ('document_type', 'title', 'file', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class LeaveRequestInline(admin.TabularInline):
    """Inline for leave requests"""
    model = LeaveRequest
    extra = 0
    fk_name = 'staff'
    fields = ('leave_type', 'start_date', 'end_date', 'days_requested', 'status')
    readonly_fields = ('days_requested',)
    can_delete = False
    show_change_link = True


class StaffAttendanceInline(admin.TabularInline):
    """Inline for attendance records"""
    model = StaffAttendance
    extra = 0
    fields = ('date', 'status', 'check_in_time', 'check_out_time')
    readonly_fields = ()
    can_delete = False


# ============================================================================
# MODEL ADMIN CLASSES
# ============================================================================

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    """Admin configuration for Staff model"""
    
    list_display = (
        'staff_id', 'get_full_name', 'email', 'phone',
        'staff_type', 'staff_category', 'employment_status',
        'department', 'date_employed', 'passport_preview'
    )
    list_filter = (
        'staff_type', 'staff_category', 'employment_status',
        'gender', 'department', 'date_employed'
    )
    search_fields = (
        'staff_id', 'first_name', 'last_name', 'middle_name',
        'email', 'phone', 'department'
    )
    readonly_fields = (
        'staff_id', 'staff_category', 'years_of_service',
        'age', 'created_at', 'updated_at', 'created_by'
    )
    fieldsets = (
        (_('Personal Information'), {
            'fields': (
                ('staff_id', 'passport_photograph'),
                ('first_name', 'last_name', 'middle_name'),
                ('gender', 'date_of_birth', 'marital_status'),
                ('blood_group', 'nationality', 'state_of_origin'),
                'lga',
            )
        }),
        (_('Contact Information'), {
            'fields': (
                'email', 'phone', 'alternate_phone',
                'address', 'city',
            )
        }),
        (_('Employment Information'), {
            'fields': (
                ('staff_type', 'staff_category'),
                ('employment_status', 'employment_type', 'shift'),
                ('date_employed', 'date_confirmed', 'retirement_date'),
                ('department', 'unit'),
                'supervisor',
            )
        }),
        (_('Emergency Contact'), {
            'fields': (
                'emergency_contact_name',
                'emergency_contact_phone',
                'emergency_contact_relationship',
            )
        }),
        (_('Bank & Tax Information'), {
            'fields': (
                ('bank_name', 'account_number', 'account_name'),
                ('pension_number', 'tax_id'),
            ),
            'classes': ('collapse',)
        }),
        (_('Medical Information'), {
            'fields': (
                'medical_conditions',
                'allergies',
                ('doctor_name', 'doctor_phone'),
            ),
            'classes': ('collapse',)
        }),
        (_('Qualifications'), {
            'fields': (
                ('highest_qualification', 'qualification_details'),
            ),
        }),
        (_('Metadata'), {
            'fields': (
                ('created_by', 'created_at', 'updated_at'),
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [
        TeacherSubjectQualificationInline,
        DutyAssignmentInline,
        QualificationInline,
        WorkExperienceInline,
        StaffDocumentInline,
        LeaveRequestInline,
        StaffAttendanceInline,
        PerformanceEvaluationInline,
    ]
    
    actions = ['mark_as_active', 'mark_as_on_leave', 'mark_as_terminated', 'export_as_csv']
    
    def get_full_name(self, obj):
        return obj.get_full_name
    get_full_name.short_description = _('Full Name')
    get_full_name.admin_order_field = 'last_name'
    
    def passport_preview(self, obj):
        if obj.passport_photograph:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius: 50%; object-fit: cover;" />',
                obj.passport_photograph.url
            )
        return format_html(
            '<div style="width:40px;height:40px;border-radius:50%;background:#e5e7eb;display:flex;align-items:center;justify-content:center;color:#9ca3af;">'
            '<i class="fas fa-user"></i></div>'
        )
    passport_preview.short_description = _('Photo')
    
    # ========================================================================
    # CUSTOM ACTIONS
    # ========================================================================
    
    @admin.action(description=_("Mark selected staff as Active"))
    def mark_as_active(self, request, queryset):
        updated = queryset.update(employment_status=EmploymentStatus.ACTIVE)
        self.message_user(request, _(f"{updated} staff marked as Active."))
    
    @admin.action(description=_("Mark selected staff as On Leave"))
    def mark_as_on_leave(self, request, queryset):
        updated = queryset.update(employment_status=EmploymentStatus.ON_LEAVE)
        self.message_user(request, _(f"{updated} staff marked as On Leave."))
    
    @admin.action(description=_("Mark selected staff as Terminated"))
    def mark_as_terminated(self, request, queryset):
        updated = queryset.update(employment_status=EmploymentStatus.TERMINATED)
        self.message_user(request, _(f"{updated} staff marked as Terminated."))
    
    @admin.action(description=_("Export selected staff to CSV"))
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        from datetime import date
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="staff_export_{date.today()}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Staff ID', 'First Name', 'Last Name', 'Email', 'Phone',
            'Staff Type', 'Category', 'Status', 'Department', 'Date Employed'
        ])
        
        for staff in queryset:
            writer.writerow([
                staff.staff_id, staff.first_name, staff.last_name,
                staff.email, staff.phone, staff.get_staff_type_display(),
                staff.get_staff_category_display(), staff.get_employment_status_display(),
                staff.department, staff.date_employed
            ])
        
        return response


@admin.register(TeacherSubjectQualification)
class TeacherSubjectQualificationAdmin(admin.ModelAdmin):
    """Admin configuration for Teacher Subject Qualifications"""
    
    list_display = ('teacher', 'subject', 'is_primary', 'created_at')
    list_filter = ('is_primary', 'created_at', 'subject')
    search_fields = ('teacher__first_name', 'teacher__last_name', 'teacher__staff_id', 'subject__name')
    raw_id_fields = ('teacher', 'subject')
    autocomplete_fields = ('teacher', 'subject')
    
    fieldsets = (
        (_('Qualification Details'), {
            'fields': (
                ('teacher', 'subject'),
                'is_primary',
            )
        }),
        (_('Metadata'), {
            'fields': (
                ('created_by', 'created_at', 'updated_at'),
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher', 'subject')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DutyAssignment)
class DutyAssignmentAdmin(admin.ModelAdmin):
    """Admin configuration for Duty Assignments"""
    
    list_display = ('staff', 'duty_post', 'academic_session', 'is_active', 'assigned_at')
    list_filter = ('duty_post', 'is_active', 'academic_session')
    search_fields = ('staff__first_name', 'staff__last_name', 'staff__staff_id', 'club_name', 'sport_name')
    raw_id_fields = ('staff', 'student_class')
    
    fieldsets = (
        (_('Duty Details'), {
            'fields': (
                'staff', 'duty_post', 'academic_session',
                ('student_class', 'is_active'),
            )
        }),
        (_('Specific Details'), {
            'fields': (
                ('club_name', 'sport_name', 'house_name'),
                ('day_of_week', 'start_time', 'end_time'),
            ),
        }),
        (_('Metadata'), {
            'fields': ('assigned_by', 'assigned_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('assigned_at',)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    """Admin configuration for Leave Requests"""
    
    list_display = ('staff', 'leave_type', 'start_date', 'end_date', 'days_requested', 'status', 'created_at')
    list_filter = ('status', 'leave_type', 'created_at')
    search_fields = ('staff__first_name', 'staff__last_name', 'staff__staff_id', 'reason')
    raw_id_fields = ('staff', 'approved_by')
    
    fieldsets = (
        (_('Request Details'), {
            'fields': (
                'staff', 'leave_type',
                ('start_date', 'end_date', 'return_date'),
                'reason', 'handover_notes',
            )
        }),
        (_('Contact During Leave'), {
            'fields': (
                ('alternative_phone', 'alternative_email'),
            ),
            'classes': ('collapse',)
        }),
        (_('Approval'), {
            'fields': (
                'status',
                ('approved_by', 'approved_at'),
                'approval_notes',
            )
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('days_requested', 'created_at', 'updated_at', 'approved_at')
    
    actions = ['approve_requests', 'reject_requests']
    
    @admin.action(description=_("Approve selected leave requests"))
    def approve_requests(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='approved',
            approved_by=request.user.staff_profile if hasattr(request.user, 'staff_profile') else None,
            approved_at=timezone.now()
        )
        self.message_user(request, _(f"{updated} leave requests approved."))
    
    @admin.action(description=_("Reject selected leave requests"))
    def reject_requests(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, _(f"{updated} leave requests rejected."))


@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    """Admin configuration for Staff Attendance"""
    
    list_display = ('staff', 'date', 'status', 'check_in_time', 'check_out_time')
    list_filter = ('status', 'date')
    search_fields = ('staff__first_name', 'staff__last_name', 'staff__staff_id')
    raw_id_fields = ('staff', 'marked_by')
    date_hierarchy = 'date'
    
    fieldsets = (
        (_('Attendance Record'), {
            'fields': (
                ('staff', 'date'),
                'status',
                ('check_in_time', 'check_out_time'),
                ('check_in_location', 'check_out_location'),
                'notes',
            )
        }),
        (_('Metadata'), {
            'fields': (
                'marked_by',
                ('created_at', 'updated_at'),
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    """Admin configuration for Educational Qualifications"""
    
    list_display = ('staff', 'qualification_type', 'title', 'institution', 'year_obtained', 'verified')
    list_filter = ('qualification_type', 'verified', 'year_obtained')
    search_fields = ('staff__first_name', 'staff__last_name', 'title', 'institution')
    raw_id_fields = ('staff', 'verified_by')
    
    fieldsets = (
        (_('Qualification Details'), {
            'fields': (
                'staff', 'qualification_type',
                'title', 'institution', 'year_obtained',
                ('certificate_number', 'expiry_date'),
                'document',
            )
        }),
        (_('Verification'), {
            'fields': (
                'verified',
                ('verified_by', 'verified_at'),
            )
        }),
    )
    
    readonly_fields = ('verified_at',)


@admin.register(WorkExperience)
class WorkExperienceAdmin(admin.ModelAdmin):
    """Admin configuration for Work Experience"""
    
    list_display = ('staff', 'employer', 'position', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current',)
    search_fields = ('staff__first_name', 'staff__last_name', 'employer', 'position')
    raw_id_fields = ('staff',)
    
    fieldsets = (
        (_('Experience Details'), {
            'fields': (
                'staff',
                ('employer', 'position'),
                ('start_date', 'end_date', 'is_current'),
                'responsibilities',
            )
        }),
        (_('Reference'), {
            'fields': (
                ('referee_name', 'referee_phone', 'referee_email'),
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(PerformanceEvaluation)
class PerformanceEvaluationAdmin(admin.ModelAdmin):
    """Admin configuration for Performance Evaluations"""
    
    list_display = ('staff', 'evaluation_period', 'evaluation_date', 'overall_rating', 'evaluator')
    list_filter = ('evaluation_period', 'evaluation_date')
    search_fields = ('staff__first_name', 'staff__last_name', 'evaluator__first_name')
    raw_id_fields = ('staff', 'evaluator')
    
    fieldsets = (
        (_('Evaluation Information'), {
            'fields': (
                ('staff', 'evaluator'),
                ('evaluation_period', 'evaluation_date'),
            )
        }),
        (_('Ratings (1-5)'), {
            'fields': (
                ('punctuality', 'job_knowledge', 'quality_of_work'),
                ('communication', 'teamwork', 'initiative'),
                'overall_rating',
            )
        }),
        (_('Comments'), {
            'fields': (
                'strengths',
                'areas_for_improvement',
                'overall_comments',
                'recommendation',
            )
        }),
        (_('Metadata'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('overall_rating', 'created_at')


@admin.register(StaffDocument)
class StaffDocumentAdmin(admin.ModelAdmin):
    """Admin configuration for Staff Documents"""
    
    list_display = ('staff', 'document_type', 'title', 'uploaded_at', 'uploaded_by')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('staff__first_name', 'staff__last_name', 'title')
    raw_id_fields = ('staff', 'uploaded_by')
    
    fieldsets = (
        (_('Document Information'), {
            'fields': (
                'staff', 'document_type', 'title', 'file',
            )
        }),
        (_('Metadata'), {
            'fields': (
                ('uploaded_by', 'uploaded_at'),
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('uploaded_at',)


@admin.register(PortalSession)
class PortalSessionAdmin(admin.ModelAdmin):
    """Admin configuration for Portal Sessions"""
    
    list_display = ('staff', 'token', 'created_at', 'expires_at', 'is_used', 'is_valid')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('staff__first_name', 'staff__last_name', 'token')
    raw_id_fields = ('staff',)
    readonly_fields = ('token', 'created_at', 'is_valid')
    
    fieldsets = (
        (_('Session Details'), {
            'fields': (
                'staff', 'token',
                ('created_at', 'expires_at'),
                'is_used',
            )
        }),
    )
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = _('Is Valid')



"""
Admissions App Admin Configuration
"""

from django.contrib import admin
from .models import Application, ApplicationPayment, ApplicationDocument, ApplicationNote, ApplicationReview


class ApplicationPaymentInline(admin.StackedInline):
    model = ApplicationPayment
    extra = 0
    readonly_fields = ['paystack_reference', 'paystack_response', 'verified_at']


class ApplicationDocumentInline(admin.TabularInline):
    model = ApplicationDocument
    extra = 0
    readonly_fields = ['uploaded_at']


class ApplicationNoteInline(admin.TabularInline):
    model = ApplicationNote
    extra = 0
    readonly_fields = ['created_at']


class ApplicationReviewInline(admin.TabularInline):
    model = ApplicationReview
    extra = 0
    readonly_fields = ['reviewed_at']
    raw_id_fields = ['reviewed_by']


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['application_number', 'full_name', 'email', 'applying_for_class', 'status', 'submitted_at']
    list_filter = ['status', 'application_type', 'applying_for_session', 'applying_for_class']
    search_fields = ['application_number', 'first_name', 'last_name', 'email']
    readonly_fields = ['application_number', 'created_at', 'updated_at']
    raw_id_fields = ['applying_for_class', 'applying_for_session', 'reviewed_by', 'created_by']
    inlines = [ApplicationPaymentInline, ApplicationDocumentInline, ApplicationNoteInline, ApplicationReviewInline]

    fieldsets = (
        ('Application Information', {
            'fields': ('application_number', 'status', 'application_type')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'middle_name', 'gender', 'date_of_birth')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'alternate_phone', 'address', 'city', 'state_of_origin', 'nationality')
        }),
        ('Academic Information', {
            'fields': ('applying_for_class', 'applying_for_session', 'previous_school', 'previous_class')
        }),
        ('Guardian Information', {
            'fields': ('guardian_first_name', 'guardian_last_name', 'guardian_relationship',
                      'guardian_phone', 'guardian_email', 'guardian_address', 'guardian_occupation')
        }),
        ('Review Information', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes'),
            'classes': ('collapse',)
        }),
        ('Enrollment Information', {
            'fields': ('enrolled_student_id', 'enrolled_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ApplicationPayment)
class ApplicationPaymentAdmin(admin.ModelAdmin):
    list_display = ['application', 'amount', 'status', 'payment_method', 'transaction_date']
    list_filter = ['status', 'payment_method']
    search_fields = ['application__application_number', 'paystack_reference']
    readonly_fields = ['paystack_response', 'created_at', 'updated_at']


@admin.register(ApplicationDocument)
class ApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = ['application', 'document_type', 'filename', 'file_size', 'uploaded_at']
    list_filter = ['document_type']
    search_fields = ['application__application_number', 'filename']
    readonly_fields = ['uploaded_at']


@admin.register(ApplicationNote)
class ApplicationNoteAdmin(admin.ModelAdmin):
    list_display = ['application', 'created_by', 'created_at', 'note_preview']
    list_filter = ['created_at']
    search_fields = ['application__application_number', 'note']
    readonly_fields = ['created_at']

    def note_preview(self, obj):
        return obj.note[:50] + '...' if len(obj.note) > 50 else obj.note
    note_preview.short_description = 'Note'


@admin.register(ApplicationReview)
class ApplicationReviewAdmin(admin.ModelAdmin):
    list_display = ['application', 'from_status', 'to_status', 'reviewed_by', 'reviewed_at']
    list_filter = ['from_status', 'to_status', 'reviewed_at']
    search_fields = ['application__application_number']
    readonly_fields = ['reviewed_at']
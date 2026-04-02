"""
Admissions App Admin Configuration
"""

from django.contrib import admin
from .models import Application, ApplicationDocument, ApplicationNote, ApplicationReview, AdmissionsPeriod


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
    list_display = ['application_number', 'full_name', 'email', 'applying_for_class', 'status', 'submitted_at', 'payment_status']
    list_filter = ['status', 'application_type', 'applying_for_session', 'applying_for_class']
    search_fields = ['application_number', 'first_name', 'last_name', 'email']
    readonly_fields = ['application_number', 'invoice_id', 'created_at', 'updated_at']
    raw_id_fields = ['applying_for_class', 'applying_for_session', 'reviewed_by', 'created_by']
    inlines = [ApplicationDocumentInline, ApplicationNoteInline, ApplicationReviewInline]

    fieldsets = (
        ('Application Information', {
            'fields': ('application_number', 'status', 'application_type', 'invoice_id')
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

    def payment_status(self, obj):
        """Display payment status from linked invoice"""
        if obj.invoice_id:
            from finance.selectors import InvoiceSelector
            invoice = InvoiceSelector.get_by_id(obj.invoice_id)
            if invoice:
                status = invoice.get('status_display', 'Unknown')
                if invoice.get('status') == 'paid':
                    return admin.utils.display_for_value(f'✅ {status}', True)
                elif invoice.get('status') in ['pending', 'partial']:
                    return admin.utils.display_for_value(f'⏳ {status}', True)
                elif invoice.get('status') == 'overdue':
                    return admin.utils.display_for_value(f'⚠️ {status}', True)
                return admin.utils.display_for_value(status, True)
        return admin.utils.display_for_value('No Invoice', True)
    payment_status.short_description = 'Payment'
    payment_status.admin_order_field = 'invoice_id'


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
    

@admin.register(AdmissionsPeriod)
class AdmissionsPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'academic_session', 'start_date', 'end_date', 'application_fee', 'is_active', 'current_applications', 'max_applications']
    list_filter = ['academic_session', 'is_active']
    search_fields = ['name', 'academic_session__name']
    date_hierarchy = 'start_date'
    readonly_fields = ['current_applications', 'created_at', 'updated_at', 'academic_session']  # Make it readonly
    raw_id_fields = ['created_by']
    
    fieldsets = (
        ('Period Information', {
            'fields': ('name', 'description')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Fee & Capacity', {
            'fields': ('application_fee', 'max_applications', 'current_applications')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Auto-set academic_session to current session"""
        from apps.corecode.selectors import AcademicSessionSelector
        current_session = AcademicSessionSelector.get_current_session()
        if current_session:
            obj.academic_session = current_session
        else:
            from django.contrib import messages
            messages.error(request, 'No current academic session exists. Please set one first.')
            return
        obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """Make academic_session readonly in edit mode too"""
        readonly = super().get_readonly_fields(request, obj)
        if obj:  # Editing existing
            return readonly
        return readonly
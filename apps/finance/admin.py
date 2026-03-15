"""
Finance App Admin Configuration
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import FeeStructure, Invoice, Payment, FeeWaiver


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ['transaction_id', 'amount', 'payment_method', 'status', 'payment_date', 'receipt_number']
    readonly_fields = ['transaction_id', 'receipt_number']
    can_delete = False


class FeeWaiverInline(admin.TabularInline):
    model = FeeWaiver
    extra = 0
    fields = ['amount', 'reason', 'status', 'requested_by', 'approved_by']
    readonly_fields = ['requested_at', 'approved_at']
    can_delete = False


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ['student_class', 'fee_type', 'amount', 'term', 'academic_session', 'is_active']
    list_filter = ['fee_type', 'term', 'is_active', 'academic_session']
    search_fields = ['student_class__name', 'description']
    raw_id_fields = ['student_class', 'academic_session', 'created_by']
    list_editable = ['amount', 'is_active']
    
    fieldsets = (
        ('Fee Details', {
            'fields': ('student_class', 'fee_type', 'amount', 'term', 'description')
        }),
        ('Academic Context', {
            'fields': ('academic_session',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student_class', 'academic_session')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'student_name', 'student_class', 'fee_type', 'total', 'balance', 'status', 'due_date']
    list_filter = ['status', 'fee_type', 'issue_date', 'due_date', 'academic_session', 'academic_term']
    search_fields = ['invoice_number', 'student_name', 'student_id']
    raw_id_fields = ['student_class', 'academic_session', 'academic_term', 'created_by', 'waiver_approved_by']
    readonly_fields = ['invoice_number', 'subtotal', 'total', 'amount_paid', 'balance', 'created_at', 'updated_at']
    inlines = [PaymentInline, FeeWaiverInline]
    
    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'student_id', 'student_name', 'student_class')
        }),
        ('Fee Details', {
            'fields': ('fee_type', 'description', 'subtotal', 'discount_type', 'discount_value', 'discount_amount', 'total')
        }),
        ('Payment Status', {
            'fields': ('amount_paid', 'balance', 'status')
        }),
        ('Dates', {
            'fields': ('issue_date', 'due_date')
        }),
        ('Academic Context', {
            'fields': ('academic_session', 'academic_term')
        }),
        ('Waiver Information', {
            'fields': ('has_waiver', 'waiver_amount', 'waiver_reason', 'waiver_approved_by'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student_class', 'academic_session', 'academic_term')
    
    def status_colored(self, obj):
        colors = {
            'paid': 'green',
            'pending': 'orange',
            'partial': 'blue',
            'overdue': 'red',
            'draft': 'gray',
            'cancelled': 'gray',
            'refunded': 'purple',
        }
        color = colors.get(obj.status, 'gray')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())
    status_colored.short_description = 'Status'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'invoice', 'amount', 'payment_method', 'status', 'payment_date', 'receipt_number']
    list_filter = ['status', 'payment_method', 'payment_date']
    search_fields = ['transaction_id', 'receipt_number', 'invoice__invoice_number', 'invoice__student_name']
    raw_id_fields = ['invoice', 'received_by']
    readonly_fields = ['transaction_id', 'receipt_number', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('transaction_id', 'invoice', 'amount', 'payment_method', 'status')
        }),
        ('Gateway Information', {
            'fields': ('gateway_reference', 'gateway_response'),
            'classes': ('collapse',)
        }),
        ('Receipt', {
            'fields': ('receipt_number', 'payment_date', 'notes')
        }),
        ('Metadata', {
            'fields': ('received_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('invoice', 'received_by')


@admin.register(FeeWaiver)
class FeeWaiverAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'status', 'requested_by', 'approved_by', 'requested_at']
    list_filter = ['status', 'requested_at']
    search_fields = ['invoice__invoice_number', 'invoice__student_name', 'reason']
    raw_id_fields = ['invoice', 'requested_by', 'approved_by']
    readonly_fields = ['requested_at', 'approved_at']
    
    fieldsets = (
        ('Waiver Details', {
            'fields': ('invoice', 'amount', 'reason')
        }),
        ('Status', {
            'fields': ('status', 'approval_notes')
        }),
        ('Request Information', {
            'fields': ('requested_by', 'requested_at')
        }),
        ('Approval Information', {
            'fields': ('approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_waivers', 'reject_waivers']
    
    def approve_waivers(self, request, queryset):
        for waiver in queryset.filter(status='pending'):
            waiver.approve(request.user, "Approved via admin action")
        self.message_user(request, f"{queryset.filter(status='pending').count()} waivers approved.")
    approve_waivers.short_description = "Approve selected waivers"
    
    def reject_waivers(self, request, queryset):
        for waiver in queryset.filter(status='pending'):
            waiver.reject(request.user, "Rejected via admin action")
        self.message_user(request, f"{queryset.filter(status='pending').count()} waivers rejected.")
    reject_waivers.short_description = "Reject selected waivers"
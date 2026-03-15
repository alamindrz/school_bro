"""
Finance Models - The Ledger
Depends on: corecode (AcademicSession, AcademicTerm, StudentClass)
Depends on: students (via student_id only, not direct model)
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass
from .constants import (
    InvoiceStatus, PaymentStatus, PaymentMethod,
    FeeType, FeeTerm, DiscountType, DEFAULT_DUE_DAYS
)

User = get_user_model()


class FeeStructure(models.Model):
    """
    Defines fees for classes and fee types
    Used to generate invoices automatically
    """
    
    # What this fee applies to
    student_class = models.ForeignKey(
        StudentClass,
        on_delete=models.PROTECT,
        related_name='fee_structures'
    )
    fee_type = models.CharField(max_length=20, choices=FeeType.CHOICES)
    
    # Amount and frequency
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    term = models.CharField(
        max_length=20,
        choices=FeeTerm.CHOICES,
        default=FeeTerm.PER_TERM
    )
    
    # Optional: specific session (None means all sessions)
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='fee_structures'
    )
    
    # Description
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_fee_structures'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['student_class', 'fee_type']
        unique_together = [
            ['student_class', 'fee_type', 'academic_session', 'term']
        ]
        indexes = [
            models.Index(fields=['student_class', 'is_active']),
        ]
        verbose_name = _('Fee Structure')
        verbose_name_plural = _('Fee Structures')
    
    def __str__(self):
        session = f" - {self.academic_session.name}" if self.academic_session else ""
        return f"{self.get_fee_type_display()}: ₦{self.amount} ({self.student_class}{session})"


class Invoice(models.Model):
    """
    Student Invoice - Core of the finance system
    CRITICAL: Stores student_id only, not ForeignKey to Student
    This maintains decoupling
    """
    
    # Invoice identification
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique invoice reference (e.g., INV-2024-0001)")
    )
    
    # Student reference (decoupled)
    student_id = models.IntegerField(
        db_index=True,
        help_text=_("Student ID from students app")
    )
    student_name = models.CharField(
        max_length=200,
        help_text=_("Denormalized student name for quick reference")
    )
    student_class = models.ForeignKey(
        StudentClass,
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    
    # Academic context
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    academic_term = models.ForeignKey(
        AcademicTerm,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='invoices'
    )
    
    # Fee details
    fee_type = models.CharField(max_length=20, choices=FeeType.CHOICES)
    description = models.CharField(max_length=255)
    
    # Amounts
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.CHOICES,
        null=True,
        blank=True
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    # Amount paid tracking
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.CHOICES,
        default=InvoiceStatus.DRAFT
    )
    
    # Dates
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    
    # Waiver tracking
    has_waiver = models.BooleanField(default=False)
    waiver_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    waiver_reason = models.TextField(blank=True)
    waiver_approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_invoice_waivers'
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_invoices'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-issue_date', 'student_name']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['student_id']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['academic_session', 'academic_term']),
        ]
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
    
    def __str__(self):
        return f"{self.invoice_number} - {self.student_name} - ₦{self.total}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate balance before saving"""
        self.balance = self.total - self.amount_paid
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        return (
            self.status in InvoiceStatus.REQUIRES_PAYMENT and
            timezone.now().date() > self.due_date
        )
    
    @property
    def payment_progress(self):
        """Calculate payment percentage"""
        if self.total == 0:
            return 100
        return (self.amount_paid / self.total) * 100
    
    def can_transition_to(self, new_status: str) -> bool:
        """Check if status transition is valid"""
        valid_next = InvoiceStatus.VALID_TRANSITIONS.get(self.status, [])
        return new_status in valid_next


class Payment(models.Model):
    """
    Payment transaction against an invoice
    CRITICAL: Implements idempotency for payment processing
    """
    
    # Payment identification
    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Unique transaction reference")
    )
    
    # Link to invoice
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.CHOICES
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.CHOICES,
        default=PaymentStatus.PENDING
    )
    
    # Payment gateway fields (Paystack)
    gateway_reference = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        help_text=_("Paystack reference")
    )
    gateway_response = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Full gateway response for audit")
    )
    
    # Payment metadata
    payment_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Receipt
    receipt_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True
    )
    
    # Metadata
    received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_payments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['gateway_reference']),
            models.Index(fields=['status']),
            models.Index(fields=['invoice', 'payment_date']),
        ]
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
    
    def __str__(self):
        return f"{self.transaction_id} - ₦{self.amount}"
    
    def save(self, *args, **kwargs):
        """Generate receipt number if not set"""
        if not self.receipt_number and self.status == PaymentStatus.COMPLETED:
            self.receipt_number = self._generate_receipt_number()
        super().save(*args, **kwargs)
    
    def _generate_receipt_number(self):
        """Generate unique receipt number"""
        year = timezone.now().year
        prefix = f"RCP-{year}"
        
        last_payment = Payment.objects.filter(
            receipt_number__startswith=prefix
        ).order_by('-receipt_number').first()
        
        if last_payment and last_payment.receipt_number:
            last_num = int(last_payment.receipt_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}-{new_num:04d}"
    
    def mark_completed(self, gateway_ref=None, gateway_resp=None):
        """Mark payment as completed and update invoice"""
        self.status = PaymentStatus.COMPLETED
        self.payment_date = timezone.now()
        if gateway_ref:
            self.gateway_reference = gateway_ref
        if gateway_resp:
            self.gateway_response = gateway_resp
        self.save()
        
        # Update invoice amount paid
        invoice = self.invoice
        invoice.amount_paid += self.amount
        invoice.balance = invoice.total - invoice.amount_paid
        
        # Update invoice status
        if invoice.balance <= 0:
            invoice.status = InvoiceStatus.PAID
        elif invoice.amount_paid > 0:
            invoice.status = InvoiceStatus.PARTIAL
        
        invoice.save()


class FeeWaiver(models.Model):
    """
    Fee waiver request and approval tracking
    """
    
    # Link to invoice
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='waivers'
    )
    
    # Waiver details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    reason = models.TextField()
    
    # Approval workflow
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_waivers'
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_fee_waivers'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-requested_at']
        verbose_name = _('Fee Waiver')
        verbose_name_plural = _('Fee Waivers')
    
    def __str__(self):
        return f"Waiver for {self.invoice.invoice_number} - ₦{self.amount}"
    
    def approve(self, approved_by, notes=""):
        """Approve waiver and apply to invoice"""
        self.status = 'approved'
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.approval_notes = notes
        self.save()
        
        # Update invoice with waiver
        invoice = self.invoice
        invoice.has_waiver = True
        invoice.waiver_amount += self.amount
        invoice.waiver_reason = self.reason
        invoice.waiver_approved_by = approved_by
        
        # Recalculate total with waiver
        invoice.total = invoice.subtotal - invoice.waiver_amount
        invoice.balance = invoice.total - invoice.amount_paid
        invoice.save()
    
    def reject(self, rejected_by, reason):
        """Reject waiver request"""
        self.status = 'rejected'
        self.approved_by = rejected_by
        self.approved_at = timezone.now()
        self.approval_notes = reason
        self.save()
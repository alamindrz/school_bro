"""
Admissions Models - The Gatekeeper
Depends ONLY on: corecode, students (via interfaces, not direct models)
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from apps.corecode.models import AcademicSession, StudentClass
from .constants import (
    ApplicationStatus, ApplicationType, PaymentStatus,
    PaymentMethod, DocumentType, DEFAULT_APPLICATION_FEE
)

User = get_user_model()


class Application(models.Model):
    """
    Student Application - Main admissions model
    CRITICAL: Does NOT import Student model directly
    """
    
    # Application identifiers
    application_number = models.CharField(
        max_length=20,
        unique=True,
        help_text=_("Unique application reference (e.g., APP-2024-0001)")
    )
    
    # Applicant Personal Information
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True)
    
    GENDER_CHOICES = [
        ('M', _('Male')),
        ('F', _('Female')),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    date_of_birth = models.DateField()
    
    # Contact Information
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    alternate_phone = models.CharField(max_length=15, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state_of_origin = models.CharField(max_length=50)
    nationality = models.CharField(max_length=50, default='Nigerian')
    
    # Academic Information
    applying_for_class = models.ForeignKey(
        StudentClass,
        on_delete=models.PROTECT,
        related_name='applications'
    )
    application_type = models.CharField(
        max_length=20,
        choices=ApplicationType.CHOICES,
        default=ApplicationType.NEW
    )
    previous_school = models.CharField(max_length=200, blank=True)
    previous_class = models.CharField(max_length=50, blank=True)
    
    # Guardian Information (denormalized - no separate Guardian model)
    guardian_first_name = models.CharField(max_length=50)
    guardian_last_name = models.CharField(max_length=50)
    guardian_relationship = models.CharField(max_length=50)
    guardian_phone = models.CharField(max_length=15)
    guardian_email = models.EmailField(blank=True)
    guardian_address = models.TextField(blank=True)
    guardian_occupation = models.CharField(max_length=100, blank=True)
    
    # Application Status
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.CHOICES,
        default=ApplicationStatus.DRAFT
    )
    
    # Academic Context
    applying_for_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name='applications'
    )
    
    # Review Tracking
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_applications'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Enrollment Tracking (reference to student once enrolled)
    # CRITICAL: This stores the ID only, NOT a ForeignKey to Student
    # This maintains decoupling - admissions doesn't import students.models
    enrolled_student_id = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("ID of created student record (from students app)")
    )
    enrolled_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_applications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at', 'last_name', 'first_name']
        indexes = [
            models.Index(fields=['application_number']),
            models.Index(fields=['status']),
            models.Index(fields=['email']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = _('Application')
        verbose_name_plural = _('Applications')
    
    def __str__(self):
        return f"{self.application_number} - {self.last_name}, {self.first_name}"
    
    @property
    def full_name(self):
        """Return applicant's full name"""
        if self.middle_name:
            return f"{self.last_name}, {self.first_name} {self.middle_name}"
        return f"{self.last_name}, {self.first_name}"
    
    def can_transition_to(self, new_status: str) -> bool:
        """Check if status transition is valid"""
        valid_next = ApplicationStatus.VALID_TRANSITIONS.get(self.status, [])
        return new_status in valid_next


class ApplicationPayment(models.Model):
    """
    Application Fee Payment
    CRITICAL: Implements idempotency for Paystack callbacks
    """
    
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='payment'
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.CHOICES,
        default=PaymentMethod.PAYSTACK
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.CHOICES,
        default=PaymentStatus.PENDING
    )
    
    # Paystack specific fields
    paystack_reference = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text=_("Paystack transaction reference")
    )
    paystack_access_code = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Paystack access code for initialization")
    )
    paystack_response = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Full Paystack response for audit")
    )
    
    # Transaction tracking
    transaction_date = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['paystack_reference']),
            models.Index(fields=['status']),
        ]
        verbose_name = _('Application Payment')
        verbose_name_plural = _('Application Payments')
    
    def __str__(self):
        return f"Payment for {self.application.application_number} - {self.amount}"
    
    def mark_completed(self, reference: str, response: dict = None):
        """Mark payment as completed with idempotency check"""
        self.status = PaymentStatus.COMPLETED
        self.paystack_reference = reference
        if response:
            self.paystack_response = response
        self.verified_at = timezone.now()
        self.save(update_fields=['status', 'paystack_reference', 'paystack_response', 'verified_at', 'updated_at'])


class ApplicationDocument(models.Model):
    """Supporting documents uploaded with application"""
    
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.CHOICES
    )
    
    file = models.FileField(
        upload_to='applications/documents/%Y/%m/',
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])]
    )
    
    filename = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text=_("File size in bytes"))
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['document_type', '-uploaded_at']
        verbose_name = _('Application Document')
        verbose_name_plural = _('Application Documents')
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.application.application_number}"


class ApplicationNote(models.Model):
    """Internal notes on applications (for reviewers)"""
    
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='notes'
    )
    
    note = models.TextField()
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Application Note')
        verbose_name_plural = _('Application Notes')
    
    def __str__(self):
        return f"Note on {self.application.application_number} by {self.created_by}"


class ApplicationReview(models.Model):
    """Review history for applications"""
    
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    
    from_status = models.CharField(max_length=20, choices=ApplicationStatus.CHOICES)
    to_status = models.CharField(max_length=20, choices=ApplicationStatus.CHOICES)
    
    notes = models.TextField(blank=True)
    
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    reviewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-reviewed_at']
        verbose_name = _('Application Review')
        verbose_name_plural = _('Application Reviews')
    
    def __str__(self):
        return f"{self.application.application_number}: {self.from_status} → {self.to_status}"
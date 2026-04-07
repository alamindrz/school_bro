"""
Admissions Models - The Gatekeeper
Depends ONLY on: corecode, students (via interfaces, not direct models)
"""

from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from apps.corecode.models import AcademicSession, StudentClass
from .constants import (
    ApplicationStatus, ApplicationType, DocumentType
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
    
    # Contact Information - ALL OPTIONAL for students without contact
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    alternate_phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=50, blank=True)
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
    
    # Guardian Information (required - primary contact)
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
    
    # Link to finance invoice (not payment directly)
    invoice_id = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("ID of created invoice from apps.finance app")
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
            models.Index(fields=['invoice_id']),
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
    
    @property
    def payment_completed(self) -> bool:
        """Check if associated invoice is paid"""
        if self.invoice_id:
            from apps.finance.selectors import InvoiceSelector
            invoice = InvoiceSelector.get_by_id(self.invoice_id)
            return invoice and invoice.get('status') == 'paid'
        return False
    
    def can_transition_to(self, new_status: str) -> bool:
        """Check if status transition is valid"""
        valid_next = ApplicationStatus.VALID_TRANSITIONS.get(self.status, [])
        return new_status in valid_next


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
        

class AdmissionsPeriod(models.Model):
    """
    Track when admissions are open and for which session.
    Allows multiple admission periods per session (early admission, regular, late)
    """
    
    # Link to academic session
    academic_session = models.ForeignKey(
        'corecode.AcademicSession',
        on_delete=models.PROTECT,
        related_name='admission_periods'
    )
    
    # Period details
    name = models.CharField(max_length=100, help_text="e.g., 'Early Admission', 'Regular Admission'")
    description = models.TextField(blank=True)
    
    # Dates
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True, help_text="Leave blank for open-ended")
    
    # Fee configuration
    application_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=5000,
        help_text="Application fee for this period (can differ by period)"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="If active, applications can be submitted during this period"
    )
    
    # Capacity limits (optional)
    max_applications = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum applications allowed for this period (leave blank for unlimited)"
    )
    current_applications = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_admission_periods'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['academic_session', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]
        verbose_name = 'Admissions Period'
        verbose_name_plural = 'Admissions Periods'
    
    def __str__(self):
        return f"{self.name} - {self.academic_session.name}"
    
    def is_currently_open(self):
        """Check if this period is currently open for applications"""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        if self.max_applications and self.current_applications >= self.max_applications:
            return False
        return True
    
    def has_capacity(self):
        """Check if there's capacity for more applications"""
        if not self.max_applications:
            return True
        return self.current_applications < self.max_applications
    
    def increment_application_count(self):
        """Increment the application counter (call when application is created)"""
        self.current_applications += 1
        self.save(update_fields=['current_applications'])
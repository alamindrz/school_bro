"""
Student Models - Core CRM
Depends ONLY on corecode (AcademicSession, StudentClass)
"""

from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator, MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.corecode.models import AcademicSession, StudentClass
from .constants import StudentStatus, StudentCreationMethod, GuardianRelationship, BloodGroup

User = get_user_model()


class Student(models.Model):
    """
    Core Student Model - The heart of the system.
    All other apps revolve around this.
    """
    
    # Core Identity
    admission_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[MinLengthValidator(5)],
        help_text=_("Unique student identifier")
    )
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile'
    )
    
    # Personal Information
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True)
    
    GENDER_CHOICES = [
        ('M', _('Male')),
        ('F', _('Female')),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    date_of_birth = models.DateField()
    blood_group = models.CharField(max_length=3, choices=BloodGroup.CHOICES, blank=True)
    
    # Contact Information
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=50, blank=True)
    state_of_origin = models.CharField(max_length=50, blank=True)
    nationality = models.CharField(max_length=50, default='Nigerian')
 
    
    application_id = models.IntegerField(
        null=True, 
        blank=True,
        help_text="ID of the admissions application that created this student"
    )
    application_number = models.CharField(
        max_length=20, 
        null=True, 
        blank=True,
        help_text="Application number from admissions app"
    )   
        
    
    # Academic Information
    current_class = models.ForeignKey(
        StudentClass,
        on_delete=models.PROTECT,
        related_name='current_students'
    )
    enrollment_date = models.DateField(default=timezone.now)
    enrollment_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name='enrolled_students'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=StudentStatus.CHOICES,
        default=StudentStatus.ACTIVE
    )
    
    # Metadata
    created_via = models.CharField(
        max_length=20,
        choices=StudentCreationMethod.CHOICES,
        default=StudentCreationMethod.MANUAL
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_students'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Medical & Special Needs
    medical_notes = models.TextField(blank=True)
    has_special_needs = models.BooleanField(default=False)
    special_needs_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['admission_number', 'last_name', 'first_name']
        indexes = [
            models.Index(fields=['admission_number']),
            models.Index(fields=['status']),
            models.Index(fields=['current_class', 'status']),
        ]
        verbose_name = _('Student')
        verbose_name_plural = _('Students')
    
    def __str__(self):
        return f"{self.admission_number} - {self.get_full_name}"
    
    @property
    def get_full_name(self):
        """Return full name"""
        if self.middle_name:
            return f"{self.last_name}, {self.first_name} {self.middle_name}"
        return f"{self.last_name}, {self.first_name}"
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    def can_transition_to(self, new_status: str) -> bool:
        """Check if status transition is valid"""
        from .constants import StudentStatus
        valid_next = StudentStatus.VALID_TRANSITIONS.get(self.status, [])
        return new_status in valid_next


class Guardian(models.Model):
    """
    Parent/Guardian Information
    """
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='guardians'
    )
    
    # Identity
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    relationship = models.CharField(max_length=20, choices=GuardianRelationship.CHOICES)
    
    # Contact
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15)
    alternate_phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    
    # Professional
    occupation = models.CharField(max_length=100, blank=True)
    employer = models.CharField(max_length=100, blank=True)
    
    # Metadata
    is_primary = models.BooleanField(default=False)
    is_emergency_contact = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_primary', 'last_name', 'first_name']
        unique_together = ['student', 'email']  # Prevent duplicate guardians
    
    def __str__(self):
        return f"{self.get_full_name} ({self.get_relationship_display()})"
    
    @property
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class StudentHistory(models.Model):
    """
    Audit trail for student status changes and promotions
    """
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='history'
    )
    
    # Academic context
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT
    )
    term = models.IntegerField(choices=[(1, 'First'), (2, 'Second'), (3, 'Third')])
    
    # Status at this point in time
    class_at_time = models.ForeignKey(
        StudentClass,
        on_delete=models.PROTECT,
        related_name='student_histories'
    )
    status_at_time = models.CharField(max_length=20, choices=StudentStatus.CHOICES)
    
    # Action details
    action = models.CharField(max_length=50)  # ENROLLED, PROMOTED, GRADUATED, etc.
    previous_class = models.ForeignKey(
        StudentClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    notes = models.TextField(blank=True)
    
    # Who performed the action
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    performed_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['student', '-performed_at']),
            models.Index(fields=['academic_session', 'term']),
        ]
    
    def __str__(self):
        return f"{self.student} - {self.action} - {self.performed_at.date()}"


class SavedStudentSearch(models.Model):
    """
    Model for saved searches (would be in models.py)
    """
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_searches')
    search_params = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('students:saved_search', args=[self.id])
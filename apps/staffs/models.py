"""
Staffs Models - Comprehensive staff management for Nigerian schools
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
import uuid

from apps.corecode.models import StudentClass, Subject
from .constants import (
    StaffType, StaffCategory, STAFF_CATEGORY_MAP,
    EmploymentStatus, EmploymentType, ShiftType,
    QualificationType, LeaveType, LeaveStatus,
    Gender, MaritalStatus, BloodGroup, DutyPost,
    NIGERIAN_STATES
)

User = get_user_model()


class Staff(models.Model):
    """
    Comprehensive Staff Model for Nigerian Schools
    Handles all staff types from Principal to Cleaner
    """
    
    # Identification
    staff_id = models.CharField(
        max_length=20,
        unique=True,
        help_text=_("Unique staff identifier (e.g., STF-2024-001)")
    )
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_profile'
    )
    
    # Personal Information
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.CHOICES)
    date_of_birth = models.DateField()
    marital_status = models.CharField(
        max_length=20,
        choices=MaritalStatus.CHOICES,
        default=MaritalStatus.SINGLE
    )
    blood_group = models.CharField(
        max_length=3,
        choices=BloodGroup.CHOICES,
        blank=True
    )
    
    # Contact Information
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    alternate_phone = models.CharField(max_length=15, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state_of_origin = models.CharField(max_length=50, choices=[(s, s) for s in NIGERIAN_STATES])
    lga = models.CharField(max_length=50, blank=True, help_text=_("Local Government Area"))
    nationality = models.CharField(max_length=50, default='Nigerian')
    
    # Photograph
    passport_photograph = models.ImageField(
        upload_to='staff/passports/%Y/%m/',
        null=True, blank=True
    )
    
    # Employment Information
    staff_type = models.CharField(
        max_length=30,
        choices=StaffType.CHOICES
    )

    invite_token = models.UUIDField(unique=True, null=True, editable=False)
    invite_sent_at = models.DateTimeField(null=True, blank=True)
    invite_accepted_at = models.DateTimeField(null=True, blank=True)
    invite_expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)  
    staff_category = models.CharField(
        max_length=20,
        choices=StaffCategory.CHOICES,
        editable=False
    )
    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.CHOICES,
        default=EmploymentStatus.ACTIVE
    )
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.CHOICES,
        default=EmploymentType.PERMANENT
    )
    shift = models.CharField(
        max_length=20,
        choices=ShiftType.CHOICES,
        default=ShiftType.FIXED,
        help_text=_("Applicable for kitchen, security, etc.")
    )
    date_employed = models.DateField()
    date_confirmed = models.DateField(null=True, blank=True)
    retirement_date = models.DateField(null=True, blank=True)
    
    # Department/Unit
    department = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=100, blank=True)
    
    # Supervisor
    supervisor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates'
    )
    
    # Qualifications
    highest_qualification = models.CharField(
        max_length=20,
        choices=QualificationType.CHOICES,
        default=QualificationType.DEGREE
    )
    qualification_details = models.TextField(blank=True)
    
    # Bank Details
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=20, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    pension_number = models.CharField(max_length=50, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=200)
    emergency_contact_phone = models.CharField(max_length=15)
    emergency_contact_relationship = models.CharField(max_length=50)
    
    # Medical Information
    medical_conditions = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    doctor_name = models.CharField(max_length=200, blank=True)
    doctor_phone = models.CharField(max_length=15, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_staff'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['staff_id']),
            models.Index(fields=['staff_type']),
            models.Index(fields=['staff_category']),
            models.Index(fields=['employment_status']),
            models.Index(fields=['email']),
        ]
        verbose_name = _('Staff Member')
        verbose_name_plural = _('Staff Members')
    
    def __str__(self):
        return f"{self.staff_id} - {self.get_full_name}"
    
    def create_user_account(self, password=None):
        """Create or get Django user account for staff"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not self.user:
            username = self.staff_id.lower()
            if not password:
                import secrets
                import string
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for _ in range(12))
            
            user = User.objects.create_user(
                username=username,
                email=self.email,
                password=password,
                first_name=self.first_name,
                last_name=self.last_name,
                is_staff=True  # Staff can access admin
            )
            self.user = user
            self.save(update_fields=['user'])
            
            # TODO: Send email with password
            return user, password
        return self.user, None
        
    
    def save(self, *args, **kwargs):
        """Auto-set staff category based on staff type"""
        self.staff_category = STAFF_CATEGORY_MAP.get(self.staff_type, StaffCategory.SUPPORT)
        
        # Generate staff ID if not set
        if not self.staff_id:
            self.staff_id = self._generate_staff_id()
        
        super().save(*args, **kwargs)
    
    def _generate_staff_id(self):
        """Generate unique staff ID"""
        year = timezone.now().year
        prefix = f"STF-{year}"
        
        last_staff = Staff.objects.filter(
            staff_id__startswith=prefix
        ).order_by('-staff_id').first()
        
        if last_staff:
            last_num = int(last_staff.staff_id.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}-{new_num:04d}"
    
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
    
    @property
    def years_of_service(self):
        """Calculate years of service"""
        today = timezone.now().date()
        return today.year - self.date_employed.year - (
            (today.month, today.day) < (self.date_employed.month, self.date_employed.day)
        )



class TeacherSubjectQualification(models.Model):
    """
    Links teachers to subjects they are qualified to teach.
    Global qualifications - applies to ALL classes.
    """
    teacher = models.ForeignKey(
        'Staff',
        on_delete=models.CASCADE,
        related_name='qualified_subjects'
    )
    subject = models.ForeignKey(
        'corecode.Subject',
        on_delete=models.CASCADE,
        related_name='qualified_teachers'
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary subject for this teacher"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        unique_together = ['teacher', 'subject']
        verbose_name = 'Teacher Subject Qualification'
        verbose_name_plural = 'Teacher Subject Qualifications'
        permissions = [
            ("manage_qualifications", "Can manage teacher subject qualifications"),
        ]
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.subject.name}"


class DutyAssignment(models.Model):
    """
    Non-teaching duties and responsibilities
    For sports masters, club patrons, duty posts, etc.
    """
    
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='duties'
    )
    duty_post = models.CharField(
        max_length=30,
        choices=DutyPost.CHOICES
    )
    
    # Context
    academic_session = models.ForeignKey(
        'corecode.AcademicSession',
        on_delete=models.CASCADE,
        related_name='staff_duties'
    )
    student_class = models.ForeignKey(
        StudentClass,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text=_("For form masters, class teachers")
    )
    club_name = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("For club patrons")
    )
    sport_name = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("For sports masters")
    )
    house_name = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("For housemasters (Red House, Blue House, etc.)")
    )
    
    # Schedule
    day_of_week = models.IntegerField(
        choices=[(i, _(f"Day {i}")) for i in range(1, 8)],
        null=True, blank=True
    )
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_duties'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['duty_post', 'staff']
        verbose_name = _('Duty Assignment')
        verbose_name_plural = _('Duty Assignments')
    
    def __str__(self):
        return f"{self.staff.get_full_name} - {self.get_duty_post_display()}"


class LeaveRequest(models.Model):
    """
    Staff leave management
    """
    
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    leave_type = models.CharField(
        max_length=20,
        choices=LeaveType.CHOICES
    )
    
    # Dates
    start_date = models.DateField()
    end_date = models.DateField()
    return_date = models.DateField()
    
    # Details
    reason = models.TextField()
    handover_notes = models.TextField(blank=True)
    
    # Contact during leave
    alternative_phone = models.CharField(max_length=15, blank=True)
    alternative_email = models.EmailField(blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=LeaveStatus.CHOICES,
        default=LeaveStatus.PENDING
    )
    
    # Approval workflow
    approved_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_leaves'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['staff', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
        verbose_name = _('Leave Request')
        verbose_name_plural = _('Leave Requests')
    
    def __str__(self):
        return f"{self.staff.get_full_name} - {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"
    
    @property
    def days_requested(self):
        """Calculate number of days requested"""
        return (self.end_date - self.start_date).days + 1


class StaffAttendance(models.Model):
    """
    Daily staff attendance tracking
    """
    
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField(default=timezone.now)
    
    # Check in/out
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    
    # Status
    STATUS_CHOICES = [
        ('present', _('Present')),
        ('absent', _('Absent')),
        ('late', _('Late')),
        ('on_leave', _('On Leave')),
        ('half_day', _('Half Day')),
        ('official', _('Official Duty')),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='present'
    )
    
    # Location (for gate security)
    check_in_location = models.CharField(max_length=255, blank=True)
    check_out_location = models.CharField(max_length=255, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Metadata
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', 'staff']
        unique_together = ['staff', 'date']
        verbose_name = _('Staff Attendance')
        verbose_name_plural = _('Staff Attendances')
    
    def __str__(self):
        return f"{self.staff.get_full_name} - {self.date} - {self.get_status_display()}"


class Qualification(models.Model):
    """
    Staff qualifications and certifications
    """
    
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='qualifications'
    )
    qualification_type = models.CharField(
        max_length=20,
        choices=QualificationType.CHOICES
    )
    title = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    year_obtained = models.IntegerField()
    
    # For certifications
    certificate_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    # Document
    document = models.FileField(
        upload_to='staff/qualifications/%Y/%m/',
        null=True, blank=True
    )
    
    # Metadata
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verified_qualifications'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-year_obtained']
        verbose_name = _('Qualification')
        verbose_name_plural = _('Qualifications')
    
    def __str__(self):
        return f"{self.staff.get_full_name} - {self.title} ({self.year_obtained})"


class WorkExperience(models.Model):
    """
    Previous work experience
    """
    
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='work_experiences'
    )
    employer = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    
    responsibilities = models.TextField(blank=True)
    
    # Reference
    referee_name = models.CharField(max_length=200, blank=True)
    referee_phone = models.CharField(max_length=15, blank=True)
    referee_email = models.EmailField(blank=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = _('Work Experience')
        verbose_name_plural = _('Work Experiences')
    
    def __str__(self):
        return f"{self.staff.get_full_name} - {self.position} at {self.employer}"


class PerformanceEvaluation(models.Model):
    """
    Staff performance evaluation records
    """
    
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='evaluations'
    )
    evaluator = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='evaluations_done'
    )
    
    evaluation_date = models.DateField()
    evaluation_period = models.CharField(
        max_length=50,
        help_text=_("e.g., Term 1 2024, Annual 2023")
    )
    
    # Ratings (1-5)
    punctuality = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    job_knowledge = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    quality_of_work = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    communication = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    teamwork = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    initiative = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Comments
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    overall_comments = models.TextField(blank=True)
    
    # Overall rating
    overall_rating = models.FloatField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        editable=False
    )
    
    # Recommendations
    recommendation = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-evaluation_date']
        verbose_name = _('Performance Evaluation')
        verbose_name_plural = _('Performance Evaluations')
    
    def save(self, *args, **kwargs):
        """Calculate overall rating"""
        ratings = [
            self.punctuality,
            self.job_knowledge,
            self.quality_of_work,
            self.communication,
            self.teamwork,
            self.initiative
        ]
        self.overall_rating = sum(ratings) / len(ratings)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.staff.get_full_name} - {self.evaluation_period} ({self.overall_rating:.1f}/5)"


class StaffDocument(models.Model):
    """
    Staff documents (contracts, letters, etc.)
    """
    
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    DOCUMENT_TYPES = [
        ('appointment', _('Appointment Letter')),
        ('confirmation', _('Confirmation Letter')),
        ('promotion', _('Promotion Letter')),
        ('contract', _('Employment Contract')),
        ('id_card', _('ID Card')),
        ('resume', _('Resume/CV')),
        ('certificate', _('Certificate')),
        ('other', _('Other')),
    ]
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='staff/documents/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = _('Staff Document')
        verbose_name_plural = _('Staff Documents')
    
    def __str__(self):
        return f"{self.staff.get_full_name} - {self.title}"
        
        
class PortalSession(models.Model):
    """Track staff magic link sessions"""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='sessions')
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
"""
Corecode Models - The Foundation
Zero dependencies on other apps.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .constants import EducationLevel, NigerianClassLevel, TermType, SiteConfigKey, SubjectType

User = get_user_model()


class AcademicSession(models.Model):
    """
    Academic Session (e.g., 2024/2025)
    Pure foundation - no dependencies
    """
    name = models.CharField(max_length=50, unique=True, help_text=_("e.g., 2024/2025"))
    code = models.CharField(max_length=20, unique=True, help_text=_("e.g., 202425"))
    is_current = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = _('Academic Session')
        verbose_name_plural = _('Academic Sessions')
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Ensure only one current session"""
        if self.is_current:
            AcademicSession.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


class AcademicTerm(models.Model):
    """
    Academic Term (First, Second, Third)
    Pure foundation - no dependencies
    """
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='terms'
    )
    term = models.IntegerField(choices=TermType.CHOICES)
    name = models.CharField(max_length=50, help_text=_("e.g., First Term 2024/2025"))
    is_current = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['session', 'term']
        unique_together = ['session', 'term']
        verbose_name = _('Academic Term')
        verbose_name_plural = _('Academic Terms')
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Ensure only one current term"""
        if self.is_current:
            AcademicTerm.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


class StudentClass(models.Model):
    """
    Student Class - Strict Nigerian 6-3-3-4 structure
    No custom classes allowed - must map to NigerianClassLevel
    """
    name = models.CharField(max_length=20, choices=NigerianClassLevel.CHOICES)
    stream = models.CharField(
        max_length=10,
        blank=True,
        default='',
        help_text="Class stream/group (e.g., 'A', 'B', 'C' or leave blank for no stream)"
    )
    display_name = models.CharField(max_length=50)
    education_level = models.CharField(max_length=20, choices=EducationLevel.CHOICES)
    
    # Class properties
    max_students = models.PositiveIntegerField(default=40, validators=[MinValueValidator(1)])
    sort_order = models.PositiveIntegerField(default=0, help_text=_("Used for ordering classes"))
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'name', 'stream']
        unique_together = ['name', 'stream']  # SS1 + A = SS1A
        verbose_name = _('Student Class')
        verbose_name_plural = _('Student Classes')
    
    def __str__(self):
        if self.stream:
            return f"{self.display_name} {self.stream}"
        return self.display_name
    
    @property
    def full_name(self):
        """Get full class name with stream"""
        if self.stream:
            return f"{self.display_name} {self.stream}"
        return self.display_name
    
    
    @property
    def next_class(self):
        """Get the next class in progression (respects streams)"""
        next_class_name = NigerianClassLevel.NEXT_CLASS.get(self.name)
        if next_class_name:
            try:
                # If this class has a stream, try to find the same stream in next class
                if self.stream:
                    return StudentClass.objects.get(name=next_class_name, stream=self.stream)
                else:
                    # No stream, get any active class with this name
                    return StudentClass.objects.filter(name=next_class_name, is_active=True).first()
            except StudentClass.DoesNotExist:
                return None
            except StudentClass.MultipleObjectsReturned:
                # Multiple streams exist, return the first one
                return StudentClass.objects.filter(name=next_class_name, is_active=True).first()
        return None


    @property
    def is_graduating_class(self):
        """Check if this is SS3 - graduation year"""
        return self.name == NigerianClassLevel.SS_3


class Subject(models.Model):
    """
    Subject/Course master list
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    subject_type = models.CharField(
        max_length=20,
        choices=SubjectType.CHOICES,
        default=SubjectType.CORE
    )
    
    # Which classes offer this subject
    offered_in_classes = models.ManyToManyField(
        StudentClass,
        related_name='subjects',
        blank=True
    )
    
    # Subject details
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    # For Nigerian curriculum
    is_nigerian_core = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = _('Subject')
        verbose_name_plural = _('Subjects')
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class SiteConfig(models.Model):
    """
    The "No-Customization" Rule implementation.
    Every school-specific requirement becomes a toggle here.
    Never change code - change config.
    """
    key = models.CharField(max_length=100, unique=True, choices=[
        (key, key) for key in SiteConfigKey.ALL_KEYS
    ])
    value = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True)
    
    # Metadata
    is_public = models.BooleanField(default=False, help_text=_("Visible in public API"))
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='site_config_updates'
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Site Configuration')
        verbose_name_plural = _('Site Configurations')
    
    def __str__(self):
        return f"{self.key}: {self.value}"
    
    @classmethod
    def get(cls, key, default=None):
        """Get config value with type inference"""
        try:
            config = cls.objects.get(key=key)
            value = config.value
            
            # Type inference
            if value is None or value == '':
                return default
            
            # Boolean
            if value.lower() in ('true', 'false', '1', '0'):
                return value.lower() in ('true', '1')
            
            # Integer
            try:
                return int(value)
            except ValueError:
                pass
            
            # Float
            try:
                return float(value)
            except ValueError:
                pass
            
            return value
            
        except cls.DoesNotExist:
            return default


class SystemLog(models.Model):
    """
    Comprehensive audit trail for all sensitive operations.
    Tracks who did what and when across the entire platform.
    """
    class ActionType(models.TextChoices):
        CREATE = 'CREATE', _('Create')
        UPDATE = 'UPDATE', _('Update')
        DELETE = 'DELETE', _('Delete')
        VIEW = 'VIEW', _('View')
        LOGIN = 'LOGIN', _('Login')
        LOGOUT = 'LOGOUT', _('Logout')
        EXPORT = 'EXPORT', _('Export')
        IMPORT = 'IMPORT', _('Import')
        PROMOTION = 'PROMOTION', _('Promotion')
        PAYMENT = 'PAYMENT', _('Payment')
        GRADE_CHANGE = 'GRADE_CHANGE', _('Grade Change')
        WAIVER = 'WAIVER', _('Fee Waiver')
    
    class AppLabel(models.TextChoices):
        CORE = 'corecode', _('Core')
        STUDENTS = 'students', _('Students')
        STAFFS = 'staffs', _('Staff')
        ADMISSIONS = 'admissions', _('Admissions')
        FINANCE = 'finance', _('Finance')
        RESULTS = 'results', _('Results')
        ATTENDANCE = 'attendance', _('Attendance')
        TIMETABLE = 'timetable', _('Timetable')
    
    # Who
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_logs'
    )
    username = models.CharField(max_length=150, blank=True)  # Denormalized for preservation
    
    # What
    action = models.CharField(max_length=20, choices=ActionType.choices)
    app_label = models.CharField(max_length=20, choices=AppLabel.choices)
    model_name = models.CharField(max_length=50)
    object_id = models.CharField(max_length=50, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    
    # Changes
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # When
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['app_label', 'model_name']),
            models.Index(fields=['user', '-timestamp']),
        ]
        verbose_name = _('System Log')
        verbose_name_plural = _('System Logs')
    
    def save(self, *args, **kwargs):
        """Denormalize username on save"""
        if self.user and not self.username:
            self.username = self.user.get_username()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.timestamp}: {self.user} - {self.action} on {self.model_name}"
        
class AdmissionSequence(models.Model):
    """
    Registry for tracking the last issued sequence number for admissions.
    
    This model implements a 'Table-Based Generator' pattern. By separating 
    counters from the Student model, we avoid expensive table scans and 
    locking issues on the main Student table during high-concurrency periods 
    (e.g., peak enrollment days).
    """
    session_code = models.CharField(
        max_length=10, 
        help_text="The academic session code (e.g., 202425)"
    )
    class_code = models.CharField(
        max_length=10, 
        help_text="The standardized class code (e.g., S01)"
    )
    last_value = models.PositiveIntegerField(
        default=0,
        help_text="The last sequence number successfully assigned"
    )

    class Meta:
        unique_together = ('session_code', 'class_code')
        verbose_name = "Admission Sequence"
        verbose_name_plural = "Admission Sequences"

    def __str__(self):
        return f"{self.session_code}/{self.class_code} -> {self.last_value}"





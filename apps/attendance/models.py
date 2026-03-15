"""
Attendance Models - Track student attendance
Depends on: corecode, students (via student_id only)
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from datetime import date, time, timedelta
import uuid

from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass
from .constants import (
    AttendanceStatus, SessionType, MarkingMethod,
    LOW_ATTENDANCE_THRESHOLD, CRITICAL_ATTENDANCE_THRESHOLD
)

User = get_user_model()


class AttendanceRegister(models.Model):
    """
    Daily attendance register for a class
    Groups attendance records for a specific date and session
    """
    
    # Identification
    register_number = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique register identifier")
    )
    
    # Context
    student_class = models.ForeignKey(
        StudentClass,
        on_delete=models.PROTECT,
        related_name='attendance_registers'
    )
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name='attendance_registers'
    )
    academic_term = models.ForeignKey(
        AcademicTerm,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='attendance_registers'
    )
    
    # Date and session
    date = models.DateField(default=date.today)
    session_type = models.CharField(
        max_length=20,
        choices=SessionType.CHOICES,
        default=SessionType.MORNING
    )
    
    # Metadata
    total_students = models.IntegerField(default=0)
    present_count = models.IntegerField(default=0)
    absent_count = models.IntegerField(default=0)
    late_count = models.IntegerField(default=0)
    excused_count = models.IntegerField(default=0)
    
    # Status
    is_closed = models.BooleanField(
        default=False,
        help_text=_("Register closed for further edits")
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_registers'
    )
    
    # Metadata
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_registers'
    )
    marking_method = models.CharField(
        max_length=20,
        choices=MarkingMethod.CHOICES,
        default=MarkingMethod.MANUAL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', 'student_class', 'session_type']
        unique_together = ['student_class', 'date', 'session_type']
        indexes = [
            models.Index(fields=['student_class', 'date']),
            models.Index(fields=['academic_session', 'academic_term']),
            models.Index(fields=['register_number']),
        ]
        verbose_name = _('Attendance Register')
        verbose_name_plural = _('Attendance Registers')
    
    def __str__(self):
        return f"{self.student_class.display_name} - {self.date} ({self.get_session_type_display()})"
    
    def save(self, *args, **kwargs):
        """Generate register number if not set"""
        if not self.register_number:
            self.register_number = self._generate_register_number()
        super().save(*args, **kwargs)
    
    def _generate_register_number(self):
        """Generate unique register number"""
        date_str = self.date.strftime('%Y%m%d')
        class_code = self.student_class.name
        session_code = self.session_type[:3].upper()
        unique_id = str(uuid.uuid4()).split('-')[0].upper()
        return f"ATT-{date_str}-{class_code}-{session_code}-{unique_id}"
    
    def update_counts(self):
        """Update attendance counts from records"""
        self.total_students = self.records.count()
        self.present_count = self.records.filter(status=AttendanceStatus.PRESENT).count()
        self.absent_count = self.records.filter(status=AttendanceStatus.ABSENT).count()
        self.late_count = self.records.filter(status=AttendanceStatus.LATE).count()
        self.excused_count = self.records.filter(
            status__in=[AttendanceStatus.EXCUSED, AttendanceStatus.SICK]
        ).count()
        self.save(update_fields=[
            'total_students', 'present_count', 'absent_count',
            'late_count', 'excused_count', 'updated_at'
        ])
    
    @property
    def present_percentage(self):
        """Calculate present percentage"""
        if self.total_students == 0:
            return 0
        return (self.present_count / self.total_students) * 100


class AttendanceRecord(models.Model):
    """
    Individual student attendance record
    """
    
    register = models.ForeignKey(
        AttendanceRegister,
        on_delete=models.CASCADE,
        related_name='records'
    )
    
    # Student reference (decoupled)
    student_id = models.IntegerField(
        db_index=True,
        help_text=_("Student ID from students app")
    )
    student_name = models.CharField(
        max_length=200,
        help_text=_("Denormalized student name")
    )
    
    # Attendance details
    status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.CHOICES,
        default=AttendanceStatus.PRESENT
    )
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    
    # Notes
    remarks = models.TextField(blank=True)
    
    # Metadata
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendance'
    )
    marked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['register__date', 'student_name']
        unique_together = ['register', 'student_id']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['status']),
            models.Index(fields=['register', 'student_id']),
        ]
        verbose_name = _('Attendance Record')
        verbose_name_plural = _('Attendance Records')
    
    def __str__(self):
        return f"{self.student_name} - {self.register.date} - {self.get_status_display()}"
    
    @property
    def is_present(self):
        return self.status == AttendanceStatus.PRESENT
    
    @property
    def is_absent(self):
        return self.status == AttendanceStatus.ABSENT
    
    @property
    def is_late(self):
        return self.status == AttendanceStatus.LATE
    
    @property
    def is_excused(self):
        return self.status in [AttendanceStatus.EXCUSED, AttendanceStatus.SICK]


class QRCode(models.Model):
    """
    QR codes for student attendance marking
    Each student can have a QR code for quick check-in
    """
    
    # Student reference
    student_id = models.IntegerField(
        unique=True,
        db_index=True,
        help_text=_("Student ID from students app")
    )
    student_name = models.CharField(
        max_length=200,
        help_text=_("Denormalized student name")
    )
    
    # QR code data
    code = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Unique QR code value")
    )
    qr_image = models.ImageField(
        upload_to='attendance/qrcodes/%Y/%m/',
        null=True,
        blank=True
    )
    
    # Validity
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    last_used = models.DateTimeField(null=True, blank=True)
    use_count = models.IntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['student_id']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = _('QR Code')
        verbose_name_plural = _('QR Codes')
    
    def __str__(self):
        return f"QR Code for {self.student_name}"
    
    def is_valid(self):
        """Check if QR code is valid and not expired"""
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
    
    def record_use(self):
        """Record usage of QR code"""
        self.last_used = timezone.now()
        self.use_count += 1
        self.save(update_fields=['last_used', 'use_count'])


class AttendanceSummary(models.Model):
    """
    Aggregated attendance summary for students
    Updated periodically or on demand
    """
    
    # Student reference
    student_id = models.IntegerField(
        db_index=True,
        help_text=_("Student ID from students app")
    )
    student_name = models.CharField(max_length=200)
    
    # Academic context
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name='attendance_summaries'
    )
    academic_term = models.ForeignKey(
        AcademicTerm,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='attendance_summaries'
    )
    
    # Counts
    total_days = models.IntegerField(default=0)
    present_days = models.IntegerField(default=0)
    absent_days = models.IntegerField(default=0)
    late_days = models.IntegerField(default=0)
    excused_days = models.IntegerField(default=0)
    
    # Percentages
    present_percentage = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    attendance_score = models.FloatField(
        default=0,
        help_text=_("Weighted attendance score")
    )
    
    # Alerts
    attendance_alert = models.BooleanField(default=False)
    alert_reason = models.CharField(max_length=255, blank=True)
    
    # Metadata
    last_calculated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-academic_session', '-academic_term', 'student_name']
        unique_together = ['student_id', 'academic_session', 'academic_term']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['attendance_alert']),
        ]
        verbose_name = _('Attendance Summary')
        verbose_name_plural = _('Attendance Summaries')
    
    def __str__(self):
        return f"{self.student_name} - {self.academic_session} - {self.present_percentage}%"
    

    def calculate_percentages(self):
        """Calculate attendance percentages"""
        if self.total_days > 0:
            self.present_percentage = (self.present_days / self.total_days) * 100
        else:
            self.present_percentage = 0
        
        # Calculate weighted score (present=1, late=0.5, excused=0.75, absent=0)
        weighted = (
            self.present_days * 1.0 +
            self.late_days * 0.5 +
            self.excused_days * 0.75
        )
        self.attendance_score = (weighted / self.total_days * 100) if self.total_days > 0 else 0
        
        # Set alerts
        if self.present_percentage < CRITICAL_ATTENDANCE_THRESHOLD:
            self.attendance_alert = True
            self.alert_reason = f"Critical attendance: {self.present_percentage:.1f}%"
        elif self.present_percentage < LOW_ATTENDANCE_THRESHOLD:
            self.attendance_alert = True
            self.alert_reason = f"Low attendance: {self.present_percentage:.1f}%"
        else:
            self.attendance_alert = False
            self.alert_reason = ""
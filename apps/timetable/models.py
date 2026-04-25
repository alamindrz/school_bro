"""
Timetable Models - School timetable management
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass, Subject
from apps.staffs.models import Staff

User = get_user_model()


class SchoolDay(models.Model):
    """Days of the week the school operates"""
    
    DAY_CHOICES = [
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
        (7, 'Sunday'),
    ]
    
    day_number = models.IntegerField(choices=DAY_CHOICES, unique=True)
    name = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    # Friday special hours
    is_friday = models.BooleanField(default=False)
    friday_start_time = models.TimeField(null=True, blank=True)
    friday_end_time = models.TimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'School Day'
        verbose_name_plural = 'School Days'
    
    def __str__(self):
        return self.name


class PeriodType(models.Model):
    """Types of periods (Teaching, Break, Assembly, Closing, etc.)"""
    
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, unique=True)
    is_teaching = models.BooleanField(default=True)
    duration_minutes = models.IntegerField(default=40)
    color = models.CharField(max_length=20, default='#3b82f6')
    
    # Break-specific fields
    is_break = models.BooleanField(default=False)
    break_duration_minutes = models.IntegerField(default=60)
    
    class Meta:
        verbose_name = 'Period Type'
        verbose_name_plural = 'Period Types'
    
    def __str__(self):
        return self.name


class TimetablePeriod(models.Model):
    """A time slot in the school day (e.g., Period 1: 8:00-8:40)"""
    
    period_type = models.ForeignKey(PeriodType, on_delete=models.PROTECT)
    order = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    display_name = models.CharField(max_length=50)
    
    # Which days this period applies to
    school_days = models.ManyToManyField(SchoolDay, related_name='periods')
    
    # For breaks, can override duration
    is_flexible = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Timetable Period'
        verbose_name_plural = 'Timetable Periods'
    
    def __str__(self):
        return f"{self.display_name} ({self.start_time} - {self.end_time})"


class Timetable(models.Model):
    """Master timetable for a specific class group and session/term"""
    
    # Academic context
    academic_session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    academic_term = models.ForeignKey(
        AcademicTerm, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    
    # Target class
    student_class = models.ForeignKey(
        StudentClass, 
        on_delete=models.CASCADE, 
        related_name='timetables'
    )
    
    # Timetable metadata
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_current = models.BooleanField(default=False)
    
    # Versioning
    version = models.IntegerField(default=1)
    previous_version = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_timetables'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='approved_timetables'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-academic_session', '-academic_term', 'student_class']
        unique_together = ['academic_session', 'academic_term', 'student_class', 'version']
        verbose_name = 'Timetable'
        verbose_name_plural = 'Timetables'
        permissions = [
            ("publish_timetable", "Can publish and activate timetables"),
            ("view_all_timetables", "Can view all timetables across classes"),
        ]
    
    def __str__(self):
        term = f" - {self.academic_term.get_term_display()}" if self.academic_term else ""
        return f"{self.student_class.display_name}{term} - {self.name} (v{self.version})"
    
    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"{self.student_class.display_name} Timetable"
        super().save(*args, **kwargs)


class TimetableSlot(models.Model):
    """A single cell in the timetable - teacher assigned to class at specific period"""
    
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='slots')
    day = models.ForeignKey(SchoolDay, on_delete=models.PROTECT)
    period = models.ForeignKey(TimetablePeriod, on_delete=models.PROTECT)
    
    # Teacher assignment
    teacher = models.ForeignKey(
        'staffs.Staff', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True
    )
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True
    )
    
    # Free period flag
    is_free_period = models.BooleanField(
        default=False, 
        help_text="Mark as free/study period"
    )
    
    # Optional overrides
    room = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    
    # For temporary changes (e.g., teacher absent)
    is_temporary = models.BooleanField(default=False)
    temporary_teacher = models.ForeignKey(
        'staffs.Staff', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name='temporary_slots'
    )
    temporary_subject = models.ForeignKey(
        Subject, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name='temporary_slots'
    )
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['day__order', 'period__order']
        unique_together = ['timetable', 'day', 'period']
        indexes = [
            models.Index(fields=['timetable', 'teacher']),
            models.Index(fields=['timetable', 'subject']),
        ]
        verbose_name = 'Timetable Slot'
        verbose_name_plural = 'Timetable Slots'
    
    def __str__(self):
        teacher_name = self.teacher.get_full_name if self.teacher else "Unassigned"
        subject_name = self.subject.name if self.subject else "No Subject"
        return f"{self.day.name} {self.period.display_name}: {subject_name} ({teacher_name})"



class TimetableClashLog(models.Model):
    """Log of timetable clashes for audit"""
    
    timetable = models.ForeignKey(
        Timetable, 
        on_delete=models.CASCADE, 
        related_name='clash_logs'
    )
    teacher = models.ForeignKey(Staff, on_delete=models.CASCADE)
    day = models.ForeignKey(SchoolDay, on_delete=models.CASCADE)
    period_1 = models.ForeignKey(
        TimetablePeriod, 
        on_delete=models.CASCADE, 
        related_name='clash_as_period1'
    )
    period_2 = models.ForeignKey(
        TimetablePeriod, 
        on_delete=models.CASCADE, 
        related_name='clash_as_period2'
    )
    slot_1 = models.ForeignKey(
        TimetableSlot, 
        on_delete=models.CASCADE, 
        related_name='clash_as_slot1'
    )
    slot_2 = models.ForeignKey(
        TimetableSlot, 
        on_delete=models.CASCADE, 
        related_name='clash_as_slot2'
    )
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    class Meta:
        verbose_name = 'Timetable Clash Log'
        verbose_name_plural = 'Timetable Clash Logs'
        indexes = [
            models.Index(fields=['timetable', 'resolved_at']),
            models.Index(fields=['teacher', 'detected_at']),
        ]
    
    def __str__(self):
        return f"Clash: {self.teacher.get_full_name} on {self.day.name} at {self.period_1.display_name}"
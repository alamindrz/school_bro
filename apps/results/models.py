"""
Results Models - Student academic scores
One ScoreSheet per subject per class stream per term.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass, Subject

User = get_user_model()


class ScoreSheet(models.Model):
    """
    A score sheet for ONE subject in ONE class stream for ONE term.
    Only the subject teacher or school heads can edit.
    """
    
    # Context
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name='score_sheets'
    )
    student_class = models.ForeignKey(
        StudentClass, on_delete=models.PROTECT, related_name='score_sheets'
    )
    academic_session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name='score_sheets'
    )
    academic_term = models.ForeignKey(
        AcademicTerm, on_delete=models.PROTECT, related_name='score_sheets'
    )
    
    # Status
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    APPROVED = 'approved'
    PUBLISHED = 'published'
    
    STATUS_CHOICES = [
        (DRAFT, _('Draft')),
        (SUBMITTED, _('Submitted')),
        (APPROVED, _('Approved')),
        (PUBLISHED, _('Published')),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    
    # Metadata
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_score_sheets'
    )
    submitted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_score_sheets'
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['subject', 'student_class', 'academic_session', 'academic_term']
        ordering = ['subject__name']
        verbose_name = _('Score Sheet')
        verbose_name_plural = _('Score Sheets')
    
    def __str__(self):
        return f"{self.subject.name} - {self.student_class.display_name} - {self.academic_term.name}"
    
    @property
    def is_editable(self):
        return self.status == self.DRAFT


class ScoreEntry(models.Model):
    """
    A single student's scores for one subject in one term.
    """
    
    score_sheet = models.ForeignKey(
        ScoreSheet, on_delete=models.CASCADE, related_name='entries'
    )
    
    # Student reference (decoupled)
    student_id = models.IntegerField(db_index=True)
    student_name = models.CharField(max_length=200, help_text=_("Denormalized for display"))
    
    # Assessment scores (3 CAs + Exam = 4 default slots)
    ca1 = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("1st Continuous Assessment")
    )
    ca2 = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("2nd Continuous Assessment")
    )
    ca3 = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("3rd Continuous Assessment")
    )
    exam = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("End of Term Examination")
    )
    
    # Calculated fields
    total_score = models.IntegerField(null=True, blank=True)
    grade = models.CharField(max_length=2, null=True, blank=True)
    position = models.IntegerField(null=True, blank=True)
    
    # Metadata
    entered_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['score_sheet', 'student_id']
        ordering = ['student_name']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['score_sheet', 'student_id']),
        ]
        verbose_name = _('Score Entry')
        verbose_name_plural = _('Score Entries')
    
    def __str__(self):
        return f"{self.student_name} - {self.score_sheet.subject.name}"
    
    def calculate_total(self):
        """Calculate weighted total from CA and Exam scores."""
        scores = []
        weights = []
        
        if self.ca1 is not None:
            scores.append(self.ca1)
            weights.append(10)
        if self.ca2 is not None:
            scores.append(self.ca2)
            weights.append(10)
        if self.ca3 is not None:
            scores.append(self.ca3)
            weights.append(10)
        if self.exam is not None:
            scores.append(self.exam)
            weights.append(60)
        
        if not scores:
            self.total_score = None
            return None
        
        total_weight = sum(weights)
        if total_weight == 0:
            self.total_score = None
            return None
        
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        self.total_score = int(weighted_sum / total_weight)
        return self.total_score
    
    def determine_grade(self):
        """Determine grade based on total score."""
        if self.total_score is None:
            return None
        
        if self.total_score >= 75:
            self.grade = 'A1'
        elif self.total_score >= 70:
            self.grade = 'B2'
        elif self.total_score >= 65:
            self.grade = 'B3'
        elif self.total_score >= 60:
            self.grade = 'C4'
        elif self.total_score >= 55:
            self.grade = 'C5'
        elif self.total_score >= 50:
            self.grade = 'C6'
        elif self.total_score >= 45:
            self.grade = 'D7'
        elif self.total_score >= 40:
            self.grade = 'E8'
        else:
            self.grade = 'F9'
        
        return self.grade
    
    def save(self, *args, **kwargs):
        self.calculate_total()
        self.determine_grade()
        super().save(*args, **kwargs)



class CumulativeRecord(models.Model):
    """
    Cumulative academic record across terms/sessions
    """
    
    student_id = models.IntegerField(
        db_index=True,
        help_text=_("Student ID from students app")
    )
    student_name = models.CharField(max_length=200)
    
    # Academic context
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name='cumulative_records'
    )
    
    # Term 1 results
    term1_total = models.IntegerField(null=True, blank=True)
    term1_average = models.FloatField(null=True, blank=True)
    term1_position = models.IntegerField(null=True, blank=True)
    
    # Term 2 results
    term2_total = models.IntegerField(null=True, blank=True)
    term2_average = models.FloatField(null=True, blank=True)
    term2_position = models.IntegerField(null=True, blank=True)
    
    # Term 3 results
    term3_total = models.IntegerField(null=True, blank=True)
    term3_average = models.FloatField(null=True, blank=True)
    term3_position = models.IntegerField(null=True, blank=True)
    
    # Session totals
    session_total = models.IntegerField(null=True, blank=True)
    session_average = models.FloatField(null=True, blank=True)
    session_position = models.IntegerField(null=True, blank=True)
    
    # Promotion status
    promoted_to_next_class = models.BooleanField(default=False)
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student_id', 'academic_session']
        verbose_name = _('Cumulative Record')
        verbose_name_plural = _('Cumulative Records')
    
    def __str__(self):
        return f"{self.student_name} - {self.academic_session.name}"
    
    def calculate_session_average(self):
        """Calculate session average from terms"""
        totals = []
        if self.term1_average:
            totals.append(self.term1_average)
        if self.term2_average:
            totals.append(self.term2_average)
        if self.term3_average:
            totals.append(self.term3_average)
        
        if totals:
            self.session_average = sum(totals) / len(totals)
        return self.session_average
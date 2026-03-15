"""
Results Models - Student academic performance tracking
Depends on: corecode, students (via student_id only), finance (for clearance)
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import uuid

from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass
from .constants import (
    GradeSystem, ResultStatus,
    AssessmentType, RemarkType, DEFAULT_PASS_MARK
)
from apps.corecode.models import Subject
from apps.corecode.constants import SubjectType




User = get_user_model()



class ResultSheet(models.Model):
    """
    Master result sheet for a class/term
    Groups all results for a specific class and term
    """
    
    # Identification
    sheet_number = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique result sheet identifier")
    )
    
    # Context
    student_class = models.ForeignKey(
        StudentClass,
        on_delete=models.PROTECT,
        related_name='result_sheets'
    )
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name='result_sheets'
    )
    academic_term = models.ForeignKey(
        AcademicTerm,
        on_delete=models.PROTECT,
        related_name='result_sheets'
    )
    
    # Subjects in this sheet
    subjects = models.ManyToManyField(
        Subject,
        related_name='result_sheets',
        through='ResultSheetSubject'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=ResultStatus.CHOICES,
        default=ResultStatus.DRAFT
    )
    
    # Approval workflow
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_result_sheets'
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_result_sheets'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    published_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='published_result_sheets'
    )
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_result_sheets'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-academic_session', '-academic_term', 'student_class']
        unique_together = ['student_class', 'academic_session', 'academic_term']
        indexes = [
            models.Index(fields=['sheet_number']),
            models.Index(fields=['status']),
        ]
        verbose_name = _('Result Sheet')
        verbose_name_plural = _('Result Sheets')
    
    def __str__(self):
        return f"{self.student_class.display_name} - {self.academic_term.name}"
    
    def save(self, *args, **kwargs):
        """Generate sheet number if not set"""
        if not self.sheet_number:
            self.sheet_number = self._generate_sheet_number()
        super().save(*args, **kwargs)
    
    def _generate_sheet_number(self):
        """Generate unique sheet number"""
        import uuid
        return f"RS-{uuid.uuid4().hex[:8].upper()}"
    
    def can_edit(self):
        """Check if result sheet can be edited"""
        return self.status in [ResultStatus.DRAFT, ResultStatus.PENDING_APPROVAL]
    
    def can_approve(self):
        """Check if result sheet can be approved"""
        return self.status == ResultStatus.PENDING_APPROVAL
    
    def can_publish(self):
        """Check if result sheet can be published"""
        return self.status == ResultStatus.APPROVED


class ResultSheetSubject(models.Model):
    """
    Through model for subjects in a result sheet
    Stores subject-specific settings
    """
    
    result_sheet = models.ForeignKey(
        ResultSheet,
        on_delete=models.CASCADE,
        related_name='sheet_subjects'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name='sheet_subjects'
    )
    
    # Teacher for this subject
    teacher_id = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("Teacher ID from staffs app")
    )
    teacher_name = models.CharField(max_length=200, blank=True)
    
    # Subject settings
    pass_mark = models.IntegerField(
        default=DEFAULT_PASS_MARK,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    has_practical = models.BooleanField(default=False)
    has_project = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['result_sheet', 'subject']
        ordering = ['subject__name']
    
    def __str__(self):
        return f"{self.result_sheet} - {self.subject.name}"


class Result(models.Model):
    """
    Individual student result for a subject
    """
    
    # Links
    result_sheet = models.ForeignKey(
        ResultSheet,
        on_delete=models.CASCADE,
        related_name='results'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name='results'
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
    
    # Assessment scores
    ca1_score = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Continuous Assessment 1")
    )
    ca2_score = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Continuous Assessment 2")
    )
    ca3_score = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Continuous Assessment 3")
    )
    exam_score = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("End of Term Examination")
    )
    practical_score = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Practical Assessment")
    )
    project_score = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Project Work")
    )
    
    # Calculated fields
    total_score = models.IntegerField(
        null=True, blank=True,
        help_text=_("Weighted total score")
    )
    grade = models.CharField(
        max_length=2,
        choices=GradeSystem.CHOICES,
        null=True, blank=True
    )
    grade_point = models.IntegerField(
        null=True, blank=True,
        help_text=_("Grade point for GPA calculation")
    )
    remark = models.CharField(
        max_length=20,
        choices=RemarkType.CHOICES,
        null=True, blank=True
    )
    custom_remark = models.TextField(blank=True)
    
    # Position in class
    position = models.IntegerField(null=True, blank=True)
    
    # Metadata
    entered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entered_results'
    )
    entered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['student_name']
        unique_together = ['result_sheet', 'subject', 'student_id']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['result_sheet', 'subject']),
            models.Index(fields=['grade']),
        ]
        verbose_name = _('Result')
        verbose_name_plural = _('Results')
    
    def __str__(self):
        return f"{self.student_name} - {self.subject.name} - {self.grade}"
    
    def calculate_total(self):
        """Calculate weighted total score"""
        from .constants import AssessmentType
        
        total = 0
        weights = AssessmentType.WEIGHTS
        
        if self.ca1_score is not None:
            total += self.ca1_score * (weights[AssessmentType.CA1] / 100)
        if self.ca2_score is not None:
            total += self.ca2_score * (weights[AssessmentType.CA2] / 100)
        if self.ca3_score is not None:
            total += self.ca3_score * (weights[AssessmentType.CA3] / 100)
        if self.exam_score is not None:
            total += self.exam_score * (weights[AssessmentType.EXAM] / 100)
        if self.practical_score is not None:
            total += self.practical_score * (weights[AssessmentType.PRACTICAL] / 100)
        if self.project_score is not None:
            total += self.project_score * (weights[AssessmentType.PROJECT] / 100)
        
        self.total_score = round(total)
        return self.total_score
    
    def determine_grade(self):
        """Determine grade based on total score"""
        if self.total_score is None:
            self.calculate_total()
        
        for grade, (min_score, max_score) in GradeSystem.PERCENTAGE_RANGES.items():
            if min_score <= self.total_score <= max_score:
                self.grade = grade
                self.grade_point = GradeSystem.GRADE_POINTS.get(grade, 0)
                break
        
        return self.grade
    
    def determine_remark(self):
        """Determine automated remark"""
        if self.grade:
            self.remark = GradeSystem.REMARKS.get(self.grade)
        return self.remark
    
    def save(self, *args, **kwargs):
        """Auto-calculate totals and grades"""
        self.calculate_total()
        self.determine_grade()
        self.determine_remark()
        super().save(*args, **kwargs)


class ResultComment(models.Model):
    """
    Teacher's comments on student performance
    """
    
    result_sheet = models.ForeignKey(
        ResultSheet,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    student_id = models.IntegerField(
        db_index=True,
        help_text=_("Student ID from students app")
    )
    student_name = models.CharField(max_length=200)
    
    # Comments
    teacher_comment = models.TextField(blank=True)
    principal_comment = models.TextField(blank=True)
    class_teacher_comment = models.TextField(blank=True)
    
    # Next term recommendations
    next_term_recommendation = models.TextField(blank=True)
    
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
        unique_together = ['result_sheet', 'student_id']
        verbose_name = _('Result Comment')
        verbose_name_plural = _('Result Comments')
    
    def __str__(self):
        return f"Comments for {self.student_name}"


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
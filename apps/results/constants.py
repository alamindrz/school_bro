"""
Results App Constants
Pure constants - no dependencies
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class GradeSystem:
    """Standard grading system (Nigerian/WASSCE style)"""
    
    A1 = 'A1'
    B2 = 'B2'
    B3 = 'B3'
    C4 = 'C4'
    C5 = 'C5'
    C6 = 'C6'
    D7 = 'D7'
    E8 = 'E8'
    F9 = 'F9'
    
    CHOICES = [
        (A1, _('A1 - Excellent')),
        (B2, _('B2 - Very Good')),
        (B3, _('B3 - Good')),
        (C4, _('C4 - Credit')),
        (C5, _('C5 - Credit')),
        (C6, _('C6 - Credit')),
        (D7, _('D7 - Pass')),
        (E8, _('E8 - Pass')),
        (F9, _('F9 - Fail')),
    ]
    
    # Grade points for GPA calculation
    GRADE_POINTS = {
        A1: 8,
        B2: 7,
        B3: 6,
        C4: 5,
        C5: 4,
        C6: 3,
        D7: 2,
        E8: 1,
        F9: 0,
    }
    
    # Percentage ranges
    PERCENTAGE_RANGES = {
        A1: (75, 100),
        B2: (70, 74),
        B3: (65, 69),
        C4: (60, 64),
        C5: (55, 59),
        C6: (50, 54),
        D7: (45, 49),
        E8: (40, 44),
        F9: (0, 39),
    }
    
    # Grade remarks
    REMARKS = {
        A1: _('Excellent'),
        B2: _('Very Good'),
        B3: _('Good'),
        C4: _('Credit'),
        C5: _('Credit'),
        C6: _('Credit'),
        D7: _('Pass'),
        E8: _('Pass'),
        F9: _('Fail'),
    }


class ResultStatus:
    """Result publication status"""
    
    DRAFT = 'draft'
    PENDING_APPROVAL = 'pending_approval'
    APPROVED = 'approved'
    PUBLISHED = 'published'
    ARCHIVED = 'archived'
    
    CHOICES = [
        (DRAFT, _('Draft')),
        (PENDING_APPROVAL, _('Pending Approval')),
        (APPROVED, _('Approved')),
        (PUBLISHED, _('Published')),
        (ARCHIVED, _('Archived')),
    ]


class SubjectType:
    """Subject categories"""
    
    CORE = 'core'
    ELECTIVE = 'elective'
    VOCATIONAL = 'vocational'
    
    CHOICES = [
        (CORE, _('Core Subject')),
        (ELECTIVE, _('Elective')),
        (VOCATIONAL, _('Vocational')),
    ]


class AssessmentType:
    """Types of assessments"""
    
    CA1 = 'ca1'  # Continuous Assessment 1
    CA2 = 'ca2'  # Continuous Assessment 2
    CA3 = 'ca3'  # Continuous Assessment 3
    EXAM = 'exam'  # End of Term Exam
    PROJECT = 'project'
    PRACTICAL = 'practical'
    
    CHOICES = [
        (CA1, _('Continuous Assessment 1')),
        (CA2, _('Continuous Assessment 2')),
        (CA3, _('Continuous Assessment 3')),
        (EXAM, _('End of Term Exam')),
        (PROJECT, _('Project')),
        (PRACTICAL, _('Practical')),
    ]
    
    # Weight percentages for final grade calculation
    WEIGHTS = {
        CA1: 10,
        CA2: 10,
        CA3: 10,
        EXAM: 60,
        PROJECT: 5,
        PRACTICAL: 5,
    }


class RemarkType:
    """Teacher's remark types"""
    
    EXCELLENT = 'excellent'
    VERY_GOOD = 'very_good'
    GOOD = 'good'
    FAIR = 'fair'
    POOR = 'poor'
    VERY_POOR = 'very_poor'
    
    CHOICES = [
        (EXCELLENT, _('Excellent')),
        (VERY_GOOD, _('Very Good')),
        (GOOD, _('Good')),
        (FAIR, _('Fair')),
        (POOR, _('Poor')),
        (VERY_POOR, _('Very Poor')),
    ]
    
    # Templates for remarks
    TEMPLATES = {
        EXCELLENT: _("Excellent performance. Keep up the great work!"),
        VERY_GOOD: _("Very good performance. Can do even better."),
        GOOD: _("Good performance. Put in more effort."),
        FAIR: _("Fair performance. Needs improvement."),
        POOR: _("Poor performance. Requires serious attention."),
        VERY_POOR: _("Very poor performance. Urgent intervention needed."),
    }


# Default pass mark from corecode config
DEFAULT_PASS_MARK = 40
DEFAULT_DISTINCTION_MARK = 70

# Subject groups for Nigerian curriculum
NIGERIAN_CORE_SUBJECTS = [
    'English Language',
    'Mathematics',
    'Civic Education',
    'Biology',
    'Chemistry',
    'Physics',
    'Literature in English',
    'Government',
    'Economics',
    'Geography',
]

NIGERIAN_ELECTIVE_SUBJECTS = [
    'Further Mathematics',
    'Accounting',
    'Commerce',
    'History',
    'Islamic Studies',
    'Christian Religious Studies',
    'French',
    'Arabic',
]
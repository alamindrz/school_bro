"""
Results App Validators - Pure validation functions
"""

from django.core.exceptions import ValidationError
from decimal import Decimal
from typing import Optional, List
from datetime import date
from .constants import GradeSystem, AssessmentType, RemarkType
from apps.shared.validators import (
    validate_status_transition as _shared_validate_status_transition,
    validate_csv_headers as _shared_validate_csv_headers,
    validate_batch_size as _shared_validate_batch_size,
)


class ResultValidator:
    """Validate result data"""
    
    @staticmethod
    def validate_score(score: Optional[int], field_name: str = "Score") -> bool:
        """Validate individual score"""
        if score is not None:
            if not isinstance(score, int):
                raise ValidationError(f"{field_name} must be an integer")
            if score < 0 or score > 100:
                raise ValidationError(f"{field_name} must be between 0 and 100")
        return True
    
    @staticmethod
    def validate_scores(ca1=None, ca2=None, ca3=None, exam=None, practical=None, project=None):
        """Validate all scores"""
        ResultValidator.validate_score(ca1, "CA1 Score")
        ResultValidator.validate_score(ca2, "CA2 Score")
        ResultValidator.validate_score(ca3, "CA3 Score")
        ResultValidator.validate_score(exam, "Exam Score")
        ResultValidator.validate_score(practical, "Practical Score")
        ResultValidator.validate_score(project, "Project Score")
        return True
    
    @staticmethod
    def validate_grade(grade: str) -> bool:
        """Validate grade value"""
        valid_grades = [g[0] for g in GradeSystem.CHOICES]
        if grade and grade not in valid_grades:
            raise ValidationError(f"Invalid grade: {grade}")
        return True
    
    @staticmethod
    def validate_remark(remark: str) -> bool:
        """Validate remark type"""
        valid_remarks = [r[0] for r in RemarkType.CHOICES]
        if remark and remark not in valid_remarks:
            raise ValidationError(f"Invalid remark: {remark}")
        return True


class SubjectValidator:
    """Validate subject data"""
    
    @staticmethod
    def validate_subject_name(name: str) -> bool:
        """Validate subject name"""
        if len(name) < 2:
            raise ValidationError("Subject name must be at least 2 characters")
        if len(name) > 100:
            raise ValidationError("Subject name cannot exceed 100 characters")
        return True
    
    @staticmethod
    def validate_subject_code(code: str) -> bool:
        """Validate subject code format"""
        if len(code) < 2 or len(code) > 20:
            raise ValidationError("Subject code must be between 2 and 20 characters")
        
        import re
        if not re.match(r'^[A-Z0-9]+$', code):
            raise ValidationError("Subject code can only contain uppercase letters and numbers")
        
        return True


class ScoreSheetValidator:
    """Validate result sheet data"""
    
    @staticmethod
    def validate_status_transition(current_status: str, new_status: str) -> bool:
        """Validate result sheet status transition"""
        from .constants import ResultStatus

        valid_transitions = {
            ResultStatus.DRAFT: [ResultStatus.PENDING_APPROVAL, ResultStatus.ARCHIVED],
            ResultStatus.PENDING_APPROVAL: [ResultStatus.APPROVED, ResultStatus.DRAFT],
            ResultStatus.APPROVED: [ResultStatus.PUBLISHED, ResultStatus.DRAFT],
            ResultStatus.PUBLISHED: [ResultStatus.ARCHIVED],
            ResultStatus.ARCHIVED: [],
        }
        return _shared_validate_status_transition(
            current_status, new_status, valid_transitions,
        )
    
    @staticmethod
    def validate_term_completion(term_end_date: date, current_date: date) -> bool:
        """Validate if term is complete enough for results"""
        # Results can be entered before term ends, but warning
        if current_date < term_end_date:
            # Not a hard error, just warning
            pass
        return True


class BulkResultValidator:
    """Validate bulk result operations"""
    
    @staticmethod
    def validate_csv_headers(headers: List[str], required_fields: List[str]) -> bool:
        """Validate CSV headers for bulk import (with extra score-column check)."""
        _shared_validate_csv_headers(headers, required_fields)

        score_columns = ['ca1', 'ca2', 'ca3', 'exam', 'practical', 'project']
        if not any(col in headers for col in score_columns):
            raise ValidationError("CSV must contain at least one score column")
        return True
    
    @staticmethod
    def validate_batch_size(batch_size: int, max_batch: int = 500) -> bool:
        return _shared_validate_batch_size(batch_size, max_batch)
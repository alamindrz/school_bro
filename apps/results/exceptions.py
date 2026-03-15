"""
Results App Exceptions
Inherit from corecode exceptions
"""

from apps.corecode.exceptions import CorecodeError


class ResultError(CorecodeError):
    """Base exception for all results errors"""
    default_message = "A result processing error occurred"
    code = 'result_error'


class ResultSheetNotFoundError(ResultError):
    """Result sheet not found"""
    default_message = "Result sheet not found"
    code = 'result_sheet_not_found'


class ResultNotFoundError(ResultError):
    """Individual result not found"""
    default_message = "Result record not found"
    code = 'result_not_found'


class DuplicateResultError(ResultError):
    """Duplicate result for same student/subject/term"""
    default_message = "Result already exists for this student and subject"
    code = 'duplicate_result'


class InvalidGradeError(ResultError):
    """Invalid grade value"""
    default_message = "Invalid grade value"
    code = 'invalid_grade'


class InvalidScoreError(ResultError):
    """Invalid score value"""
    default_message = "Score must be between 0 and 100"
    code = 'invalid_score'


class ResultSheetClosedError(ResultError):
    """Result sheet is closed for editing"""
    default_message = "Result sheet is closed and cannot be modified"
    code = 'result_sheet_closed'


class ResultSheetNotApprovedError(ResultError):
    """Result sheet not approved for publishing"""
    default_message = "Result sheet must be approved before publishing"
    code = 'result_sheet_not_approved'


class StudentNotEligibleError(ResultError):
    """Student not eligible for results"""
    default_message = "Student is not eligible for results"
    code = 'student_not_eligible'


class SubjectNotFoundError(ResultError):
    """Subject not found"""
    default_message = "Subject not found"
    code = 'subject_not_found'


class BulkOperationError(ResultError):
    """Bulk operation failed"""
    default_message = "Bulk operation failed"
    code = 'bulk_operation_error'


class InvalidAssessmentWeightError(ResultError):
    """Invalid assessment weight configuration"""
    default_message = "Assessment weights must sum to 100"
    code = 'invalid_assessment_weight'


class TermNotCompleteError(ResultError):
    """Term not complete for result calculation"""
    default_message = "Term is not complete for result calculation"
    code = 'term_not_complete'


class FinancialClearanceRequiredError(ResultError):
    """Student needs financial clearance"""
    default_message = "Student requires financial clearance to access results"
    code = 'financial_clearance_required'
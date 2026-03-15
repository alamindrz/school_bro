"""
Student App Exceptions - Inherit from Corecode exceptions
ALL student exceptions must inherit from CorecodeError hierarchy
"""

from apps.corecode.exceptions import CorecodeError, ValidationError


class StudentError(CorecodeError):
    """Base exception for all student-related errors"""
    default_message = "A student management error occurred"
    code = 'student_error'


class StudentNotFoundError(StudentError):
    """Student record not found"""
    default_message = "Student record not found"
    code = 'student_not_found'


class DuplicateStudentError(StudentError):
    """Duplicate student record (admission number, email)"""
    default_message = "A student with this admission number already exists"
    code = 'duplicate_student'


class InvalidStatusTransitionError(StudentError):
    """Invalid student status transition"""
    default_message = "Cannot transition student to this status"
    code = 'invalid_status_transition'
    
    def __init__(self, from_status=None, to_status=None, message=None):
        self.from_status = from_status
        self.to_status = to_status
        if from_status and to_status and not message:
            message = f"Cannot transition from '{from_status}' to '{to_status}'"
        super().__init__(message=message, code=self.code)


class StudentNotEligibleError(StudentError):
    """Student not eligible for requested operation"""
    default_message = "Student is not eligible for this operation"
    code = 'not_eligible'
    
    
class NoActiveSessionError(StudentError):
    """No active session found in the db"""
    default_message = "No active session found!"
    code = 'no_active_session'


class AdmissionNumberError(StudentError):
    """Admission number generation/validation errors"""
    default_message = "Admission number error"
    code = 'admission_number_error'


class AdmissionNumberFormatError(AdmissionNumberError):
    """Invalid admission number format"""
    default_message = "Invalid admission number format"
    code = 'invalid_format'


class AdmissionNumberGenerationError(AdmissionNumberError):
    """Failed to generate admission number"""
    default_message = "Could not generate unique admission number"
    code = 'generation_failed'


class AdmissionNumberCollisionError(AdmissionNumberError):
    """Admission number collision detected"""
    default_message = "Admission number already in use"
    code = 'collision'


class GuardianError(StudentError):
    """Guardian-related errors"""
    default_message = "Guardian error"
    code = 'guardian_error'


class GuardianLimitExceededError(GuardianError):
    """Maximum guardians per student exceeded"""
    default_message = "Maximum number of guardians per student exceeded"
    code = 'guardian_limit'


class PrimaryGuardianRequiredError(GuardianError):
    """At least one primary guardian required"""
    default_message = "At least one primary guardian is required"
    code = 'primary_guardian_required'


class StudentUserError(StudentError):
    """Student user account errors"""
    default_message = "Student user account error"
    code = 'user_account_error'


class StudentUserAlreadyExistsError(StudentUserError):
    """User account already exists for student"""
    default_message = "A user account already exists for this student"
    code = 'user_exists'


class ParentPortalAccessError(StudentUserError):
    """Parent portal access errors"""
    default_message = "Parent portal access error"
    code = 'portal_access_error'


class StudentHistoryError(StudentError):
    """Student history/audit errors"""
    default_message = "Student history error"
    code = 'history_error'
    
    
class InvalidClassProgressionError(StudentError):
    """Student history/audit errors"""
    default_message = "Student cannot move to the next class due to an error"
    code = 'progression_error'


class BulkOperationError(StudentError):
    """Bulk operation errors"""
    default_message = "Bulk operation failed"
    code = 'bulk_operation_error'
    
    def __init__(self, message=None, successful=None, failed=None):
        self.successful = successful or []
        self.failed = failed or []
        summary = f"{len(self.successful)} succeeded, {len(self.failed)} failed"
        message = message or f"Bulk operation completed with errors: {summary}"
        super().__init__(message=message, code=self.code)


class StudentValidationError(StudentError, ValidationError):
    """Student data validation error"""
    default_message = "Student data validation failed"
    code = 'validation_error'
    
    def __init__(self, message=None, field_errors=None):
        self.field_errors = field_errors or {}
        super().__init__(message=message or self.default_message, code=self.code)
        


"""
Admissions App Exceptions
Inherit from corecode exceptions
"""

from apps.corecode.exceptions import CorecodeError


class AdmissionsError(CorecodeError):
    """Base exception for all admissions errors"""
    default_message = "An admissions error occurred"
    code = 'admissions_error'


class ApplicationNotFoundError(AdmissionsError):
    """Application not found"""
    default_message = "Application not found"
    code = 'application_not_found'


class InvalidApplicationStatusError(AdmissionsError):
    """Invalid status transition"""
    default_message = "Cannot transition application to this status"
    code = 'invalid_status_transition'
    
    def __init__(self, from_status=None, to_status=None, message=None):
        self.from_status = from_status
        self.to_status = to_status
        if from_status and to_status and not message:
            message = f"Cannot transition from '{from_status}' to '{to_status}'"
        super().__init__(message=message, code=self.code)


class DuplicateApplicationError(AdmissionsError):
    """Duplicate application (same email/phone for active period)"""
    default_message = "An active application already exists for this applicant"
    code = 'duplicate_application'


class PaymentError(AdmissionsError):
    """Payment processing errors"""
    default_message = "Payment processing error"
    code = 'payment_error'


class PaymentVerificationError(PaymentError):
    """Payment verification failed"""
    default_message = "Payment verification failed"
    code = 'payment_verification_failed'


class PaymentIdempotencyError(PaymentError):
    """Duplicate payment detected"""
    default_message = "This payment has already been processed"
    code = 'payment_idempotency_error'


class DocumentError(AdmissionsError):
    """Document upload/validation errors"""
    default_message = "Document error"
    code = 'document_error'


class DocumentTypeError(DocumentError):
    """Invalid document type"""
    default_message = "Invalid document type"
    code = 'invalid_document_type'


class DocumentSizeError(DocumentError):
    """Document size too large"""
    default_message = "Document size exceeds limit"
    code = 'document_size_exceeded'


class EnrollmentError(AdmissionsError):
    """Enrollment processing errors"""
    default_message = "Enrollment error"
    code = 'enrollment_error'


class EnrollmentHandoffError(EnrollmentError):
    """Error during student creation handoff to students app"""
    default_message = "Failed to create student record from application"
    code = 'enrollment_handoff_failed'


class DeadlineExceededError(AdmissionsError):
    """Application deadline has passed"""
    default_message = "Application deadline has passed"
    code = 'deadline_exceeded'


class AdmissionsClosedError(AdmissionsError):
    """Admissions are currently closed"""
    default_message = "Admissions are currently closed"
    code = 'admissions_closed'


class ClassFullError(AdmissionsError):
    """Target class has reached maximum capacity"""
    default_message = "The selected class is full"
    code = 'class_full'
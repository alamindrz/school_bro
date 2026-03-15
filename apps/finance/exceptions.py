"""
Finance App Exceptions
Inherit from corecode exceptions
"""

from apps.corecode.exceptions import CorecodeError


class FinanceError(CorecodeError):
    """Base exception for all finance errors"""
    default_message = "A finance error occurred"
    code = 'finance_error'


class InvoiceNotFoundError(FinanceError):
    """Invoice not found"""
    default_message = "Invoice not found"
    code = 'invoice_not_found'


class DuplicateInvoiceError(FinanceError):
    """Duplicate invoice (same student/session/term/fee_type)"""
    default_message = "An invoice already exists for this student, session, term, and fee type"
    code = 'duplicate_invoice'


class InvalidInvoiceStatusError(FinanceError):
    """Invalid status transition"""
    default_message = "Cannot transition invoice to this status"
    code = 'invalid_invoice_status'


class PaymentError(FinanceError):
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


class InsufficientPaymentError(PaymentError):
    """Payment amount less than required"""
    default_message = "Payment amount is less than the minimum required"
    code = 'insufficient_payment'


class ExcessPaymentError(PaymentError):
    """Payment amount exceeds invoice total"""
    default_message = "Payment amount exceeds invoice total"
    code = 'excess_payment'


class WaiverError(FinanceError):
    """Fee waiver errors"""
    default_message = "Waiver processing error"
    code = 'waiver_error'


class WaiverLimitExceededError(WaiverError):
    """Waiver amount exceeds allowed limit"""
    default_message = "Waiver amount exceeds maximum allowed"
    code = 'waiver_limit_exceeded'


class StudentNotEligibleError(FinanceError):
    """Student not eligible for operation"""
    default_message = "Student is not eligible for this operation"
    code = 'student_not_eligible'


class FeeStructureError(FinanceError):
    """Fee structure configuration error"""
    default_message = "Fee structure error"
    code = 'fee_structure_error'
"""
Shared Exception Base Classes

Provides reusable base classes for the common exception patterns that are
duplicated across every app (students, staffs, finance, admissions,
attendance, results).  App-specific exception modules keep their own
classes but inherit from these instead of re-implementing the same
``__init__`` logic.

Patterns extracted:
  - ``NotFoundError``             — 6 near-identical copies
  - ``DuplicateError``            — 6 copies
  - ``InvalidStatusTransitionError`` — 4 copies (two with from/to args)
  - ``BulkOperationError``        — 3 copies (students, attendance, results)
  - ``PaymentError`` family       — duplicated between finance & admissions
"""

from apps.corecode.exceptions import CorecodeError


# ---------------------------------------------------------------------------
# Reusable "Not Found" base
# ---------------------------------------------------------------------------
class NotFoundError(CorecodeError):
    """Generic *not-found* base.  Subclass once per app/model."""

    default_message = "Record not found"
    code = "not_found"


# ---------------------------------------------------------------------------
# Reusable "Duplicate" base
# ---------------------------------------------------------------------------
class DuplicateError(CorecodeError):
    """Generic *duplicate-record* base."""

    default_message = "A duplicate record already exists"
    code = "duplicate"


# ---------------------------------------------------------------------------
# Reusable status-transition error (with optional from/to info)
# ---------------------------------------------------------------------------
class InvalidStatusTransitionError(CorecodeError):
    """
    Raised when a status transition is not allowed.

    Accepts optional ``from_status`` / ``to_status`` so callers get a
    human-readable message automatically.
    """

    default_message = "Cannot transition to this status"
    code = "invalid_status_transition"

    def __init__(self, from_status=None, to_status=None, message=None, **kwargs):
        self.from_status = from_status
        self.to_status = to_status
        if from_status and to_status and not message:
            message = f"Cannot transition from '{from_status}' to '{to_status}'"
        kwargs.setdefault("code", self.code)
        super().__init__(message=message, **kwargs)


# ---------------------------------------------------------------------------
# Reusable bulk-operation error (with success/failure counts)
# ---------------------------------------------------------------------------
class BulkOperationError(CorecodeError):
    """
    Raised when a bulk operation partially or fully fails.

    Stores lists of ``successful`` and ``failed`` item identifiers so
    callers can report granular results.
    """

    default_message = "Bulk operation failed"
    code = "bulk_operation_error"

    def __init__(self, message=None, successful=None, failed=None, **kwargs):
        self.successful = successful or []
        self.failed = failed or []
        summary = f"{len(self.successful)} succeeded, {len(self.failed)} failed"
        message = message or f"Bulk operation completed with errors: {summary}"
        kwargs.setdefault("code", self.code)
        super().__init__(message=message, **kwargs)


# ---------------------------------------------------------------------------
# Reusable payment-error hierarchy (shared by finance & admissions)
# ---------------------------------------------------------------------------
class PaymentError(CorecodeError):
    """Base payment-processing error."""

    default_message = "Payment processing error"
    code = "payment_error"


class PaymentVerificationError(PaymentError):
    """Payment verification failed."""

    default_message = "Payment verification failed"
    code = "payment_verification_failed"


class PaymentIdempotencyError(PaymentError):
    """Duplicate payment detected."""

    default_message = "This payment has already been processed"
    code = "payment_idempotency_error"


# ---------------------------------------------------------------------------
# Reusable eligibility error
# ---------------------------------------------------------------------------
class NotEligibleError(CorecodeError):
    """Entity is not eligible for the requested operation."""

    default_message = "Not eligible for this operation"
    code = "not_eligible"

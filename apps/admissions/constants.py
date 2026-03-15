"""
Admissions App Constants
Pure constants - no dependencies
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class ApplicationStatus:
    """Application lifecycle status"""
    
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    UNDER_REVIEW = 'under_review'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    WAITLISTED = 'waitlisted'
    ENROLLED = 'enrolled'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'
    
    CHOICES = [
        (DRAFT, _('Draft')),
        (SUBMITTED, _('Submitted')),
        (UNDER_REVIEW, _('Under Review')),
        (APPROVED, _('Approved')),
        (REJECTED, _('Rejected')),
        (WAITLISTED, _('Waitlisted')),
        (ENROLLED, _('Enrolled')),
        (CANCELLED, _('Cancelled')),
        (EXPIRED, _('Expired')),
    ]
    
    # Valid transitions for state machine
    VALID_TRANSITIONS = {
        DRAFT: [SUBMITTED, CANCELLED],
        SUBMITTED: [UNDER_REVIEW, REJECTED, CANCELLED],
        UNDER_REVIEW: [APPROVED, REJECTED, WAITLISTED],
        APPROVED: [ENROLLED, EXPIRED, CANCELLED],
        REJECTED: [],  # Terminal state
        WAITLISTED: [UNDER_REVIEW, APPROVED, CANCELLED],
        ENROLLED: [],  # Terminal state - moved to students
        CANCELLED: [],  # Terminal state
        EXPIRED: [],  # Terminal state
    }
    
    # Terminal states (no further transitions)
    TERMINAL_STATES = [REJECTED, ENROLLED, CANCELLED, EXPIRED]
    
    # Active states (still in process)
    ACTIVE_STATES = [DRAFT, SUBMITTED, UNDER_REVIEW, WAITLISTED]


class ApplicationType:
    """Type of application"""
    
    NEW = 'new'
    TRANSFER = 'transfer'
    RE_ADMISSION = 're_admission'
    
    CHOICES = [
        (NEW, _('New Student')),
        (TRANSFER, _('Transfer from Another School')),
        (RE_ADMISSION, _('Re-admission')),
    ]


class PaymentStatus:
    """Application fee payment status"""
    
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'
    
    CHOICES = [
        (PENDING, _('Pending')),
        (PROCESSING, _('Processing')),
        (COMPLETED, _('Completed')),
        (FAILED, _('Failed')),
        (REFUNDED, _('Refunded')),
    ]


class PaymentMethod:
    """Payment methods supported"""
    
    PAYSTACK = 'paystack'
    BANK_TRANSFER = 'bank_transfer'
    CASH = 'cash'
    POS = 'pos'
    
    CHOICES = [
        (PAYSTACK, _('Paystack Online')),
        (BANK_TRANSFER, _('Bank Transfer')),
        (CASH, _('Cash')),
        (POS, _('POS')),
    ]


class DocumentType:
    """Types of documents that can be uploaded"""
    
    PASSPORT = 'passport'
    BIRTH_CERT = 'birth_certificate'
    TRANSFER_CERT = 'transfer_certificate'
    REPORT_CARD = 'report_card'
    MEDICAL = 'medical_record'
    OTHER = 'other'
    
    CHOICES = [
        (PASSPORT, _('Passport Photograph')),
        (BIRTH_CERT, _('Birth Certificate')),
        (TRANSFER_CERT, _('Transfer Certificate')),
        (REPORT_CARD, _('Previous Report Card')),
        (MEDICAL, _('Medical Record')),
        (OTHER, _('Other Document')),
    ]


# Application fee configuration (can be overridden in SiteConfig)
DEFAULT_APPLICATION_FEE = 5000  # Naira
DEFAULT_ADMISSION_DEADLINE_DAYS = 30  # Days from approval to enrollment
"""
Finance App Constants
Pure constants - no dependencies
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class InvoiceStatus:
    """Invoice lifecycle status"""
    
    DRAFT = 'draft'
    PENDING = 'pending'
    PARTIAL = 'partial'
    PAID = 'paid'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'
    
    CHOICES = [
        (DRAFT, _('Draft')),
        (PENDING, _('Pending')),
        (PARTIAL, _('Partially Paid')),
        (PAID, _('Paid')),
        (OVERDUE, _('Overdue')),
        (CANCELLED, _('Cancelled')),
        (REFUNDED, _('Refunded')),
    ]
    
    # Valid transitions
    VALID_TRANSITIONS = {
        DRAFT: [PENDING, CANCELLED],
        PENDING: [PARTIAL, PAID, OVERDUE, CANCELLED],
        PARTIAL: [PAID, OVERDUE, CANCELLED],
        PAID: [REFUNDED],
        OVERDUE: [PENDING, CANCELLED],
        CANCELLED: [],  # Terminal
        REFUNDED: [],   # Terminal
    }
    
    # Payment required statuses
    REQUIRES_PAYMENT = [PENDING, PARTIAL, OVERDUE]
    
    # Final statuses (no further action)
    FINAL_STATUSES = [PAID, CANCELLED, REFUNDED]


class PaymentStatus:
    """Payment transaction status"""
    
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
    
    CASH = 'cash'
    POS = 'pos'
    PAYSTACK = 'paystack'
    CHEQUE = 'cheque'
    WAIVER = 'waiver'
    BANK_TRANSFER = 'bank_transfer'
    
    CHOICES = [
        (CASH, _('Cash')),
        (POS, _('POS')),
        (BANK_TRANSFER, _('Bank Transfer')),
        (PAYSTACK, _('Paystack Online')),
        (CHEQUE, _('Cheque')),
        (WAIVER, _('Fee Waiver')),
    ]


class FeeType:
    """Types of fees that can be charged"""
    
    TUITION = 'tuition'
    DEVELOPMENT = 'development'
    SPORTS = 'sports'
    LIBRARY = 'library'
    LABORATORY = 'laboratory'
    EXAM = 'exam'
    REGISTRATION = 'registration'
    UNIFORM = 'uniform'
    TRANSPORT = 'transport'
    ICT = 'ict'
    APPLICATION = 'application'  # ADDED for application fees
    OTHER = 'other'
    
    CHOICES = [
        (TUITION, _('Tuition Fee')),
        (DEVELOPMENT, _('Development Levy')),
        (SPORTS, _('Sports Fee')),
        (LIBRARY, _('Library Fee')),
        (LABORATORY, _('Laboratory Fee')),
        (EXAM, _('Examination Fee')),
        (REGISTRATION, _('Registration Fee')),
        (UNIFORM, _('Uniform Fee')),
        (TRANSPORT, _('Transport Fee')),
        (ICT, _('ICT Fee')),
        (APPLICATION, _('Application Fee')),
        (OTHER, _('Other Fee')),
    ]
    
    # Fee categories for grouping
    CATEGORIES = {
        'mandatory': [TUITION, DEVELOPMENT, REGISTRATION, APPLICATION],
        'academic': [LIBRARY, LABORATORY, EXAM, ICT],
        'ancillary': [SPORTS, UNIFORM, TRANSPORT, OTHER],
    }


class FeeTerm:
    """When the fee applies"""
    
    PER_TERM = 'per_term'
    PER_SESSION = 'per_session'
    ONE_TIME = 'one_time'
    
    CHOICES = [
        (PER_TERM, _('Per Term')),
        (PER_SESSION, _('Per Session')),
        (ONE_TIME, _('One Time')),
    ]


class DiscountType:
    """Types of discounts"""
    
    PERCENTAGE = 'percentage'
    FIXED = 'fixed'
    
    CHOICES = [
        (PERCENTAGE, _('Percentage')),
        (FIXED, _('Fixed Amount')),
    ]


# Fee defaults
DEFAULT_DUE_DAYS = 30
LATE_PENALTY_PERCENTAGE = 5  # 5% per term
WAIVER_MAX_PERCENTAGE = 100  # 100% max waiver
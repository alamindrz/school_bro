"""
Finance App Validators - Pure validation functions
"""

from decimal import Decimal
from datetime import date
from django.core.exceptions import ValidationError

from .constants import InvoiceStatus, PaymentMethod, FeeType, DiscountType
from apps.shared.validators import (
    validate_status_transition as _shared_validate_status_transition,
    validate_choice as _shared_validate_choice,
)


class InvoiceValidator:
    """Validate invoice data"""
    
    @staticmethod
    def validate_amount(amount: Decimal) -> bool:
        """Validate invoice amount"""
        if amount <= 0:
            raise ValidationError("Amount must be greater than zero")
        if amount > 1_000_000_000:  # 1 billion cap
            raise ValidationError("Amount exceeds maximum allowed")
        return True
    
    @staticmethod
    def validate_due_date(due_date: date, issue_date: date = None) -> bool:
        """Validate due date"""
        if issue_date and due_date < issue_date:
            raise ValidationError("Due date cannot be before issue date")
        
        # Don't allow due dates more than 1 year in the future
        max_future = date.today().replace(year=date.today().year + 1)
        if due_date > max_future:
            raise ValidationError("Due date cannot be more than 1 year in the future")
        
        return True
    
    @staticmethod
    def validate_discount(discount_type: str, discount_value: Decimal, subtotal: Decimal) -> Decimal:
        """Validate and calculate discount amount"""
        valid_types = [dt[0] for dt in DiscountType.CHOICES]
        if discount_type and discount_type not in valid_types:
            raise ValidationError(f"Invalid discount type: {discount_type}")
        
        if discount_value < 0:
            raise ValidationError("Discount value cannot be negative")
        
        if discount_type == DiscountType.PERCENTAGE:
            if discount_value > 100:
                raise ValidationError("Percentage discount cannot exceed 100%")
            discount_amount = (subtotal * discount_value) / 100
        elif discount_type == DiscountType.FIXED:
            if discount_value > subtotal:
                raise ValidationError("Fixed discount cannot exceed subtotal")
            discount_amount = discount_value
        else:
            discount_amount = Decimal('0')
        
        return discount_amount
    
    @staticmethod
    def validate_status_transition(current_status: str, new_status: str) -> bool:
        """Validate invoice status transition"""
        return _shared_validate_status_transition(
            current_status, new_status, InvoiceStatus.VALID_TRANSITIONS,
        )


class PaymentValidator:
    """Validate payment data"""
    
    @staticmethod
    def validate_amount(amount: Decimal, invoice_total: Decimal, current_paid: Decimal) -> bool:
        """Validate payment amount against invoice"""
        if amount <= 0:
            raise ValidationError("Payment amount must be positive")
        
        remaining = invoice_total - current_paid
        if amount > remaining:
            raise ValidationError(
                f"Payment amount {amount} exceeds remaining balance {remaining}"
            )
        
        return True
    
    @staticmethod
    def validate_payment_method(method: str) -> bool:
        """Validate payment method"""
        return _shared_validate_choice(method, PaymentMethod.CHOICES, "payment method")
    
    @staticmethod
    def validate_transaction_id(transaction_id: str) -> bool:
        """Validate transaction ID format"""
        if len(transaction_id) < 5 or len(transaction_id) > 100:
            raise ValidationError("Transaction ID must be between 5 and 100 characters")
        
        import re
        if not re.match(r'^[a-zA-Z0-9\-_]+$', transaction_id):
            raise ValidationError("Transaction ID can only contain letters, numbers, hyphens, and underscores")
        
        return True


class FeeStructureValidator:
    """Validate fee structure data"""
    
    @staticmethod
    def validate_fee_type(fee_type: str) -> bool:
        """Validate fee type"""
        return _shared_validate_choice(fee_type, FeeType.CHOICES, "fee type")
    
    @staticmethod
    def validate_term(term: str) -> bool:
        """Validate fee term"""
        from .constants import FeeTerm
        valid_terms = [ft[0] for ft in FeeTerm.CHOICES]
        if term not in valid_terms:
            raise ValidationError(f"Invalid fee term: {term}")
        return True
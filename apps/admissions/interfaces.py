"""
Admissions Interfaces - Contracts for other apps
NO model imports. Pure data contracts.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import date


@dataclass
class ApplicantDataContract:
    """
    Data contract for applicant information.
    Used when handing off to students app for enrollment.
    """
    
    # Required fields
    first_name: str
    last_name: str
    date_of_birth: str  # ISO format date
    gender: str
    current_class_id: int  # Target class ID from corecode
    
    # Optional fields
    middle_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state_of_origin: Optional[str] = None
    nationality: Optional[str] = 'Nigerian'
    
    # Guardian info (will be passed to guardian creation)
    guardian_first_name: Optional[str] = None
    guardian_last_name: Optional[str] = None
    guardian_relationship: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_email: Optional[str] = None
    
    # Metadata
    application_id: Optional[int] = None
    application_number: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for service layer"""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class PaymentVerificationContract:
    """
    Contract for payment verification callbacks
    """
    reference: str  # Paystack reference
    amount: float
    status: str
    paid_at: str  # ISO datetime
    metadata: Dict[str, Any] = None


class AdmissionsServiceInterface:
    """
    Interface that other apps must use to interact with admissions.
    """
    
    @staticmethod
    def get_application_by_number(application_number: str) -> Optional[Dict[str, Any]]:
        """Get application data by number. Returns dict, not model."""
        raise NotImplementedError("Use admissions.selectors.ApplicationSelector.get_by_number")
    
    @staticmethod
    def verify_payment(reference: str) -> Dict[str, Any]:
        """Verify a payment with idempotency protection."""
        raise NotImplementedError("Use admissions.services.PaymentService.verify_payment")
    
    @staticmethod
    def is_admissions_open() -> bool:
        """Check if admissions are currently open."""
        raise NotImplementedError("Use admissions.services.ApplicationService.is_admissions_open")


# This is the ONLY public API for the admissions app
__all__ = [
    'ApplicantDataContract',
    'PaymentVerificationContract',
    'AdmissionsServiceInterface',
]
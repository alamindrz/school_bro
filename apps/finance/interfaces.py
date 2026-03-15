"""
Finance App Interfaces - Contracts for other apps
NO model imports. Pure data contracts.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from decimal import Decimal


@dataclass
class InvoiceContract:
    """
    Contract for creating invoices
    Used by other apps (admissions, results)
    """
    student_id: int
    student_name: str
    class_id: int
    fee_type: str
    amount: Decimal
    description: str = ""
    session_id: Optional[int] = None
    term_id: Optional[int] = None
    due_date: Optional[str] = None


@dataclass
class PaymentContract:
    """
    Contract for recording payments
    """
    invoice_id: int
    amount: Decimal
    payment_method: str
    transaction_id: Optional[str] = None
    notes: str = ""


@dataclass
class FinancialStatusContract:
    """
    Contract for financial clearance status
    """
    student_id: int
    session_id: Optional[int] = None
    is_cleared: bool = False
    total_due: Decimal = Decimal('0')
    has_overdue: bool = False


class FinanceServiceInterface:
    """
    Interface that other apps must use to interact with finance app
    """
    
    @staticmethod
    def create_invoice(contract: InvoiceContract) -> Dict[str, Any]:
        """Create an invoice for a student"""
        raise NotImplementedError("Use finance.services.InvoiceService.create_invoice")
    
    @staticmethod
    def record_payment(contract: PaymentContract) -> Dict[str, Any]:
        """Record a payment against an invoice"""
        raise NotImplementedError("Use finance.services.PaymentService.record_cash_payment")
    
    @staticmethod
    def get_student_balance(student_id: int, session_id: Optional[int] = None) -> Dict[str, Any]:
        """Get student's financial balance"""
        raise NotImplementedError("Use finance.selectors.InvoiceSelector.get_student_balance")
    
    @staticmethod
    def is_cleared_for_exams(student_id: int, session_id: Optional[int] = None) -> FinancialStatusContract:
        """Check if student is financially cleared for exams"""
        result = FinancialStatusSelector.is_student_cleared_for_exams(student_id, session_id)
        return FinancialStatusContract(
            student_id=student_id,
            session_id=session_id,
            is_cleared=result['is_cleared'],
            total_due=Decimal(str(result['total_due'])),
            has_overdue=result['has_overdue']
        )
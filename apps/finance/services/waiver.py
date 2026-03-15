"""
Waiver Service - Fee waiver request and approval workflow
"""

from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import logging
from typing import Optional, Dict, Any

from ..models import Invoice, FeeWaiver
from ..constants import WAIVER_MAX_PERCENTAGE
from ..exceptions import (
    WaiverError,
    WaiverLimitExceededError,
    InvoiceNotFoundError,
    InvalidInvoiceStatusError,
)
from ..selectors import InvoiceSelector
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class WaiverService:
    """
    Fee waiver business operations
    Handles waiver requests, approvals, and rejections
    """
    
    @staticmethod
    @transaction.atomic
    def request_waiver(
        invoice_id: int,
        amount: Decimal,
        reason: str,
        requested_by_id: int
    ) -> FeeWaiver:
        """
        Request a fee waiver for an invoice
        """
        try:
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")
        
        # Check if invoice can have waiver
        if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.REFUNDED]:
            raise InvalidInvoiceStatusError(
                f"Cannot request waiver for invoice with status {invoice.status}"
            )
        
        # Validate waiver amount
        if amount <= 0:
            raise WaiverError("Waiver amount must be positive")
        
        if amount > invoice.balance:
            raise WaiverError(f"Waiver amount ₦{amount} exceeds remaining balance ₦{invoice.balance}")
        
        # Check against maximum allowed (configurable)
        max_waiver = invoice.total * (WAIVER_MAX_PERCENTAGE / 100)
        total_waivers = invoice.waiver_amount + amount
        
        if total_waivers > max_waiver:
            raise WaiverLimitExceededError(
                f"Total waivers ₦{total_waivers} exceeds maximum allowed ₦{max_waiver} "
                f"({WAIVER_MAX_PERCENTAGE}% of invoice total)"
            )
        
        # Check for existing pending waiver
        existing_pending = FeeWaiver.objects.filter(
            invoice=invoice,
            status='pending'
        ).exists()
        
        if existing_pending:
            raise WaiverError("There is already a pending waiver request for this invoice")
        
        # Create waiver request
        waiver = FeeWaiver.objects.create(
            invoice=invoice,
            amount=amount,
            reason=reason,
            requested_by_id=requested_by_id
        )
        
        logger.info(f"Waiver requested for invoice {invoice.invoice_number}: ₦{amount}")
        return waiver
    
    @staticmethod
    @transaction.atomic
    def approve_waiver(
        waiver_id: int,
        approved_by_id: int,
        notes: str = ""
    ) -> FeeWaiver:
        """
        Approve a waiver request and apply to invoice
        """
        try:
            waiver = FeeWaiver.objects.select_for_update().get(id=waiver_id)
        except FeeWaiver.DoesNotExist:
            raise WaiverError(f"Waiver {waiver_id} not found")
        
        if waiver.status != 'pending':
            raise WaiverError(f"Waiver is already {waiver.status}")
        
        # Lock the invoice
        invoice = Invoice.objects.select_for_update().get(id=waiver.invoice_id)
        
        # Re-validate amount against current balance
        if waiver.amount > invoice.balance:
            raise WaiverError(
                f"Waiver amount ₦{waiver.amount} exceeds current balance ₦{invoice.balance}"
            )
        
        # Approve and apply
        waiver.approve(approved_by_id, notes)
        
        # Log the action
        SystemLogService.log_waiver(
            user=approved_by_id,
            invoice=invoice,
            amount=waiver.amount,
            reason=waiver.reason,
            approved_by=approved_by_id
        )
        
        logger.info(f"Waiver {waiver.id} approved for invoice {invoice.invoice_number}")
        return waiver
    
    @staticmethod
    @transaction.atomic
    def reject_waiver(
        waiver_id: int,
        rejected_by_id: int,
        reason: str
    ) -> FeeWaiver:
        """
        Reject a waiver request
        """
        try:
            waiver = FeeWaiver.objects.select_for_update().get(id=waiver_id)
        except FeeWaiver.DoesNotExist:
            raise WaiverError(f"Waiver {waiver_id} not found")
        
        if waiver.status != 'pending':
            raise WaiverError(f"Waiver is already {waiver.status}")
        
        waiver.reject(rejected_by_id, reason)
        
        logger.info(f"Waiver {waiver.id} rejected")
        return waiver
    
    @staticmethod
    def get_pending_waivers_count() -> int:
        """Get count of pending waiver requests"""
        return FeeWaiver.objects.filter(status='pending').count()
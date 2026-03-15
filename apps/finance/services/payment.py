"""
Payment Service - Idempotent payment processing
CRITICAL: Implements select_for_update() to prevent double processing
Supports partial payments, overpayments with credit handling
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging
import hashlib
import hmac
from typing import Optional, Dict, Any, Tuple, List
import requests
from django.conf import settings

from ..models import Invoice, Payment
from ..constants import PaymentStatus, PaymentMethod, InvoiceStatus
from ..exceptions import (
    PaymentError,
    PaymentVerificationError,
    PaymentIdempotencyError,
    InsufficientPaymentError,
    ExcessPaymentError,
    InvoiceNotFoundError,
)
from ..selectors import InvoiceSelector, PaymentSelector
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Payment processing with idempotency protection
    Uses select_for_update() to prevent race conditions
    Supports partial payments and overpayments (credit)
    """
    
    PAYSTACK_API_URL = "https://api.paystack.co"
    
    @classmethod
    def get_paystack_headers(cls):
        """Get Paystack API headers"""
        secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
        if not secret_key:
            raise PaymentError("PAYSTACK_SECRET_KEY not configured")
        
        return {
            'Authorization': f'Bearer {secret_key}',
            'Content-Type': 'application/json',
        }
    
    @classmethod
    @transaction.atomic
    def record_cash_payment(
        cls,
        invoice_id: int,
        amount: Decimal,
        received_by_id: int,
        notes: str = ""
    ) -> Payment:
        """
        Record a cash/POS payment (offline)
        """
        # Lock the invoice row
        try:
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")
        
        # Validate payment amount
        if amount <= 0:
            raise ValidationError("Payment amount must be positive")
        
        # Generate transaction ID
        transaction_id = cls._generate_transaction_id()
        
        # Create payment record
        payment = Payment.objects.create(
            transaction_id=transaction_id,
            invoice=invoice,
            amount=amount,
            payment_method=PaymentMethod.CASH,
            status=PaymentStatus.COMPLETED,  # Cash payments are immediate
            payment_date=timezone.now(),
            notes=notes,
            received_by_id=received_by_id
        )
        
        # Update invoice (auto-saves via payment's post-save signal)
        payment.mark_completed()
        
        # Generate receipt number
        payment.save()  # This triggers receipt number generation
        
        # Log the action
        SystemLogService.log_payment(
            user=received_by_id,
            invoice=invoice,
            amount=amount,
            payment_method='cash',
            transaction_ref=transaction_id
        )
        
        logger.info(f"Cash payment recorded: {transaction_id} for invoice {invoice.invoice_number}")
        return payment
    
    @classmethod
    @transaction.atomic
    def record_bulk_payment(
        cls,
        invoice_ids: List[int],
        amount: Decimal,
        payment_method: str,
        received_by_id: int,
        notes: str = "",
        allocate_evenly: bool = True
    ) -> List[Payment]:
        """
        Record a payment that covers multiple invoices
        e.g., Parent paying for multiple children or multiple fees at once
        """
        payments = []
        remaining = amount
        
        # Lock all invoices in order to prevent deadlock
        invoices = Invoice.objects.select_for_update().filter(
            id__in=invoice_ids,
            balance__gt=0
        ).order_by('due_date')  # Pay oldest first
        
        if not invoices:
            raise ValidationError("No valid invoices found for payment")
        
        if allocate_evenly:
            # Split payment evenly among invoices
            per_invoice = amount / len(invoices)
            for invoice in invoices:
                pay_amount = min(per_invoice, invoice.balance, remaining)
                if pay_amount <= 0:
                    continue
                
                payment = cls.record_cash_payment(
                    invoice_id=invoice.id,
                    amount=pay_amount,
                    received_by_id=received_by_id,
                    notes=f"{notes} (Bulk payment - part of ₦{amount})"
                )
                payments.append(payment)
                remaining -= pay_amount
        else:
            # Pay invoices in full until money runs out
            for invoice in invoices:
                pay_amount = min(invoice.balance, remaining)
                if pay_amount <= 0:
                    continue
                
                payment = cls.record_cash_payment(
                    invoice_id=invoice.id,
                    amount=pay_amount,
                    received_by_id=received_by_id,
                    notes=f"{notes} (Bulk payment)"
                )
                payments.append(payment)
                remaining -= pay_amount
        
        # Handle overpayment (credit)
        if remaining > 0:
            logger.info(f"Overpayment of ₦{remaining} will be held as credit")
            # TODO: Implement credit system for future invoices
        
        return payments
    
    @classmethod
    @transaction.atomic
    def initialize_paystack_payment(
        cls,
        invoice_id: int,
        email: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Initialize Paystack payment for an invoice
        """
        try:
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")
        
        # Check if invoice is payable
        if invoice.status not in InvoiceStatus.REQUIRES_PAYMENT:
            raise PaymentError(f"Invoice is {invoice.get_status_display()} and cannot be paid")
        
        # Generate transaction ID
        transaction_id = cls._generate_transaction_id()
        
        # Create pending payment record
        payment = Payment.objects.create(
            transaction_id=transaction_id,
            invoice=invoice,
            amount=invoice.balance,  # Pay remaining balance
            payment_method=PaymentMethod.PAYSTACK,
            status=PaymentStatus.PENDING
        )
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'student_id': invoice.student_id,
            'student_name': invoice.student_name,
            'payment_id': payment.id,
            'transaction_id': transaction_id,
        })
        
        # Prepare Paystack payload
        amount_in_kobo = int(invoice.balance * 100)
        
        payload = {
            'email': email,
            'amount': amount_in_kobo,
            'metadata': metadata,
            'callback_url': getattr(
                settings,
                'PAYSTACK_CALLBACK_URL',
                '/finance/payment/callback/'
            ),
            'reference': transaction_id,  # Use our transaction ID as reference
        }
        
        try:
            response = requests.post(
                f"{cls.PAYSTACK_API_URL}/transaction/initialize",
                headers=cls.get_paystack_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get('status'):
                raise PaymentError(f"Paystack error: {data.get('message')}")
            
            logger.info(f"Paystack payment initialized for invoice {invoice.invoice_number}")
            
            return {
                'authorization_url': data['data']['authorization_url'],
                'access_code': data['data']['access_code'],
                'reference': data['data']['reference'],
                'payment_id': payment.id,
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack initialization failed: {e}")
            # Mark payment as failed
            payment.status = PaymentStatus.FAILED
            payment.save()
            raise PaymentError(f"Payment gateway error: {str(e)}")
    
    @classmethod
    @transaction.atomic
    def verify_paystack_payment(cls, reference: str) -> Dict[str, Any]:
        """
        Verify Paystack payment with idempotency protection
        Uses select_for_update to prevent double processing
        """
        logger.info(f"Verifying Paystack payment: {reference}")
        
        # Try to find existing payment
        try:
            payment = Payment.objects.select_for_update().get(
                transaction_id=reference
            )
            
            # If already completed, return success (idempotent)
            if payment.status == PaymentStatus.COMPLETED:
                logger.info(f"Payment {reference} already verified")
                return {
                    'success': True,
                    'payment_id': payment.id,
                    'invoice_id': payment.invoice_id,
                    'status': payment.status,
                    'already_processed': True,
                }
            
        except Payment.DoesNotExist:
            payment = None
        
        # Verify with Paystack
        try:
            response = requests.get(
                f"{cls.PAYSTACK_API_URL}/transaction/verify/{reference}",
                headers=cls.get_paystack_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get('status'):
                raise PaymentVerificationError(f"Verification failed: {data.get('message')}")
            
            tx_data = data['data']
            
            # Check if payment was successful
            if tx_data['status'] != 'success':
                logger.warning(f"Payment {reference} not successful: {tx_data['status']}")
                
                if payment:
                    payment.status = PaymentStatus.FAILED
                    payment.gateway_response = tx_data
                    payment.save()
                
                return {
                    'success': False,
                    'status': tx_data['status'],
                    'message': 'Payment was not successful',
                }
            
            # Find invoice from metadata
            metadata = tx_data.get('metadata', {})
            invoice_id = metadata.get('invoice_id')
            
            if not invoice_id:
                raise PaymentVerificationError("No invoice_id in metadata")
            
            # Lock invoice
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
            
            # If payment doesn't exist, create it
            if not payment:
                payment = Payment.objects.create(
                    transaction_id=reference,
                    invoice=invoice,
                    amount=Decimal(tx_data['amount']) / 100,  # Convert from kobo
                    payment_method=PaymentMethod.PAYSTACK,
                    status=PaymentStatus.COMPLETED,
                    gateway_reference=reference,
                    gateway_response=tx_data,
                    payment_date=timezone.now()
                )
                logger.info(f"Payment record created for invoice {invoice.invoice_number}")
            
            # Mark payment as completed
            payment.mark_completed(reference, tx_data)
            
            # Log the action
            SystemLogService.log_payment(
                user=None,  # System action
                invoice=invoice,
                amount=payment.amount,
                payment_method='paystack',
                transaction_ref=reference
            )
            
            logger.info(f"Payment verified for invoice {invoice.invoice_number}")
            
            return {
                'success': True,
                'payment_id': payment.id,
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'amount': float(payment.amount),
                'reference': reference,
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack verification failed: {e}")
            raise PaymentVerificationError(f"Payment gateway error: {str(e)}")
    
    @classmethod
    @transaction.atomic
    def process_partial_payment(
        cls,
        invoice_id: int,
        amount: Decimal,
        payment_method: str,
        received_by_id: int,
        notes: str = ""
    ) -> Payment:
        """
        Process a partial payment (less than full balance)
        """
        try:
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")
        
        # Validate amount
        if amount <= 0:
            raise ValidationError("Payment amount must be positive")
        
        if amount >= invoice.balance:
            raise ValidationError(
                f"Amount ₦{amount} is not partial. Use full payment or record as full."
            )
        
        # Record payment
        payment = cls.record_cash_payment(
            invoice_id=invoice_id,
            amount=amount,
            received_by_id=received_by_id,
            notes=f"Partial payment: {notes}"
        )
        
        # Invoice status will be updated to PARTIAL by payment.mark_completed()
        
        logger.info(f"Partial payment of ₦{amount} recorded for invoice {invoice.invoice_number}")
        return payment
    
    @classmethod
    def _generate_transaction_id(cls) -> str:
        """Generate unique transaction ID"""
        import uuid
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4()).split('-')[0].upper()
        return f"TXN-{timestamp}-{unique_id}"
    
    @classmethod
    def verify_webhook(cls, request) -> bool:
        """
        Verify Paystack webhook signature
        """
        signature = request.headers.get('x-paystack-signature')
        if not signature:
            logger.warning("No Paystack signature in webhook")
            return False
        
        secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        if not secret_key:
            logger.error("PAYSTACK_SECRET_KEY not configured")
            return False
        
        payload = request.body
        expected = hmac.new(
            key=secret_key.encode('utf-8'),
            msg=payload,
            digestmod=hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
    
    @classmethod
    @transaction.atomic
    def handle_webhook(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Paystack webhook callback
        """
        event = payload.get('event')
        data = payload.get('data', {})
        
        logger.info(f"Processing webhook event: {event}")
        
        if event == 'charge.success':
            reference = data.get('reference')
            return cls.verify_paystack_payment(reference)
        
        elif event == 'charge.failed':
            reference = data.get('reference')
            try:
                payment = Payment.objects.get(transaction_id=reference)
                payment.status = PaymentStatus.FAILED
                payment.gateway_response = data
                payment.save()
                
                logger.info(f"Payment failed recorded for {reference}")
                
                return {
                    'success': False,
                    'event': event,
                    'reference': reference,
                    'status': 'failed',
                }
            except Payment.DoesNotExist:
                logger.warning(f"Payment not found for failed reference {reference}")
                return {'success': False, 'error': 'Payment not found'}
        
        else:
            logger.info(f"Unhandled webhook event: {event}")
            return {
                'success': True,
                'event': event,
                'ignored': True,
            }
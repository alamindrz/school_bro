"""
Payment Service - Idempotent payment processing with Paystack
CRITICAL: Implements select_for_update() to prevent double processing
"""

import hashlib
import hmac
import json
import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from django.db import transaction, models
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError

import requests

from ..models import Application, ApplicationPayment
from ..constants import PaymentStatus, PaymentMethod, DEFAULT_APPLICATION_FEE
from ..exceptions import (
    PaymentError,
    PaymentVerificationError,
    PaymentIdempotencyError,
    ApplicationNotFoundError,
)
from ..selectors import ApplicationSelector
from apps.corecode.services import SystemLogService, SiteConfigService
from apps.corecode.models import SystemLog
from apps.corecode.constants import SiteConfigKey

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Payment processing with idempotency protection
    Uses select_for_update() to prevent race conditions
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
    def create_payment_record(cls, application: Application) -> ApplicationPayment:
        """
        Create a payment record for an approved application
        Uses select_for_update to prevent duplicate records
        """
        # Lock the application row to prevent race conditions
        locked_app = Application.objects.select_for_update().get(id=application.id)
        
        # Check if payment already exists
        try:
            payment = ApplicationPayment.objects.get(application=application)
            logger.info(f"Payment record already exists for {application.application_number}")
            return payment
        except ApplicationPayment.DoesNotExist:
            pass
        
        # Get application fee from config
        fee = SiteConfigService.get_config(
            SiteConfigKey.APPLICATION_FEE,
            DEFAULT_APPLICATION_FEE
        )
        
        # Create payment record
        payment = ApplicationPayment.objects.create(
            application=application,
            amount=fee,
            payment_method=PaymentMethod.PAYSTACK,
            status=PaymentStatus.PENDING
        )
        
        logger.info(f"Payment record created for {application.application_number}: {fee}")
        return payment
    
    @classmethod
    def initialize_paystack_payment(
        cls,
        application_id: int,
        email: str,
        amount: Optional[Decimal] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Initialize Paystack payment transaction
        """
        try:
            application = Application.objects.get(id=application_id)
        except Application.DoesNotExist:
            raise ApplicationNotFoundError(f"Application {application_id} not found")
        
        # Get or create payment record
        try:
            payment = ApplicationPayment.objects.get(application=application)
        except ApplicationPayment.DoesNotExist:
            payment = cls.create_payment_record(application)
        
        # Use provided amount or payment amount
        amount_to_charge = amount or payment.amount
        amount_in_kobo = int(amount_to_charge * 100)  # Paystack uses kobo
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'application_id': application.id,
            'application_number': application.application_number,
            'applicant_name': application.full_name,
        })
        
        # Prepare request payload
        payload = {
            'email': email,
            'amount': amount_in_kobo,
            'metadata': metadata,
            'callback_url': getattr(
                settings,
                'PAYSTACK_CALLBACK_URL',
                '/admissions/payment/callback/'
            )
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
            
            # Store access code
            payment.paystack_access_code = data['data']['access_code']
            payment.save(update_fields=['paystack_access_code', 'updated_at'])
            
            logger.info(f"Paystack payment initialized for {application.application_number}")
            
            return {
                'authorization_url': data['data']['authorization_url'],
                'access_code': data['data']['access_code'],
                'reference': data['data']['reference'],
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack initialization failed: {e}")
            raise PaymentError(f"Payment gateway error: {str(e)}")
    
    @classmethod
    @transaction.atomic
    def verify_payment(cls, reference: str) -> Dict[str, Any]:
        """
        Verify Paystack payment with idempotency protection
        Uses select_for_update to prevent double processing
        """
        logger.info(f"Verifying payment with reference: {reference}")
        
        # Try to find existing payment first
        try:
            payment = ApplicationPayment.objects.select_for_update().get(
                paystack_reference=reference
            )
            
            # If already completed, return success (idempotent)
            if payment.status == PaymentStatus.COMPLETED:
                logger.info(f"Payment {reference} already verified")
                return {
                    'success': True,
                    'payment_id': payment.id,
                    'application_id': payment.application_id,
                    'status': payment.status,
                    'already_processed': True,
                }
            
        except ApplicationPayment.DoesNotExist:
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
                
                # Update existing payment if found
                if payment:
                    payment.status = PaymentStatus.FAILED
                    payment.paystack_response = tx_data
                    payment.save(update_fields=['status', 'paystack_response', 'updated_at'])
                
                return {
                    'success': False,
                    'status': tx_data['status'],
                    'message': 'Payment was not successful',
                }
            
            # Find or create payment record
            application_id = tx_data['metadata'].get('application_id')
            if not application_id:
                raise PaymentVerificationError("No application_id in metadata")
            
            # Lock application for update
            application = Application.objects.select_for_update().get(id=application_id)
            
            # If payment doesn't exist, create it
            if not payment:
                payment, created = ApplicationPayment.objects.get_or_create(
                    application=application,
                    defaults={
                        'amount': Decimal(tx_data['amount']) / 100,  # Convert from kobo
                        'payment_method': PaymentMethod.PAYSTACK,
                        'status': PaymentStatus.COMPLETED,
                        'paystack_reference': reference,
                        'paystack_response': tx_data,
                        'transaction_date': timezone.now(),
                        'verified_at': timezone.now(),
                    }
                )
                
                if created:
                    logger.info(f"Payment record created for {application.application_number}")
            
            # Mark payment as completed
            payment.mark_completed(reference, tx_data)
            
            # Log the action
            SystemLogService.log_payment(
                user=None,  # System action
                invoice=None,
                amount=payment.amount,
                payment_method='paystack',
                transaction_ref=reference
            )
            
            logger.info(f"Payment verified successfully for {application.application_number}")
            
            return {
                'success': True,
                'payment_id': payment.id,
                'application_id': application.id,
                'application_number': application.application_number,
                'amount': float(payment.amount),
                'reference': reference,
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack verification failed: {e}")
            raise PaymentVerificationError(f"Payment gateway error: {str(e)}")
  
    @classmethod
    def verify_webhook(cls, request) -> bool:
        """
        Verify Paystack webhook signature
        Public method for webhook verification
        """
        signature = request.headers.get('x-paystack-signature')
        if not signature:
            logger.warning("No Paystack signature in webhook")
            return False
        
        # Compute expected signature
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
    def handle_webhook(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Paystack webhook callback
        Comprehensive handler for all webhook events
        """
        event = payload.get('event')
        data = payload.get('data', {})
      
        logger.info(f"Processing webhook event: {event}")
      
      # Charge success - payment completed
        if event == 'charge.success':
            reference = data.get('reference')
            return cls.verify_payment(reference)
        
        # Charge failed - payment failed
        elif event == 'charge.failed':
            reference = data.get('reference')
            try:
                payment = ApplicationPayment.objects.get(paystack_reference=reference)
                payment.status = PaymentStatus.FAILED
                payment.paystack_response = data
                payment.save(update_fields=['status', 'paystack_response', 'updated_at'])
                
                logger.info(f"Payment failed recorded for {reference}")
                
                return {
                    'success': False,
                    'event': event,
                    'reference': reference,
                    'status': 'failed',
                }
            except ApplicationPayment.DoesNotExist:
                logger.warning(f"Payment not found for failed reference {reference}")
                return {'success': False, 'error': 'Payment not found'}
        
        # Transfer success - refund completed
        elif event == 'transfer.success':
            reference = data.get('reference')
            logger.info(f"Transfer successful: {reference}")
            return {
                'success': True,
                'event': event,
                'reference': reference,
            }
        
        # Transfer failed - refund failed
        elif event == 'transfer.failed':
            reference = data.get('reference')
            logger.warning(f"Transfer failed: {reference}")
            return {
                'success': False,
                'event': event,
                'reference': reference,
            }
        
        # Other events we don't need to process
        else:
            logger.info(f"Unhandled webhook event: {event}")
            return {
                'success': True,
                'event': event,
                'ignored': True,
            }
        

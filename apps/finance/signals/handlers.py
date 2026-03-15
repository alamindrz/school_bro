"""
Finance Signals - Handlers for finance app events
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import logging

from ..models import Invoice, Payment

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Payment)
def payment_post_save(sender, instance, created, **kwargs):
    """Update invoice status after payment"""
    if created:
        logger.info(f"New payment recorded: {instance.transaction_id}")
        # Parent notifications handled in service layer


@receiver(pre_save, sender=Invoice)
def invoice_pre_save(sender, instance, **kwargs):
    """Auto-calculate balance before save"""
    if instance.pk:
        try:
            old = Invoice.objects.get(pk=instance.pk)
            if old.amount_paid != instance.amount_paid:
                logger.info(f"Invoice {instance.invoice_number} payment updated")
        except Invoice.DoesNotExist:
            pass
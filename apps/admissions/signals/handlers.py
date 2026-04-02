"""
Admissions Signals - Handlers for admissions app events
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from ..models import Application
from ..services import ApplicationService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Application)
def application_post_save(sender, instance, created, **kwargs):
    """Handle post-save actions for applications"""
    if created:
        logger.info(f"New application created: {instance.application_number}")
        # Could send welcome email here


@receiver(pre_save, sender=Application)
def application_pre_save(sender, instance, **kwargs):
    """Track status changes for audit"""
    if not instance.pk:
        return
    
    try:
        old = Application.objects.get(pk=instance.pk)
        if old.status != instance.status:
            logger.info(f"Application {instance.application_number} status changed: {old.status} -> {instance.status}")
            # Could trigger notifications here
    except Application.DoesNotExist:
        pass


# REMOVED: payment_post_save signal for ApplicationPayment
# Payment handling is now delegated to the finance app.
# When payment is completed in finance, the webhook will trigger
# ApplicationService.submit_application() via the callback.
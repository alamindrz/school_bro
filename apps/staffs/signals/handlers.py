"""
Staffs Signals - Handlers for staffs app events
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import logging

from ..models import Staff, LeaveRequest

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Staff)
def staff_post_save(sender, instance, created, **kwargs):
    """Handle new staff creation"""
    if created:
        logger.info(f"New staff member created: {instance.staff_id}")


@receiver(post_save, sender=LeaveRequest)
def leave_request_post_save(sender, instance, created, **kwargs):
    """Handle leave request status changes"""
    if created:
        logger.info(f"Leave request created for staff {instance.staff_id}")
    else:
        try:
            old = LeaveRequest.objects.get(pk=instance.pk)
            if old.status != instance.status:
                logger.info(f"Leave request {instance.id} status changed: {old.status} -> {instance.status}")
        except LeaveRequest.DoesNotExist:
            logger.warning(f"LeaveRequest pk={instance.pk} not found during post_save signal")
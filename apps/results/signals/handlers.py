"""
Results Signals - Handlers for results app events
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import logging

from ..models import Result, ResultSheet
from ..services import ResultService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Result)
def result_post_save(sender, instance, created, **kwargs):
    """Handle result creation/update"""
    if created:
        logger.info(f"Result entered for student {instance.student_id}, subject {instance.subject_id}")


@receiver(post_save, sender=ResultSheet)
def result_sheet_post_save(sender, instance, created, **kwargs):
    """Handle result sheet status changes"""
    if not created:
        try:
            old = ResultSheet.objects.get(pk=instance.pk)
            if old.status != instance.status and instance.status == 'published':
                logger.info(f"Result sheet {instance.sheet_number} published")
                # Notify parents
                ResultService._notify_parents(instance)
        except ResultSheet.DoesNotExist:
            pass
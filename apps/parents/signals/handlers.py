"""
Parents Signals - Handlers for parents app events
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

from ..models import ParentProfile, ChildLink, Notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ParentProfile)
def parent_profile_post_save(sender, instance, created, **kwargs):
    """Handle new parent profile creation"""
    if created:
        logger.info(f"New parent profile created: {instance.email}")


@receiver(post_save, sender=ChildLink)
def child_link_post_save(sender, instance, created, **kwargs):
    """Handle new child link"""
    if created:
        logger.info(f"Child {instance.student_id} linked to parent {instance.parent_id}")


@receiver(post_save, sender=Notification)
def notification_post_save(sender, instance, created, **kwargs):
    """Handle notification creation"""
    if created:
        logger.info(f"Notification sent to parent {instance.parent_id}: {instance.title}")
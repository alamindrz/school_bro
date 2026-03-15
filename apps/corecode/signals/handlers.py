"""
Corecode signals - strictly internal to corecode only.
No cross-app signals allowed per manifesto.
"""

from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import SystemLog, AcademicSession, AcademicTerm, StudentClass, SiteConfig
from ..services import SystemLogService

User = get_user_model()


@receiver(pre_save, sender=AcademicSession)
def track_session_changes(sender, instance, **kwargs):
    """Track changes to academic sessions"""
    if not instance.pk:
        return  # New instance, no changes to track yet
    
    try:
        old = sender.objects.get(pk=instance.pk)
        changes = {}
        
        for field in ['name', 'code', 'start_date', 'end_date', 'is_current']:
            old_value = getattr(old, field)
            new_value = getattr(instance, field)
            if old_value != new_value:
                changes[field] = {'old': str(old_value), 'new': str(new_value)}
        
        if changes:
            # Async log - will be implemented with Celery
            # For now, we'll create sync logs
            SystemLog.objects.create(
                user=None,  # Will be set in view layer
                username='system',
                action=SystemLog.ActionType.UPDATE,
                app_label=SystemLog.AppLabel.CORE,
                model_name='AcademicSession',
                object_id=str(instance.pk),
                object_repr=str(instance),
                changes=changes,
                timestamp=timezone.now()
            )
    except sender.DoesNotExist:
        pass
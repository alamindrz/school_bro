"""
Attendance Signals - Handlers for attendance app events
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import logging

from ..models import AttendanceRecord, AttendanceSummary
from ..services import AttendanceService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AttendanceRecord)
def attendance_record_post_save(sender, instance, created, **kwargs):
    """Update register counts and check for alerts"""
    if created:
        logger.info(f"Attendance marked for student {instance.student_id}")
    
    # Update register counts
    instance.register.update_counts()
    
    # Check for attendance alerts
    AttendanceService._check_attendance_alert(instance.student_id)


@receiver(pre_save, sender=AttendanceRecord)
def attendance_record_pre_save(sender, instance, **kwargs):
    """Track changes for audit"""
    if not instance.pk:
        return
    
    try:
        old = AttendanceRecord.objects.get(pk=instance.pk)
        if old.status != instance.status:
            logger.info(f"Attendance status changed for student {instance.student_id}: {old.status} -> {instance.status}")
    except AttendanceRecord.DoesNotExist:
        pass
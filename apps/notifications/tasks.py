"""
Celery tasks for notifications
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from .models import Notification, NotificationTemplate
from .services import NotificationService

logger = logging.getLogger(__name__)


@shared_task
def send_scheduled_notification(notification_id):
    """Send a scheduled notification"""
    try:
        notification = Notification.objects.get(id=notification_id, status='pending')
        # Re-send through all channels
        for channel in notification.channels:
            NotificationService._send_via_channel(notification, channel)
        notification.mark_as_sent()
        logger.info(f"Scheduled notification {notification_id} sent")
    except Notification.DoesNotExist:
        logger.error(f"Scheduled notification {notification_id} not found")


@shared_task
def process_pending_notifications():
    """Process any pending notifications"""
    pending = Notification.objects.filter(status='pending')
    count = 0
    for notification in pending:
        try:
            for channel in notification.channels:
                NotificationService._send_via_channel(notification, channel)
            notification.mark_as_sent()
            count += 1
        except Exception as e:
            logger.error(f"Failed to process notification {notification.id}: {e}")
            notification.mark_as_failed(e)
    
    logger.info(f"Processed {count} pending notifications")
    return count


@shared_task
def send_birthday_wishes():
    """Send birthday wishes to students/staff"""
    from datetime import date
    today = date.today()
    
    # Students
    from apps.students.models import Student
    students = Student.objects.filter(
        date_of_birth__month=today.month,
        date_of_birth__day=today.day,
        status='active'
    )
    
    for student in students:
        NotificationService.send_notification(
            notification_type='general_announcement',
            title="Happy Birthday! 🎂",
            message=f"Wishing you a wonderful birthday, {student.get_full_name}!",
            recipient_type='student',
            recipient_id=student.id,
            priority='normal'
        )
    
    # Staff
    from apps.staffs.models import Staff
    staff = Staff.objects.filter(
        date_of_birth__month=today.month,
        date_of_birth__day=today.day,
        employment_status='active'
    )
    
    for member in staff:
        NotificationService.send_notification(
            notification_type='general_announcement',
            title="Happy Birthday! 🎂",
            message=f"Wishing you a wonderful birthday, {member.get_full_name}!",
            recipient_type='staff',
            recipient_id=member.id,
            priority='normal'
        )
    
    logger.info(f"Sent birthday wishes to {students.count()} students and {staff.count()} staff")


@shared_task
def cleanup_old_notifications(days=30):
    """Archive old notifications"""
    cutoff = timezone.now() - timedelta(days=days)
    old = Notification.objects.filter(created_at__lt=cutoff, status='read')
    count = old.count()
    old.delete()
    logger.info(f"Cleaned up {count} old notifications")
    return count
"""
Notification Service - Parent portal notifications
"""

import logging
from django.utils import timezone
from typing import Optional

from ..models import Notification
from ..constants import NotificationType, NotificationChannel, NotificationPriority

logger = logging.getLogger(__name__)


class NotificationService:
    """Handle parent notifications"""
    
    @staticmethod
    def send_application_status_notification(
        parent,
        student,
        status: str,
        application_number: str
    ) -> Optional[Notification]:
        """
        Send notification about application status change.
        
        Status can be: submitted, under_review, approved, rejected, enrolled
        """
        
        status_messages = {
            'submitted': {
                'title': 'Application Submitted',
                'message': f'Your application for {student.get_full_name} has been submitted successfully. Application #: {application_number}',
                'priority': NotificationPriority.NORMAL,
            },
            'under_review': {
                'title': 'Application Under Review',
                'message': f'Your application for {student.get_full_name} (Ref: {application_number}) is now being reviewed by our admissions team.',
                'priority': NotificationPriority.NORMAL,
            },
            'approved': {
                'title': 'Application Approved! 🎉',
                'message': f'Congratulations! The application for {student.get_full_name} has been approved. Please complete the enrollment process.',
                'priority': NotificationPriority.HIGH,
            },
            'rejected': {
                'title': 'Application Update',
                'message': f'We regret to inform you that the application for {student.get_full_name} (Ref: {application_number}) could not be approved at this time.',
                'priority': NotificationPriority.HIGH,
            },
            'enrolled': {
                'title': 'Welcome to the School! 🎓',
                'message': f'Congratulations! {student.get_full_name} has been successfully enrolled. Admission Number: {student.admission_number}',
                'priority': NotificationPriority.HIGH,
            },
        }
        
        msg = status_messages.get(status, status_messages['submitted'])
        
        notification = Notification.objects.create(
            parent=parent,
            notification_type=NotificationType.GENERAL_ANNOUNCEMENT,
            channel=NotificationChannel.IN_APP,
            priority=msg['priority'],
            title=msg['title'],
            message=msg['message'],
            data={
                'application_number': application_number,
                'student_id': student.id,
                'student_name': student.get_full_name,
                'status': status,
            },
            link_url=f'/parents/children/{student.id}/',
            link_text='View Details',
            related_student_ids=[student.id],
            is_sent=True,
            sent_at=timezone.now()
        )
        
        logger.info(f"Sent {status} notification to parent {parent.id} for student {student.id}")
        
        # TODO: Also send email/SMS based on parent preferences
        # if 'email' in parent.notification_preferences.get(notification_type, []):
        #     send_email(...)
        
        return notification
    
    @staticmethod
    def mark_as_read(notification_id: int, parent_id: int) -> bool:
        """Mark a notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id, parent_id=parent_id)
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    @staticmethod
    def mark_all_as_read(parent_id: int) -> int:
        """Mark all notifications as read for a parent"""
        count = Notification.objects.filter(
            parent_id=parent_id,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return count
"""
Notification Service - Parent notifications
Handles sending notifications via multiple channels
"""

from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from typing import Optional, Dict, Any, List
import logging
import requests

from ..models import ParentProfile, Notification
from ..constants import (
    NotificationType, NotificationChannel, NotificationPriority,
    DEFAULT_NOTIFICATION_PREFERENCES
)
from ..exceptions import (
    NotificationError,
    NotificationSendError,
    InvalidNotificationTypeError,
    InvalidNotificationChannelError,
)
from ..selectors import ParentProfileSelector

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Parent notification business operations
    Handles multi-channel notifications (email, SMS, push, in-app)
    """
    
    @classmethod
    @transaction.atomic
    def send_notification(
        cls,
        parent_id: int,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict] = None,
        priority: str = NotificationPriority.NORMAL,
        link_url: str = "",
        link_text: str = "",
        related_student_ids: List[int] = None,
        force_channels: List[str] = None
    ) -> List[Notification]:
        """
        Send a notification to a parent via preferred channels
        """
        try:
            parent = ParentProfile.objects.get(id=parent_id)
        except ParentProfile.DoesNotExist:
            raise NotificationError(f"Parent {parent_id} not found")
        
        # Determine which channels to use
        channels = force_channels or cls._get_preferred_channels(
            parent, notification_type
        )
        
        notifications = []
        
        for channel in channels:
            try:
                # Create notification record
                notification = Notification.objects.create(
                    parent=parent,
                    notification_type=notification_type,
                    channel=channel,
                    priority=priority,
                    title=title,
                    message=message,
                    data=data or {},
                    link_url=link_url,
                    link_text=link_text,
                    related_student_ids=related_student_ids or [],
                )
                
                # Send via appropriate channel
                success = cls._send_via_channel(notification, channel)
                
                if success:
                    notification.is_sent = True
                    notification.sent_at = timezone.now()
                    notification.save(update_fields=['is_sent', 'sent_at'])
                    notifications.append(notification)
                else:
                    logger.error(f"Failed to send {channel} notification to parent {parent_id}")
                    
            except Exception as e:
                logger.error(f"Error sending {channel} notification: {e}")
        
        return notifications
    
    @classmethod
    def _get_preferred_channels(
        cls,
        parent: ParentProfile,
        notification_type: str
    ) -> List[str]:
        """Get preferred channels for this notification type"""
        preferences = parent.notification_preferences or DEFAULT_NOTIFICATION_PREFERENCES
        return preferences.get(notification_type, [NotificationChannel.IN_APP])
    
    @classmethod
    def _send_via_channel(cls, notification: Notification, channel: str) -> bool:
        """Send notification via specific channel"""
        
        if channel == NotificationChannel.EMAIL:
            return cls._send_email(notification)
        
        elif channel == NotificationChannel.SMS:
            return cls._send_sms(notification)
        
        elif channel == NotificationChannel.PUSH:
            return cls._send_push(notification)
        
        elif channel == NotificationChannel.IN_APP:
            # In-app notifications are just stored, no external send needed
            return True
        
        else:
            raise InvalidNotificationChannelError(f"Unknown channel: {channel}")
    
    @classmethod
    def _send_email(cls, notification: Notification) -> bool:
        """Send email notification"""
        try:
            subject = notification.title
            message = f"""
            {notification.message}
            
            {notification.link_text}: {notification.link_url}
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.parent.email],
                fail_silently=False,
            )
            
            logger.info(f"Email sent to {notification.parent.email}")
            return True
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False
    
    @classmethod
    def _send_sms(cls, notification: Notification) -> bool:
        """Send SMS notification via configured provider"""
        # This is a placeholder - implement with your SMS provider
        # e.g., Twilio, Africa's Talking, etc.
        try:
            # Example with Africa's Talking
            if hasattr(settings, 'SMS_PROVIDER') and settings.SMS_PROVIDER == 'africastalking':
                import africastalking
                africastalking.initialize(
                    username=settings.AT_USERNAME,
                    api_key=settings.AT_API_KEY
                )
                sms = africastalking.SMS
                response = sms.send(
                    message=notification.message[:160],  # SMS length limit
                    recipients=[notification.parent.phone]
                )
                return response.get('SMSMessageData', {}).get('Recipients') is not None
            
            logger.info(f"SMS would be sent to {notification.parent.phone}")
            return True
            
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return False
    
    @classmethod
    def _send_push(cls, notification: Notification) -> bool:
        """Send push notification via Firebase or similar"""
        # This is a placeholder - implement with Firebase Cloud Messaging
        try:
            # Example with FCM
            if hasattr(notification.parent.user, 'fcm_token'):
                # Send push notification
                pass
            
            logger.info(f"Push notification would be sent to {notification.parent.id}")
            return True
            
        except Exception as e:
            logger.error(f"Push notification failed: {e}")
            return False
    
    @classmethod
    def send_payment_receipt(
        cls,
        parent_id: int,
        student_id: int,
        amount: float,
        receipt_number: str,
        payment_date: str
    ) -> List[Notification]:
        """Send payment receipt notification"""
        title = "Payment Receipt"
        message = f"Payment of ₦{amount} has been received. Receipt: {receipt_number}"
        data = {
            'amount': amount,
            'receipt_number': receipt_number,
            'payment_date': payment_date,
            'student_id': student_id,
        }
        link_url = f"/finance/receipt/{receipt_number}/"
        link_text = "View Receipt"
        
        return cls.send_notification(
            parent_id=parent_id,
            notification_type=NotificationType.PAYMENT_RECEIPT,
            title=title,
            message=message,
            data=data,
            link_url=link_url,
            link_text=link_text,
            related_student_ids=[student_id]
        )
    
    @classmethod
    def send_payment_reminder(
        cls,
        parent_id: int,
        student_id: int,
        amount: float,
        due_date: str,
        invoice_number: str
    ) -> List[Notification]:
        """Send payment reminder notification"""
        title = "Payment Reminder"
        message = f"Payment of ₦{amount} is due on {due_date}. Please make arrangements to avoid late fees."
        data = {
            'amount': amount,
            'due_date': due_date,
            'invoice_number': invoice_number,
            'student_id': student_id,
        }
        link_url = f"/finance/invoice/{invoice_number}/"
        link_text = "View Invoice"
        
        return cls.send_notification(
            parent_id=parent_id,
            notification_type=NotificationType.PAYMENT_REMINDER,
            title=title,
            message=message,
            data=data,
            link_url=link_url,
            link_text=link_text,
            related_student_ids=[student_id],
            priority=NotificationPriority.HIGH
        )
    
    @classmethod
    def send_results_published(
        cls,
        parent_id: int,
        student_id: int,
        term: str,
        session: str
    ) -> List[Notification]:
        """Send results published notification"""
        title = "Results Published"
        message = f"Results for {term}, {session} have been published. Login to view your child's performance."
        data = {
            'student_id': student_id,
            'term': term,
            'session': session,
        }
        link_url = f"/results/student/{student_id}/"
        link_text = "View Results"
        
        return cls.send_notification(
            parent_id=parent_id,
            notification_type=NotificationType.RESULT_PUBLISHED,
            title=title,
            message=message,
            data=data,
            link_url=link_url,
            link_text=link_text,
            related_student_ids=[student_id]
        )
    
    @classmethod
    def send_attendance_alert(
        cls,
        parent_id: int,
        student_id: int,
        absence_date: str,
        total_absences: int
    ) -> List[Notification]:
        """Send attendance alert notification"""
        title = "Attendance Alert"
        message = f"Your child was marked absent on {absence_date}. Total absences this term: {total_absences}"
        data = {
            'student_id': student_id,
            'absence_date': absence_date,
            'total_absences': total_absences,
        }
        link_url = f"/attendance/student/{student_id}/"
        link_text = "View Attendance"
        
        return cls.send_notification(
            parent_id=parent_id,
            notification_type=NotificationType.ATTENDANCE_ALERT,
            title=title,
            message=message,
            data=data,
            link_url=link_url,
            link_text=link_text,
            related_student_ids=[student_id],
            priority=NotificationPriority.HIGH
        )
    
    @classmethod
    def send_event_reminder(
        cls,
        parent_ids: List[int],
        event_name: str,
        event_date: str,
        event_time: str,
        location: str
    ) -> List[Notification]:
        """Send event reminder to multiple parents"""
        notifications = []
        title = "Event Reminder"
        message = f"{event_name} on {event_date} at {event_time} at {location}"
        data = {
            'event_name': event_name,
            'event_date': event_date,
            'event_time': event_time,
            'location': location,
        }
        
        for parent_id in parent_ids:
            try:
                notes = cls.send_notification(
                    parent_id=parent_id,
                    notification_type=NotificationType.EVENT_REMINDER,
                    title=title,
                    message=message,
                    data=data,
                    priority=NotificationPriority.NORMAL
                )
                notifications.extend(notes)
            except Exception as e:
                logger.error(f"Failed to send event reminder to parent {parent_id}: {e}")
        
        return notifications
    
    @classmethod
    def mark_as_read(cls, notification_id: int, parent_id: int) -> bool:
        """Mark notification as read"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                parent_id=parent_id
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    @classmethod
    def mark_all_as_read(cls, parent_id: int) -> int:
        """Mark all notifications as read for a parent"""
        count = Notification.objects.filter(
            parent_id=parent_id,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        return count
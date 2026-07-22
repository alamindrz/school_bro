"""
Notification Service
Centralized notification sending across multiple channels
ARCHITECTURE COMPLIANT: Single source of truth for notification operations
"""

from django.core.mail import send_mail, send_mass_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from typing import List, Dict, Any, Optional, Tuple
import logging
import json
from datetime import datetime, timedelta

from .models import (
    Notification, NotificationTemplate, NotificationPreference, 
    NotificationLog
)
from .constants import (
    NotificationType, NotificationChannel, NotificationPriority,
    NotificationStatus, RecipientType
)
from .exceptions import (
    NotificationError, TemplateNotFoundError, InvalidChannelError,
    DeliveryFailedError, RecipientNotFoundError
)

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Centralized notification service
    Handles sending notifications through multiple channels
    SINGLE SOURCE OF TRUTH for notification operations
    """

    # Default channel mappings for different notification types
    DEFAULT_CHANNELS = {
        NotificationType.RESULT_PUBLISHED: [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        NotificationType.REPORT_CARD_READY: [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        NotificationType.TERM_BEGINS: [NotificationChannel.EMAIL, NotificationChannel.SMS],
        NotificationType.TERM_ENDS: [NotificationChannel.EMAIL, NotificationChannel.SMS],
        
        NotificationType.PAYMENT_RECEIPT: [NotificationChannel.EMAIL, NotificationChannel.SMS],
        NotificationType.PAYMENT_REMINDER: [NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.PUSH],
        NotificationType.INVOICE_GENERATED: [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        NotificationType.WAIVER_APPROVED: [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        
        NotificationType.ATTENDANCE_ALERT: [NotificationChannel.SMS, NotificationChannel.PUSH, NotificationChannel.IN_APP],
        NotificationType.LOW_ATTENDANCE: [NotificationChannel.EMAIL, NotificationChannel.SMS],
        
        NotificationType.APPLICATION_STATUS: [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        NotificationType.ADMISSION_OFFER: [NotificationChannel.EMAIL, NotificationChannel.SMS],
        NotificationType.EVENT_REMINDER: [NotificationChannel.EMAIL, NotificationChannel.PUSH],
        NotificationType.GENERAL_ANNOUNCEMENT: [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        
        NotificationType.LEAVE_APPROVED: [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        NotificationType.LEAVE_REJECTED: [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        NotificationType.PERFORMANCE_REVIEW: [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
    }

    @classmethod
    def create_notification(
        cls,
        notification_type: str,
        title: str,
        message: str,
        recipient_type: str,
        recipient_id: Optional[int] = None,
        recipient_group: Optional[str] = None,
        class_id: Optional[int] = None,
        role: Optional[str] = None,
        channels: Optional[List[str]] = None,
        priority: str = NotificationPriority.NORMAL,
        data: Optional[Dict] = None,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        scheduled_for: Optional[datetime] = None,
        created_by_id: Optional[int] = None
    ) -> Notification:
        """
        Create a notification record without sending.
        
        Args:
            notification_type: Type from NotificationType
            title: Notification title
            message: Notification message
            recipient_type: Type from RecipientType
            recipient_id: ID of recipient (if single)
            recipient_group: Group name (if group)
            class_id: Class ID (for class-based)
            role: Role name (for role-based)
            channels: List of channels to use
            priority: Priority level
            data: Additional JSON data
            action_url: URL for action button
            action_text: Text for action button
            scheduled_for: Schedule for later delivery
            created_by_id: User ID creating the notification
            
        Returns:
            Created notification instance
        """
        # Use default channels if not provided
        if not channels:
            channels = cls.DEFAULT_CHANNELS.get(notification_type, [NotificationChannel.IN_APP])
        
        # Create notification record
        notification = Notification.objects.create(
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            channels=channels,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            class_id=class_id,
            data=data or {},
            action_url=action_url or '',
            action_text=action_text or '',
            created_by_id=created_by_id
        )
        
        logger.info(f"Notification created: {notification.id} - {title}")
        return notification

    @classmethod
    def send_notification(
        cls,
        notification_type: str,
        title: str,
        message: str,
        recipient_type: str,
        recipient_id: Optional[int] = None,
        recipient_group: Optional[str] = None,
        class_id: Optional[int] = None,
        role: Optional[str] = None,
        channels: Optional[List[str]] = None,
        priority: str = NotificationPriority.NORMAL,
        data: Optional[Dict] = None,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        scheduled_for: Optional[datetime] = None,
        template_name: Optional[str] = None,
        template_vars: Optional[Dict] = None,
        created_by_id: Optional[int] = None
    ) -> Notification:
        """
        Create and send a notification immediately.
        
        Args:
            Same as create_notification plus:
            template_name: Name of template to use
            template_vars: Variables for template rendering
            
        Returns:
            Sent notification instance
        """
        # Use template if provided
        if template_name:
            try:
                template = NotificationTemplate.objects.get(name=template_name, is_active=True)
                title, message = cls._render_template(template, template_vars or {})
                notification_type = template.notification_type
            except NotificationTemplate.DoesNotExist:
                raise TemplateNotFoundError(f"Template '{template_name}' not found")
        
        # Create notification
        notification = cls.create_notification(
            notification_type=notification_type,
            title=title,
            message=message,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            class_id=class_id,
            channels=channels,
            priority=priority,
            data=data,
            action_url=action_url,
            action_text=action_text,
            scheduled_for=scheduled_for,
            created_by_id=created_by_id
        )
        
        # If scheduled for later, don't send now
        if scheduled_for and scheduled_for > timezone.now():
            logger.info(f"Notification {notification.id} scheduled for {scheduled_for}")
            return notification
        
        # Send immediately
        cls._deliver_notification(notification)
        
        return notification

    @classmethod
    def _deliver_notification(cls, notification: Notification) -> None:
        """
        Deliver a notification through all its channels.
        
        Args:
            notification: Notification instance to deliver
        """
        for channel in notification.channels:
            try:
                success = cls._send_via_channel(notification, channel)
                
                # Create log entry
                NotificationLog.objects.create(
                    notification=notification,
                    channel=channel,
                    status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
                )
                
            except Exception as e:
                logger.error(f"Failed to send {channel} notification: {e}")
                NotificationLog.objects.create(
                    notification=notification,
                    channel=channel,
                    status=NotificationStatus.FAILED,
                    error=str(e)
                )
        
        # Update notification status
        if notification.logs.filter(status=NotificationStatus.FAILED).count() == len(notification.channels):
            notification.status = NotificationStatus.FAILED
        else:
            notification.status = NotificationStatus.SENT
            notification.sent_at = timezone.now()
        
        notification.save(update_fields=['status', 'sent_at'])

    @classmethod
    def _send_via_channel(cls, notification: Notification, channel: str) -> bool:
        """
        Send notification through specific channel.
        
        Args:
            notification: Notification instance
            channel: Channel to send through
            
        Returns:
            True if sent successfully, False otherwise
        """
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
            raise InvalidChannelError(f"Unknown channel: {channel}")

    @classmethod
    def _send_email(cls, notification: Notification) -> bool:
        """
        Send email notification.
        
        Args:
            notification: Notification instance
            
        Returns:
            True if email sent successfully
        """
        try:
            # Check user preferences
            if not cls._check_preferences(notification, NotificationChannel.EMAIL):
                logger.info(f"Email disabled for notification {notification.id}")
                return False
            
            # Get recipient email
            email = cls._get_recipient_email(notification)
            if not email:
                logger.warning(f"No email found for notification {notification.id}")
                return False
            
            # Send email
            send_mail(
                subject=notification.title,
                message=strip_tags(notification.message),
                html_message=notification.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            logger.info(f"Email sent for notification {notification.id}")
            return True
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            raise DeliveryFailedError(f"Email delivery failed: {e}")

    @classmethod
    def _send_sms(cls, notification: Notification) -> bool:
        """
        Send SMS notification.
        
        Args:
            notification: Notification instance
            
        Returns:
            True if SMS sent successfully
        """
        try:
            # Check user preferences
            if not cls._check_preferences(notification, NotificationChannel.SMS):
                logger.info(f"SMS disabled for notification {notification.id}")
                return False
            
            # Get recipient phone
            phone = cls._get_recipient_phone(notification)
            if not phone:
                logger.warning(f"No phone found for notification {notification.id}")
                return False
            
            # Truncate message for SMS (160 characters max)
            sms_message = notification.message[:157] + '...' if len(notification.message) > 160 else notification.message
            
            # TODO: Integrate with SMS provider (Twilio, Africa's Talking, etc.)
            # This is a placeholder - implement based on your SMS provider
            logger.info(f"SMS would be sent to {phone}: {sms_message}")
            
            # Simulate success for now
            return True
            
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            raise DeliveryFailedError(f"SMS delivery failed: {e}")

    @classmethod
    def _send_push(cls, notification: Notification) -> bool:
        """
        Send push notification.
        
        Args:
            notification: Notification instance
            
        Returns:
            True if push sent successfully
        """
        try:
            # Check user preferences
            if not cls._check_preferences(notification, NotificationChannel.PUSH):
                logger.info(f"Push disabled for notification {notification.id}")
                return False
            
            # TODO: Integrate with Firebase Cloud Messaging or similar
            # This is a placeholder - implement based on your push provider
            logger.info(f"Push notification would be sent for notification {notification.id}")
            
            # Simulate success for now
            return True
            
        except Exception as e:
            logger.error(f"Push sending failed: {e}")
            raise DeliveryFailedError(f"Push delivery failed: {e}")

    @classmethod
    def _get_recipient_email(cls, notification: Notification) -> Optional[str]:
        """
        Get email for recipient.
        
        Args:
            notification: Notification instance
            
        Returns:
            Email address or None
        """
        if notification.recipient_type == 'student' and notification.recipient_id:
            from apps.students.models import Student
            try:
                return Student.objects.get(id=notification.recipient_id).email
            except Student.DoesNotExist:
                return None
        
        elif notification.recipient_type == 'parent' and notification.recipient_id:
            from apps.parents.models import ParentProfile
            try:
                return ParentProfile.objects.get(id=notification.recipient_id).email
            except ParentProfile.DoesNotExist:
                return None
        
        elif notification.recipient_type == 'staff' and notification.recipient_id:
            from apps.staffs.models import Staff
            try:
                return Staff.objects.get(id=notification.recipient_id).email
            except Staff.DoesNotExist:
                return None
        
        return None

    @classmethod
    def _get_recipient_phone(cls, notification: Notification) -> Optional[str]:
        """
        Get phone number for recipient.
        
        Args:
            notification: Notification instance
            
        Returns:
            Phone number or None
        """
        if notification.recipient_type == 'student' and notification.recipient_id:
            from apps.students.models import Student
            try:
                return Student.objects.get(id=notification.recipient_id).phone
            except Student.DoesNotExist:
                return None
        
        elif notification.recipient_type == 'parent' and notification.recipient_id:
            from apps.parents.models import ParentProfile
            try:
                return ParentProfile.objects.get(id=notification.recipient_id).phone
            except ParentProfile.DoesNotExist:
                return None
        
        elif notification.recipient_type == 'staff' and notification.recipient_id:
            from apps.staffs.models import Staff
            try:
                return Staff.objects.get(id=notification.recipient_id).phone
            except Staff.DoesNotExist:
                return None
        
        return None

    @classmethod
    def _get_user_for_recipient(cls, notification: Notification) -> Optional[Any]:
        """
        Get Django user for recipient.
        
        Args:
            notification: Notification instance
            
        Returns:
            User instance or None
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if notification.recipient_type == 'student' and notification.recipient_id:
            from apps.students.models import Student
            try:
                student = Student.objects.get(id=notification.recipient_id)
                return student.user
            except Student.DoesNotExist:
                return None
        
        elif notification.recipient_type == 'parent' and notification.recipient_id:
            from apps.parents.models import ParentProfile
            try:
                parent = ParentProfile.objects.get(id=notification.recipient_id)
                return parent.user
            except ParentProfile.DoesNotExist:
                return None
        
        elif notification.recipient_type == 'staff' and notification.recipient_id:
            from apps.staffs.models import Staff
            try:
                staff = Staff.objects.get(id=notification.recipient_id)
                return staff.user
            except Staff.DoesNotExist:
                return None
        
        return None

    @classmethod
    def _check_preferences(cls, notification: Notification, channel: str) -> bool:
        """
        Check if user has enabled this channel for this notification type.
        
        Args:
            notification: Notification instance
            channel: Channel to check
            
        Returns:
            True if enabled, False otherwise
        """
        user = cls._get_user_for_recipient(notification)
        if not user:
            return True  # No user, can't check preferences
        
        try:
            prefs = NotificationPreference.objects.get(user=user)
            
            # Check global channel settings
            if channel == NotificationChannel.EMAIL and not prefs.email_enabled:
                return False
            if channel == NotificationChannel.SMS and not prefs.sms_enabled:
                return False
            if channel == NotificationChannel.PUSH and not prefs.push_enabled:
                return False
            if channel == NotificationChannel.IN_APP and not prefs.in_app_enabled:
                return False
            
            # Check quiet hours
            if prefs.quiet_hours_start and prefs.quiet_hours_end:
                now = timezone.now().time()
                if prefs.quiet_hours_start <= now <= prefs.quiet_hours_end:
                    return False
            
            # Check per-type preferences
            channels = prefs.preferences.get(notification.notification_type, [])
            if channels and channel not in channels:
                return False
            
            return True
            
        except NotificationPreference.DoesNotExist:
            return True

    @classmethod
    def _render_template(cls, template: NotificationTemplate, variables: Dict) -> Tuple[str, str]:
        """
        Render template with variables.
        
        Args:
            template: Template instance
            variables: Variables to substitute
            
        Returns:
            Tuple of (title, message)
        """
        title = template.email_subject
        message = template.email_template or template.in_app_message or template.sms_template
        
        # Simple variable substitution
        for key, value in variables.items():
            placeholder = f"{{{{ {key} }}}}"
            title = title.replace(placeholder, str(value))
            message = message.replace(placeholder, str(value))
        
        return title, message

    @classmethod
    def send_bulk_notification(
        cls,
        notification_type: str,
        title: str,
        message: str,
        recipient_type: str,
        class_id: Optional[int] = None,
        role: Optional[str] = None,
        channels: Optional[List[str]] = None,
        priority: str = NotificationPriority.NORMAL,
        data: Optional[Dict] = None,
        created_by_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send notification to multiple recipients.
        
        Args:
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            recipient_type: Type of recipients (all_students, all_parents, all_staff, specific_class)
            class_id: Class ID for class-based
            role: Role for role-based
            channels: Channels to use
            priority: Priority level
            data: Additional data
            created_by_id: User creating the notification
            
        Returns:
            Dictionary with results (total_sent, success_count, failure_count)
        """
        notifications = []
        success_count = 0
        failure_count = 0
        
        if recipient_type == 'all_students':
            from apps.students.models import Student
            students = Student.objects.filter(status='active')
            
            for student in students:
                try:
                    notification = cls.send_notification(
                        notification_type=notification_type,
                        title=title,
                        message=message,
                        recipient_type='student',
                        recipient_id=student.id,
                        channels=channels,
                        priority=priority,
                        data=data,
                        created_by_id=created_by_id
                    )
                    notifications.append(notification)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send to student {student.id}: {e}")
                    failure_count += 1
        
        elif recipient_type == 'all_parents':
            from apps.parents.models import ParentProfile
            parents = ParentProfile.objects.filter(access_status='active')
            
            for parent in parents:
                try:
                    notification = cls.send_notification(
                        notification_type=notification_type,
                        title=title,
                        message=message,
                        recipient_type='parent',
                        recipient_id=parent.id,
                        channels=channels,
                        priority=priority,
                        data=data,
                        created_by_id=created_by_id
                    )
                    notifications.append(notification)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send to parent {parent.id}: {e}")
                    failure_count += 1
        
        elif recipient_type == 'all_staff':
            from apps.staffs.models import Staff
            staff = Staff.objects.filter(employment_status='active')
            
            for member in staff:
                try:
                    notification = cls.send_notification(
                        notification_type=notification_type,
                        title=title,
                        message=message,
                        recipient_type='staff',
                        recipient_id=member.id,
                        channels=channels,
                        priority=priority,
                        data=data,
                        created_by_id=created_by_id
                    )
                    notifications.append(notification)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send to staff {member.id}: {e}")
                    failure_count += 1
        
        elif recipient_type == 'specific_class' and class_id:
            from apps.students.models import Student
            students = Student.objects.filter(current_class_id=class_id, status='active')
            
            for student in students:
                try:
                    notification = cls.send_notification(
                        notification_type=notification_type,
                        title=title,
                        message=message,
                        recipient_type='student',
                        recipient_id=student.id,
                        channels=channels,
                        priority=priority,
                        data=data,
                        created_by_id=created_by_id
                    )
                    notifications.append(notification)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send to student {student.id}: {e}")
                    failure_count += 1
        
        elif recipient_type == 'specific_role' and role:
            from apps.staffs.models import Staff
            staff = Staff.objects.filter(staff_type=role, employment_status='active')
            
            for member in staff:
                try:
                    notification = cls.send_notification(
                        notification_type=notification_type,
                        title=title,
                        message=message,
                        recipient_type='staff',
                        recipient_id=member.id,
                        channels=channels,
                        priority=priority,
                        data=data,
                        created_by_id=created_by_id
                    )
                    notifications.append(notification)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send to staff {member.id}: {e}")
                    failure_count += 1
        
        return {
            'total': len(notifications),
            'success': success_count,
            'failure': failure_count,
            'notifications': notifications
        }

    @classmethod
    def mark_as_read(cls, notification_id: int) -> bool:
        """
        Mark a notification as read.
        
        Args:
            notification_id: ID of notification to mark
            
        Returns:
            True if successful
        """
        try:
            notification = Notification.objects.get(id=notification_id)
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            raise NotificationError(f"Notification {notification_id} not found")

    @classmethod
    def mark_all_as_read(cls, recipient_type: str, recipient_id: Optional[int] = None) -> int:
        """
        Mark all notifications as read for a recipient.
        
        Args:
            recipient_type: Type of recipient
            recipient_id: ID of recipient
            
        Returns:
            Number of notifications marked as read
        """
        queryset = Notification.objects.filter(
            recipient_type=recipient_type,
            status=NotificationStatus.PENDING
        )
        
        if recipient_id:
            queryset = queryset.filter(
                Q(recipient_id=recipient_id) | Q(recipient_id__isnull=True)
            )
        
        count = queryset.count()
        queryset.update(
            status=NotificationStatus.READ,
            read_at=timezone.now()
        )
        
        return count

    @classmethod
    def resend_notification(cls, notification_id: int, user_id: Optional[int] = None) -> Notification:
        """
        Resend a failed notification.
        
        Args:
            notification_id: ID of notification to resend
            user_id: User requesting resend
            
        Returns:
            Resent notification instance
        """
        try:
            notification = Notification.objects.get(id=notification_id)
        except Notification.DoesNotExist:
            raise NotificationError(f"Notification {notification_id} not found")
        
        # Reset status
        notification.status = NotificationStatus.PENDING
        notification.sent_at = None
        notification.delivered_at = None
        notification.save(update_fields=['status', 'sent_at', 'delivered_at'])
        
        # Resend
        cls._deliver_notification(notification)
        
        return notification

    @classmethod
    def update_user_preferences(cls, user_id: int, preferences: Dict) -> NotificationPreference:
        """
        Update notification preferences for a user.
        
        Args:
            user_id: User ID
            preferences: Dictionary of preferences
            
        Returns:
            Updated NotificationPreference instance
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotificationError(f"User {user_id} not found")
        
        # Get or create preferences
        prefs, created = NotificationPreference.objects.get_or_create(user=user)
        
        # Update fields
        if 'email_enabled' in preferences:
            prefs.email_enabled = preferences['email_enabled']
        if 'sms_enabled' in preferences:
            prefs.sms_enabled = preferences['sms_enabled']
        if 'push_enabled' in preferences:
            prefs.push_enabled = preferences['push_enabled']
        if 'in_app_enabled' in preferences:
            prefs.in_app_enabled = preferences['in_app_enabled']
        if 'quiet_hours_start' in preferences:
            prefs.quiet_hours_start = preferences['quiet_hours_start']
        if 'quiet_hours_end' in preferences:
            prefs.quiet_hours_end = preferences['quiet_hours_end']
        if 'preferences' in preferences:
            prefs.preferences = preferences['preferences']
        
        prefs.save()
        
        return prefs

    @classmethod
    def archive_old_notifications(cls, days: int = 30) -> int:
        """
        Archive notifications older than specified days.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of notifications archived
        """
        cutoff = timezone.now() - timedelta(days=days)
        
        # Soft delete by marking as archived
        old_notifications = Notification.objects.filter(
            created_at__lt=cutoff,
            status__in=[NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.READ]
        )
        
        count = old_notifications.count()
        old_notifications.update(status=NotificationStatus.ARCHIVED)
        
        logger.info(f"Archived {count} notifications older than {days} days")
        return count

    @classmethod
    def belongs_to_user(cls, notification: Notification, user) -> bool:
        """
        Check if a notification belongs to a user.
        
        Args:
            notification: Notification instance
            user: User instance
            
        Returns:
            True if notification belongs to user
        """
        if hasattr(user, 'student_profile') and notification.recipient_type == 'student':
            return notification.recipient_id == user.student_profile.id
        
        elif hasattr(user, 'parent_profile') and notification.recipient_type == 'parent':
            return notification.recipient_id == user.parent_profile.id
        
        elif hasattr(user, 'staff_profile') and notification.recipient_type == 'staff':
            return notification.recipient_id == user.staff_profile.id
        
        return False


class TemplateService:
    """
    Notification template management service.
    """

    @classmethod
    def create_template(
        cls,
        name: str,
        notification_type: str,
        email_subject: str = '',
        email_template: str = '',
        sms_template: str = '',
        push_title: str = '',
        push_body: str = '',
        in_app_message: str = '',
        available_variables: List[str] = None,
        created_by_id: Optional[int] = None
    ) -> NotificationTemplate:
        """
        Create a new notification template.
        
        Args:
            name: Template name
            notification_type: Type of notification
            email_subject: Email subject line
            email_template: HTML email template
            sms_template: SMS template
            push_title: Push notification title
            push_body: Push notification body
            in_app_message: In-app message
            available_variables: List of available variables
            created_by_id: User creating the template
            
        Returns:
            Created template instance
        """
        template = NotificationTemplate.objects.create(
            name=name,
            notification_type=notification_type,
            email_subject=email_subject,
            email_template=email_template,
            sms_template=sms_template,
            push_title=push_title,
            push_body=push_body,
            in_app_message=in_app_message,
            available_variables=available_variables or []
        )
        
        logger.info(f"Template created: {template.name}")
        return template

    @classmethod
    def update_template(cls, template_id: int, **kwargs) -> NotificationTemplate:
        """
        Update a notification template.
        
        Args:
            template_id: Template ID
            **kwargs: Fields to update
            
        Returns:
            Updated template instance
        """
        try:
            template = NotificationTemplate.objects.get(id=template_id)
        except NotificationTemplate.DoesNotExist:
            raise TemplateNotFoundError(f"Template {template_id} not found")
        
        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.save()
        logger.info(f"Template updated: {template.name}")
        
        return template

    @classmethod
    def delete_template(cls, template_id: int) -> bool:
        """
        Delete a notification template.
        
        Args:
            template_id: Template ID
            
        Returns:
            True if deleted
        """
        try:
            template = NotificationTemplate.objects.get(id=template_id)
            template.delete()
            logger.info(f"Template deleted: {template.name}")
            return True
        except NotificationTemplate.DoesNotExist:
            raise TemplateNotFoundError(f"Template {template_id} not found")


# Convenience functions for common notification types

def send_payment_receipt(
    parent_id: int,
    student_id: int,
    amount: float,
    receipt_number: str,
    payment_date: str
) -> Notification:
    """Send payment receipt notification."""
    return NotificationService.send_notification(
        notification_type=NotificationType.PAYMENT_RECEIPT,
        title="Payment Receipt",
        message=f"Payment of ₦{amount} has been received. Receipt: {receipt_number}",
        recipient_type='parent',
        recipient_id=parent_id,
        data={
            'amount': amount,
            'receipt_number': receipt_number,
            'payment_date': payment_date,
            'student_id': student_id,
        },
        action_url=f"/finance/receipt/{receipt_number}/",
        action_text="View Receipt"
    )


def send_payment_reminder(
    parent_id: int,
    student_id: int,
    amount: float,
    due_date: str,
    invoice_number: str
) -> Notification:
    """Send payment reminder notification."""
    return NotificationService.send_notification(
        notification_type=NotificationType.PAYMENT_REMINDER,
        title="Payment Reminder",
        message=f"Payment of ₦{amount} is due on {due_date}. Please make arrangements to avoid late fees.",
        recipient_type='parent',
        recipient_id=parent_id,
        priority=NotificationPriority.HIGH,
        data={
            'amount': amount,
            'due_date': due_date,
            'invoice_number': invoice_number,
            'student_id': student_id,
        },
        action_url=f"/finance/invoice/{invoice_number}/",
        action_text="View Invoice"
    )


def send_results_published(
    parent_id: int,
    student_id: int,
    term: str,
    session: str
) -> Notification:
    """Send results published notification."""
    return NotificationService.send_notification(
        notification_type=NotificationType.RESULT_PUBLISHED,
        title="Results Published",
        message=f"Results for {term}, {session} have been published.",
        recipient_type='parent',
        recipient_id=parent_id,
        data={
            'student_id': student_id,
            'term': term,
            'session': session,
        },
        action_url=f"/results/student/{student_id}/",
        action_text="View Results"
    )


def send_attendance_alert(
    parent_id: int,
    student_id: int,
    absence_date: str,
    total_absences: int
) -> Notification:
    """Send attendance alert notification."""
    return NotificationService.send_notification(
        notification_type=NotificationType.ATTENDANCE_ALERT,
        title="Attendance Alert",
        message=f"Your child was marked absent on {absence_date}. Total absences this term: {total_absences}",
        recipient_type='parent',
        recipient_id=parent_id,
        priority=NotificationPriority.HIGH,
        data={
            'student_id': student_id,
            'absence_date': absence_date,
            'total_absences': total_absences,
        },
        action_url=f"/attendance/student/{student_id}/",
        action_text="View Attendance"
    )


def send_application_status_update(
    applicant_email: str,
    application_number: str,
    status: str
) -> Notification:
    """Send application status update notification."""
    return NotificationService.send_notification(
        notification_type=NotificationType.APPLICATION_STATUS,
        title="Application Status Update",
        message=f"Your application {application_number} status has been updated to {status}.",
        recipient_type='student',
        data={
            'application_number': application_number,
            'status': status,
        },
        action_url=f"/admissions/apply/{application_number}/",
        action_text="View Application"
    )


def send_event_reminder(
    parent_ids: List[int],
    event_name: str,
    event_date: str,
    event_time: str,
    location: str
) -> List[Notification]:
    """Send event reminder to multiple parents."""
    notifications = []
    for parent_id in parent_ids:
        notification = NotificationService.send_notification(
            notification_type=NotificationType.EVENT_REMINDER,
            title="Event Reminder",
            message=f"{event_name} on {event_date} at {event_time} at {location}",
            recipient_type='parent',
            recipient_id=parent_id,
            data={
                'event_name': event_name,
                'event_date': event_date,
                'event_time': event_time,
                'location': location,
            }
        )
        notifications.append(notification)
    
    return notifications
    
    
def send_leave_approved(
    staff_id: int,
    leave_type: str,
    start_date: str,
    end_date: str
) -> Notification:
    """Send leave approved notification."""
    return NotificationService.send_notification(
        notification_type=NotificationType.LEAVE_APPROVED,
        title="Leave Request Approved",
        message=f"Your {leave_type} request from {start_date} to {end_date} has been approved.",
        recipient_type='staff',
        recipient_id=staff_id,
        priority=NotificationPriority.HIGH,
        data={
            'leave_type': leave_type,
            'start_date': start_date,
            'end_date': end_date,
        }
    )


def send_leave_rejected(
    staff_id: int,
    leave_type: str,
    reason: str
) -> Notification:
    """Send leave rejected notification."""
    return NotificationService.send_notification(
        notification_type=NotificationType.LEAVE_REJECTED,
        title="Leave Request Rejected",
        message=f"Your {leave_type} request has been rejected. Reason: {reason}",
        recipient_type='staff',
        recipient_id=staff_id,
        priority=NotificationPriority.HIGH,
        data={
            'leave_type': leave_type,
            'reason': reason,
        }
    )
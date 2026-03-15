"""
Notifications Selectors - READ Layer
Returns dicts, never model instances
ALL read operations go through this layer
"""

from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from typing import Optional, List, Dict, Any, Tuple
from datetime import date, timedelta, datetime

from .models import Notification, NotificationTemplate, NotificationPreference, NotificationLog
from .constants import NotificationType, NotificationChannel, NotificationPriority, NotificationStatus


class NotificationSelector:
    """
    Notification read operations.
    """

    @staticmethod
    def get_by_id(notification_id: int) -> Optional[Dict[str, Any]]:
        """
        Get notification by ID.
        
        Args:
            notification_id: Primary key of notification
            
        Returns:
            Dictionary with notification data or None if not found
        """
        try:
            note = Notification.objects.select_related(
                'created_by'
            ).prefetch_related('logs').get(id=notification_id)

            return {
                'id': note.id,
                'notification_id': note.notification_id,
                'type': note.notification_type,
                'type_display': note.get_notification_type_display(),
                'title': note.title,
                'message': note.message,
                'priority': note.priority,
                'priority_display': note.get_priority_display(),
                'status': note.status,
                'status_display': note.get_status_display(),
                'channels': note.channels,
                'recipient_type': note.recipient_type,
                'recipient_id': note.recipient_id,
                'recipient_group': note.recipient_group,
                'class_id': note.class_id,
                'role': note.role,
                'data': note.data,
                'action_url': note.action_url,
                'action_text': note.action_text,
                'sent_at': note.sent_at.isoformat() if note.sent_at else None,
                'delivered_at': note.delivered_at.isoformat() if note.delivered_at else None,
                'read_at': note.read_at.isoformat() if note.read_at else None,
                'created_by': note.created_by.get_full_name() if note.created_by else None,
                'created_at': note.created_at.isoformat(),
                'updated_at': note.updated_at.isoformat(),
                
                'logs': [
                    {
                        'id': log.id,
                        'channel': log.channel,
                        'channel_display': log.get_channel_display(),
                        'status': log.status,
                        'status_display': log.get_status_display(),
                        'response': log.response,
                        'error': log.error,
                        'created_at': log.created_at.isoformat(),
                    }
                    for log in note.logs.all().order_by('-created_at')
                ],
            }
        except Notification.DoesNotExist:
            return None

    @staticmethod
    def get_by_notification_id(notification_id: str) -> Optional[Dict[str, Any]]:
        """
        Get notification by its UUID.
        
        Args:
            notification_id: UUID of notification
            
        Returns:
            Dictionary with notification data or None if not found
        """
        try:
            note = Notification.objects.get(notification_id=notification_id)
            return NotificationSelector.get_by_id(note.id)
        except Notification.DoesNotExist:
            return None

    @staticmethod
    def list_for_recipient(
        recipient_type: str,
        recipient_id: Optional[int] = None,
        status: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
        created_after: Optional[datetime] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List notifications for a specific recipient.
        
        Args:
            recipient_type: Type of recipient (student, parent, staff)
            recipient_id: ID of recipient (optional for group notifications)
            status: Filter by status
            unread_only: Show only unread notifications
            limit: Maximum records to return
            offset: Number of records to skip
            created_after: Get notifications created after this time
            
        Returns:
            Tuple of (notifications list, total count)
        """
        queryset = Notification.objects.filter(recipient_type=recipient_type)
        
        if recipient_id:
            queryset = queryset.filter(
                Q(recipient_id=recipient_id) | Q(recipient_id__isnull=True)
            )
        
        if status:
            queryset = queryset.filter(status=status)
        
        if unread_only:
            queryset = queryset.filter(status=NotificationStatus.PENDING)
        
        if created_after:
            queryset = queryset.filter(created_at__gt=created_after)
        
        total = queryset.count()
        
        notifications = []
        for note in queryset.order_by('-created_at')[offset:offset + limit]:
            notifications.append({
                'id': note.id,
                'notification_id': note.notification_id,
                'type': note.notification_type,
                'type_display': note.get_notification_type_display(),
                'title': note.title,
                'message': note.message[:150] + ('...' if len(note.message) > 150 else ''),
                'priority': note.priority,
                'priority_display': note.get_priority_display(),
                'status': note.status,
                'status_display': note.get_status_display(),
                'channels': note.channels,
                'data': note.data,
                'action_url': note.action_url,
                'action_text': note.action_text,
                'created_at': note.created_at.isoformat(),
                'time_ago': NotificationSelector._time_ago(note.created_at),
                'is_read': note.status != NotificationStatus.PENDING,
            })

        return notifications, total

    @staticmethod
    def get_unread_count(
        recipient_type: str,
        recipient_id: Optional[int] = None
    ) -> int:
        """
        Get count of unread notifications for a recipient.
        
        Args:
            recipient_type: Type of recipient
            recipient_id: ID of recipient
            
        Returns:
            Number of unread notifications
        """
        queryset = Notification.objects.filter(
            recipient_type=recipient_type,
            status=NotificationStatus.PENDING
        )
        
        if recipient_id:
            queryset = queryset.filter(
                Q(recipient_id=recipient_id) | Q(recipient_id__isnull=True)
            )
        
        return queryset.count()

    @staticmethod
    def list_notifications(
        notification_type: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        recipient_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List all notifications with filtering (admin view).
        
        Args:
            notification_type: Filter by notification type
            status: Filter by status
            priority: Filter by priority
            recipient_type: Filter by recipient type
            start_date: Filter by created date >= start_date
            end_date: Filter by created date <= end_date
            search: Search in title and message
            limit: Maximum records to return
            offset: Number of records to skip
            
        Returns:
            Tuple of (notifications list, total count)
        """
        queryset = Notification.objects.select_related('created_by').all()

        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        if status:
            queryset = queryset.filter(status=status)

        if priority:
            queryset = queryset.filter(priority=priority)

        if recipient_type:
            queryset = queryset.filter(recipient_type=recipient_type)

        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)

        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(message__icontains=search)
            )

        total = queryset.count()

        notifications = []
        for note in queryset.order_by('-created_at')[offset:offset + limit]:
            notifications.append({
                'id': note.id,
                'notification_id': note.notification_id,
                'type': note.notification_type,
                'type_display': note.get_notification_type_display(),
                'title': note.title,
                'priority': note.priority,
                'priority_display': note.get_priority_display(),
                'status': note.status,
                'status_display': note.get_status_display(),
                'recipient_type': note.recipient_type,
                'recipient_summary': NotificationSelector._get_recipient_summary(note),
                'channels': note.channels,
                'sent_at': note.sent_at.isoformat() if note.sent_at else None,
                'created_at': note.created_at.isoformat(),
                'created_by': note.created_by.get_full_name() if note.created_by else None,
            })

        return notifications, total

    @staticmethod
    def _get_recipient_summary(notification) -> str:
        """Get human-readable recipient summary."""
        if notification.recipient_id:
            if notification.recipient_type == 'student':
                return f"Student #{notification.recipient_id}"
            elif notification.recipient_type == 'parent':
                return f"Parent #{notification.recipient_id}"
            elif notification.recipient_type == 'staff':
                return f"Staff #{notification.recipient_id}"
        elif notification.recipient_group:
            return f"Group: {notification.recipient_group}"
        elif notification.class_id:
            return f"Class #{notification.class_id}"
        elif notification.role:
            return f"Role: {notification.role}"
        
        return notification.recipient_type

    @staticmethod
    def _time_ago(timestamp):
        """Human readable time ago."""
        from django.utils.timesince import timesince
        from django.utils.timezone import now
        
        if not timestamp:
            return ''
        
        diff = now() - timestamp
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "just now"


class TemplateSelector:
    """
    Notification template read operations.
    """

    @staticmethod
    def get_by_id(template_id: int) -> Optional[Dict[str, Any]]:
        """
        Get template by ID.
        
        Args:
            template_id: Primary key of template
            
        Returns:
            Dictionary with template data or None if not found
        """
        try:
            tpl = NotificationTemplate.objects.get(id=template_id)
            
            return {
                'id': tpl.id,
                'name': tpl.name,
                'notification_type': tpl.notification_type,
                'notification_type_display': tpl.get_notification_type_display(),
                'email_subject': tpl.email_subject,
                'email_template': tpl.email_template,
                'sms_template': tpl.sms_template,
                'push_title': tpl.push_title,
                'push_body': tpl.push_body,
                'in_app_message': tpl.in_app_message,
                'available_variables': tpl.available_variables,
                'is_active': tpl.is_active,
                'created_at': tpl.created_at.isoformat(),
                'updated_at': tpl.updated_at.isoformat(),
            }
        except NotificationTemplate.DoesNotExist:
            return None

    @staticmethod
    def get_by_name(name: str) -> Optional[Dict[str, Any]]:
        """
        Get template by name.
        
        Args:
            name: Template name
            
        Returns:
            Dictionary with template data or None if not found
        """
        try:
            tpl = NotificationTemplate.objects.get(name=name)
            return TemplateSelector.get_by_id(tpl.id)
        except NotificationTemplate.DoesNotExist:
            return None

    @staticmethod
    def list_templates(
        notification_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List notification templates.
        
        Args:
            notification_type: Filter by notification type
            active_only: Include only active templates
            
        Returns:
            List of template dictionaries
        """
        queryset = NotificationTemplate.objects.all()
        
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        if active_only:
            queryset = queryset.filter(is_active=True)

        templates = []
        for tpl in queryset.order_by('name'):
            templates.append({
                'id': tpl.id,
                'name': tpl.name,
                'notification_type': tpl.notification_type,
                'notification_type_display': tpl.get_notification_type_display(),
                'email_subject': tpl.email_subject,
                'sms_template': tpl.sms_template,
                'is_active': tpl.is_active,
            })

        return templates


class UserPreferenceSelector:
    """
    User notification preference read operations.
    """

    @staticmethod
    def get_for_user(user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get notification preferences for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user preferences or None if not found
        """
        try:
            prefs = NotificationPreference.objects.select_related('user').get(user_id=user_id)
            
            return {
                'user_id': prefs.user.id,
                'user_email': prefs.user.email,
                'email_enabled': prefs.email_enabled,
                'sms_enabled': prefs.sms_enabled,
                'push_enabled': prefs.push_enabled,
                'in_app_enabled': prefs.in_app_enabled,
                'quiet_hours_start': prefs.quiet_hours_start.isoformat() if prefs.quiet_hours_start else None,
                'quiet_hours_end': prefs.quiet_hours_end.isoformat() if prefs.quiet_hours_end else None,
                'preferences': prefs.preferences,
                'created_at': prefs.created_at.isoformat(),
                'updated_at': prefs.updated_at.isoformat(),
            }
        except NotificationPreference.DoesNotExist:
            return {
                'user_id': user_id,
                'email_enabled': True,
                'sms_enabled': True,
                'push_enabled': True,
                'in_app_enabled': True,
                'preferences': {},
            }


class NotificationStatsSelector:
    """
    Notification statistics read operations.
    """

    @staticmethod
    def get_summary(days: int = 30) -> Dict[str, Any]:
        """
        Get summary statistics for notifications.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with summary statistics
        """
        start_date = timezone.now() - timedelta(days=days)
        queryset = Notification.objects.filter(created_at__gte=start_date)

        total = queryset.count()
        sent = queryset.filter(status=NotificationStatus.SENT).count()
        delivered = queryset.filter(status=NotificationStatus.DELIVERED).count()
        read = queryset.filter(status=NotificationStatus.READ).count()
        failed = queryset.filter(status=NotificationStatus.FAILED).count()
        pending = queryset.filter(status=NotificationStatus.PENDING).count()

        return {
            'period_days': days,
            'total': total,
            'sent': sent,
            'delivered': delivered,
            'read': read,
            'failed': failed,
            'pending': pending,
            'success_rate': ((sent + delivered + read) / total * 100) if total > 0 else 0,
        }

    @staticmethod
    def get_detailed_stats(days: int = 30) -> Dict[str, Any]:
        """
        Get detailed notification statistics.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with detailed statistics
        """
        start_date = timezone.now() - timedelta(days=days)
        queryset = Notification.objects.filter(created_at__gte=start_date)

        # By type
        by_type = {}
        for n_type, _ in NotificationType.CHOICES:
            count = queryset.filter(notification_type=n_type).count()
            if count > 0:
                by_type[n_type] = count

        # By channel
        channel_counts = {c[0]: 0 for c in NotificationChannel.CHOICES}
        for note in queryset:
            for channel in note.channels:
                if channel in channel_counts:
                    channel_counts[channel] += 1

        # By priority
        by_priority = {}
        for priority, _ in NotificationPriority.CHOICES:
            count = queryset.filter(priority=priority).count()
            if count > 0:
                by_priority[priority] = count

        # Daily trend
        daily = []
        current = start_date.date()
        end_date = timezone.now().date()
        
        while current <= end_date:
            day_start = timezone.make_aware(datetime.combine(current, datetime.min.time()))
            day_end = timezone.make_aware(datetime.combine(current, datetime.max.time()))
            
            day_queryset = queryset.filter(created_at__range=(day_start, day_end))
            
            daily.append({
                'date': current.isoformat(),
                'total': day_queryset.count(),
                'sent': day_queryset.filter(status=NotificationStatus.SENT).count(),
                'delivered': day_queryset.filter(status=NotificationStatus.DELIVERED).count(),
                'read': day_queryset.filter(status=NotificationStatus.READ).count(),
                'failed': day_queryset.filter(status=NotificationStatus.FAILED).count(),
            })
            
            current += timedelta(days=1)

        return {
            'period_days': days,
            'summary': NotificationStatsSelector.get_summary(days),
            'by_type': by_type,
            'by_channel': channel_counts,
            'by_priority': by_priority,
            'daily_trend': daily,
        }

    @staticmethod
    def get_user_stats(user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get notification statistics for a specific user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            Dictionary with user notification statistics
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
            
            # Determine recipient type
            if hasattr(user, 'student_profile'):
                recipient_type = 'student'
                recipient_id = user.student_profile.id
            elif hasattr(user, 'parent_profile'):
                recipient_type = 'parent'
                recipient_id = user.parent_profile.id
            elif hasattr(user, 'staff_profile'):
                recipient_type = 'staff'
                recipient_id = user.staff_profile.id
            else:
                return {'error': 'Unknown user type'}
            
            start_date = timezone.now() - timedelta(days=days)
            
            notifications = Notification.objects.filter(
                recipient_type=recipient_type,
                recipient_id=recipient_id,
                created_at__gte=start_date
            )
            
            total = notifications.count()
            unread = notifications.filter(status=NotificationStatus.PENDING).count()
            
            # By type
            by_type = {}
            for n_type, _ in NotificationType.CHOICES:
                count = notifications.filter(notification_type=n_type).count()
                if count > 0:
                    by_type[n_type] = count
            
            return {
                'user_id': user_id,
                'username': user.username,
                'recipient_type': recipient_type,
                'period_days': days,
                'total': total,
                'unread': unread,
                'read_rate': ((total - unread) / total * 100) if total > 0 else 0,
                'by_type': by_type,
            }
            
        except User.DoesNotExist:
            return {'error': 'User not found'}


class NotificationLogSelector:
    """
    Notification log read operations.
    """

    @staticmethod
    def get_for_notification(notification_id: int) -> List[Dict[str, Any]]:
        """
        Get delivery logs for a notification.
        
        Args:
            notification_id: Notification ID
            
        Returns:
            List of log dictionaries
        """
        logs = NotificationLog.objects.filter(
            notification_id=notification_id
        ).order_by('-created_at')

        log_list = []
        for log in logs:
            log_list.append({
                'id': log.id,
                'channel': log.channel,
                'channel_display': log.get_channel_display(),
                'status': log.status,
                'status_display': log.get_status_display(),
                'response': log.response,
                'error': log.error,
                'created_at': log.created_at.isoformat(),
            })

        return log_list

    @staticmethod
    def get_failed_logs(days: int = 7) -> List[Dict[str, Any]]:
        """
        Get failed notification logs.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of failed log dictionaries
        """
        start_date = timezone.now() - timedelta(days=days)
        
        logs = NotificationLog.objects.filter(
            status=NotificationStatus.FAILED,
            created_at__gte=start_date
        ).select_related('notification').order_by('-created_at')[:100]

        failed_logs = []
        for log in logs:
            failed_logs.append({
                'id': log.id,
                'notification_id': log.notification.id,
                'notification_title': log.notification.title,
                'channel': log.channel,
                'channel_display': log.get_channel_display(),
                'error': log.error,
                'created_at': log.created_at.isoformat(),
            })

        return failed_logs
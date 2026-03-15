"""
Notifications App Exceptions
"""

from apps.corecode.exceptions import CorecodeError


class NotificationError(CorecodeError):
    """Base exception for notification errors"""
    default_message = "A notification error occurred"
    code = 'notification_error'


class NotificationNotFoundError(NotificationError):
    """Notification not found"""
    default_message = "Notification not found"
    code = 'notification_not_found'


class TemplateNotFoundError(NotificationError):
    """Notification template not found"""
    default_message = "Notification template not found"
    code = 'template_not_found'


class InvalidChannelError(NotificationError):
    """Invalid notification channel"""
    default_message = "Invalid notification channel"
    code = 'invalid_channel'


class DeliveryFailedError(NotificationError):
    """Failed to deliver notification"""
    default_message = "Failed to deliver notification"
    code = 'delivery_failed'


class RecipientNotFoundError(NotificationError):
    """Recipient not found"""
    default_message = "Recipient not found"
    code = 'recipient_not_found'
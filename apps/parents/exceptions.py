"""
Parents App Exceptions
Inherit from corecode exceptions
"""

from apps.corecode.exceptions import CorecodeError


class ParentError(CorecodeError):
    """Base exception for all parent portal errors"""
    default_message = "A parent portal error occurred"
    code = 'parent_error'


class ParentNotFoundError(ParentError):
    """Parent/Guardian not found"""
    default_message = "Parent or guardian not found"
    code = 'parent_not_found'


class ChildNotFoundError(ParentError):
    """Child/Student not linked to parent"""
    default_message = "Student not linked to this parent"
    code = 'child_not_found'


class PortalAccessError(ParentError):
    """Portal access errors"""
    default_message = "Portal access error"
    code = 'portal_access_error'


class PortalAccessDeniedError(PortalAccessError):
    """Access denied to portal feature"""
    default_message = "You do not have permission to access this feature"
    code = 'access_denied'


class PortalAccountError(ParentError):
    """Portal account errors"""
    default_message = "Portal account error"
    code = 'portal_account_error'


class PortalAccountAlreadyExistsError(PortalAccountError):
    """Portal account already exists"""
    default_message = "A portal account already exists for this guardian"
    code = 'account_exists'


class NotificationError(ParentError):
    """Notification errors"""
    default_message = "Notification error"
    code = 'notification_error'


class NotificationSendError(NotificationError):
    """Failed to send notification"""
    default_message = "Failed to send notification"
    code = 'notification_send_failed'


class InvalidNotificationTypeError(NotificationError):
    """Invalid notification type"""
    default_message = "Invalid notification type"
    code = 'invalid_notification_type'


class InvalidNotificationChannelError(NotificationError):
    """Invalid notification channel"""
    default_message = "Invalid notification channel"
    code = 'invalid_notification_channel'


class CommunicationError(ParentError):
    """Parent-teacher communication errors"""
    default_message = "Communication error"
    code = 'communication_error'


class MessageNotFoundError(CommunicationError):
    """Message not found"""
    default_message = "Message not found"
    code = 'message_not_found'


class UnauthorizedMessageAccessError(CommunicationError):
    """Unauthorized message access"""
    default_message = "You do not have permission to access this message"
    code = 'unauthorized_message'


class AuthenticationError(ParentError):
    """Authentication errors"""
    default_message = "Authentication failed"
    code = 'auth_error'


class SessionExpiredError(AuthenticationError):
    """Session has expired"""
    default_message = "Your session has expired. Please log in again."
    code = 'session_expired'


class SessionHijackingError(AuthenticationError):
    """Potential session hijacking detected"""
    default_message = "Security check failed. Please log in again."
    code = 'session_hijacking'


class RateLimitExceededError(AuthenticationError):
    """Rate limit exceeded"""
    default_message = "Too many attempts. Please try again later."
    code = 'rate_limit_exceeded'


class MagicLinkExpiredError(AuthenticationError):
    """Magic link has expired"""
    default_message = "This login link has expired. Please request a new one."
    code = 'magic_link_expired'


class MagicLinkAlreadyUsedError(AuthenticationError):
    """Magic link already used"""
    default_message = "This login link has already been used."
    code = 'magic_link_already_used'


class InvalidMagicLinkError(AuthenticationError):
    """Invalid magic link"""
    default_message = "Invalid login link."
    code = 'invalid_magic_link'
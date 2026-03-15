"""
Notifications Validators
"""

from django.core.exceptions import ValidationError
from .constants import NotificationChannel, NotificationType, NotificationPriority


class NotificationValidator:
    """Validate notification data"""
    
    @staticmethod
    def validate_channel(channel: str) -> bool:
        """Validate notification channel"""
        valid_channels = [c[0] for c in NotificationChannel.CHOICES]
        if channel not in valid_channels:
            raise ValidationError(f"Invalid channel: {channel}")
        return True
    
    @staticmethod
    def validate_notification_type(notif_type: str) -> bool:
        """Validate notification type"""
        valid_types = [t[0] for t in NotificationType.CHOICES]
        if notif_type not in valid_types:
            raise ValidationError(f"Invalid notification type: {notif_type}")
        return True
    
    @staticmethod
    def validate_priority(priority: str) -> bool:
        """Validate priority"""
        valid_priorities = [p[0] for p in NotificationPriority.CHOICES]
        if priority not in valid_priorities:
            raise ValidationError(f"Invalid priority: {priority}")
        return True
    
    @staticmethod
    def validate_recipient(recipient_type: str, recipient_id: int = None) -> bool:
        """Validate recipient exists"""
        from .constants import RecipientType
        
        valid_types = [r[0] for r in RecipientType.CHOICES]
        if recipient_type not in valid_types:
            raise ValidationError(f"Invalid recipient type: {recipient_type}")
        
        if recipient_type in ['student', 'parent', 'staff'] and not recipient_id:
            raise ValidationError(f"Recipient ID required for {recipient_type}")
        
        return True


class TemplateValidator:
    """Validate notification templates"""
    
    @staticmethod
    def validate_template_name(name: str) -> bool:
        """Validate template name"""
        if len(name) < 3:
            raise ValidationError("Template name must be at least 3 characters")
        if not name.replace('_', '').isalnum():
            raise ValidationError("Template name can only contain letters, numbers, and underscores")
        return True
    
    @staticmethod
    def validate_variables(template_text: str, declared_vars: list) -> bool:
        """Validate that all template variables are declared"""
        import re
        found_vars = re.findall(r'\{\{\s*(\w+)\s*\}\}', template_text)
        missing = [v for v in found_vars if v not in declared_vars]
        if missing:
            raise ValidationError(f"Undefined variables in template: {', '.join(missing)}")
        return True
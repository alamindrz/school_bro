"""
Notifications Models
Centralized notification system for all apps
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid

from .constants import (
    NotificationType, NotificationChannel, NotificationPriority,
    NotificationStatus, RecipientType
)

User = get_user_model()


class NotificationTemplate(models.Model):
    """
    Reusable notification templates
    """
    
    name = models.CharField(max_length=100, unique=True)
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.CHOICES
    )
    
    # Templates for different channels
    email_subject = models.CharField(max_length=200, blank=True)
    email_template = models.TextField(help_text="HTML email template with variables")
    sms_template = models.CharField(max_length=160, blank=True, help_text="SMS template (max 160 chars)")
    push_title = models.CharField(max_length=100, blank=True)
    push_body = models.CharField(max_length=200, blank=True)
    in_app_message = models.TextField(blank=True)
    
    # Variables documentation
    available_variables = models.JSONField(default=list, blank=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
    
    def __str__(self):
        return self.name


class Notification(models.Model):
    """
    Individual notification instance
    """
    
    # Identification
    notification_id = models.CharField(
        max_length=100,
        unique=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Content
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.CHOICES
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Data and links
    data = models.JSONField(default=dict, blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    action_text = models.CharField(max_length=100, blank=True)
    
    # Priority
    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.CHOICES,
        default=NotificationPriority.NORMAL
    )
    
    # Delivery
    channels = models.JSONField(
        default=list,
        help_text="List of channels to use"
    )
    
    # Recipient (can be user, student_id, parent_id, staff_id, or group)
    recipient_type = models.CharField(
        max_length=20,
        choices=RecipientType.CHOICES
    )
    recipient_id = models.IntegerField(null=True, blank=True)
    recipient_group = models.CharField(max_length=100, blank=True)
    
    # For class/role based notifications
    class_id = models.IntegerField(null=True, blank=True)
    role = models.CharField(max_length=50, blank=True)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.CHOICES,
        default=NotificationStatus.PENDING
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_notifications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['notification_id']),
            models.Index(fields=['recipient_type', 'recipient_id']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
    
    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def mark_as_sent(self):
        """Mark notification as sent"""
        self.status = NotificationStatus.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at', 'updated_at'])
    
    def mark_as_delivered(self):
        """Mark notification as delivered"""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at', 'updated_at'])
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.status = NotificationStatus.READ
        self.read_at = timezone.now()
        self.save(update_fields=['status', 'read_at', 'updated_at'])
    
    def mark_as_failed(self, error):
        """Mark notification as failed"""
        self.status = NotificationStatus.FAILED
        self.error_message = str(error)
        self.save(update_fields=['status', 'error_message', 'updated_at'])


class NotificationPreference(models.Model):
    """
    User notification preferences
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Channel preferences per notification type
    preferences = models.JSONField(
        default=dict,
        help_text="Format: {notification_type: [channels]}"
    )
    
    # Global settings
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    
    # Quiet hours
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')
    
    def __str__(self):
        return f"Preferences for {self.user.email}"
    
    def get_channels_for_type(self, notification_type):
        """Get enabled channels for a notification type"""
        return self.preferences.get(notification_type, [])


class NotificationLog(models.Model):
    """
    Audit log for notifications
    """
    
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    channel = models.CharField(max_length=20, choices=NotificationChannel.CHOICES)
    status = models.CharField(max_length=20, choices=NotificationStatus.CHOICES)
    response = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Notification Log')
        verbose_name_plural = _('Notification Logs')
    
    def __str__(self):
        return f"{self.notification.title} - {self.channel} - {self.status}"
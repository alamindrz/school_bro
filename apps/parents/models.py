"""
Parents Models - Portal and Communication
Depends on: corecode, students (via student_id only)
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator
import uuid

from apps.corecode.models import AcademicSession, AcademicTerm
from .constants import (
    PortalAccessStatus, NotificationType, NotificationChannel,
    NotificationPriority, RelationshipType, DEFAULT_NOTIFICATION_PREFERENCES
)

User = get_user_model()


class ParentProfile(models.Model):
    """
    Parent/Guardian portal profile
    Links Django user to students and manages portal access
    """
    
    # Link to Django user (if portal account created)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='parent_profile'
    )
    
    # Guardian information (denormalized from students app)
    guardian_id = models.IntegerField(
        db_index=True,
        help_text=_("Guardian ID from students app")
    )
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    alternate_phone = models.CharField(max_length=15, blank=True)
    
    # Portal access
    access_status = models.CharField(
        max_length=20,
        choices=PortalAccessStatus.CHOICES,
        default=PortalAccessStatus.PENDING
    )
    access_key = models.CharField(
        max_length=64,
        unique=True,
        default=uuid.uuid4().hex,
        help_text=_("Unique key for portal access URL")
    )
    last_login = models.DateTimeField(null=True, blank=True)
    login_count = models.IntegerField(default=0)
    
    # Preferences
    preferred_language = models.CharField(
        max_length=10,
        default='en',
        help_text=_("Preferred language for communications")
    )
    notification_preferences = models.JSONField(
        default=dict,
        help_text=_("JSON storing notification channel preferences")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['guardian_id']),
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['access_key']),
        ]
        verbose_name = _('Parent Profile')
        verbose_name_plural = _('Parent Profiles')
    
    def __str__(self):
        return f"{self.last_name}, {self.first_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def save(self, *args, **kwargs):
        """Initialize notification preferences if empty"""
        if not self.notification_preferences:
            self.notification_preferences = DEFAULT_NOTIFICATION_PREFERENCES
        super().save(*args, **kwargs)
    
    def record_login(self):
        """Record portal login"""
        self.last_login = timezone.now()
        self.login_count += 1
        self.save(update_fields=['last_login', 'login_count'])


class ChildLink(models.Model):
    """
    Links parent to student (child)
    Allows one parent to have multiple children
    """
    
    parent = models.ForeignKey(
        ParentProfile,
        on_delete=models.CASCADE,
        related_name='children'
    )
    
    # Student reference (decoupled)
    student_id = models.IntegerField(
        db_index=True,
        help_text=_("Student ID from students app")
    )
    student_name = models.CharField(
        max_length=200,
        help_text=_("Denormalized student name")
    )
    student_class = models.CharField(
        max_length=100,
        help_text=_("Current class of student")
    )
    
    # Relationship
    relationship = models.CharField(
        max_length=20,
        choices=RelationshipType.CHOICES
    )
    is_primary = models.BooleanField(
        default=False,
        help_text=_("Primary guardian for this student")
    )
    
    # Permissions
    can_view_results = models.BooleanField(default=True)
    can_view_attendance = models.BooleanField(default=True)
    can_view_fees = models.BooleanField(default=True)
    can_make_payments = models.BooleanField(default=True)
    can_communicate = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['student_name']
        unique_together = ['parent', 'student_id']
        indexes = [
            models.Index(fields=['parent', 'student_id']),
            models.Index(fields=['student_id']),
        ]
        verbose_name = _('Child Link')
        verbose_name_plural = _('Child Links')
    
    def __str__(self):
        return f"{self.parent.full_name} → {self.student_name} ({self.get_relationship_display()})"


class Notification(models.Model):
    """
    Notifications sent to parents
    """
    
    parent = models.ForeignKey(
        ParentProfile,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Notification details
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.CHOICES
    )
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.CHOICES
    )
    priority = models.CharField(
        max_length=10,
        choices=NotificationPriority.CHOICES,
        default=NotificationPriority.NORMAL
    )
    
    # Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional data for the notification")
    )
    
    # Links (optional)
    link_url = models.CharField(max_length=500, blank=True)
    link_text = models.CharField(max_length=100, blank=True)
    
    # Status
    is_sent = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # For grouped notifications (e.g., multiple children)
    related_student_ids = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of student IDs this notification relates to")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['parent', '-created_at']),
            models.Index(fields=['parent', 'is_read']),
            models.Index(fields=['notification_type']),
        ]
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
    
    def __str__(self):
        return f"{self.parent.full_name} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])


class Message(models.Model):
    """
    Parent-teacher messaging system
    """
    
    # Sender and recipient
    sender_parent = models.ForeignKey(
        ParentProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sent_messages'
    )
    sender_teacher_id = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("Teacher ID if sent by teacher")
    )
    
    recipient_parent = models.ForeignKey(
        ParentProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='received_messages'
    )
    recipient_teacher_id = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("Teacher ID if recipient is teacher")
    )
    
    # Message content
    subject = models.CharField(max_length=200)
    body = models.TextField()
    
    # Related entities
    student_id = models.IntegerField(
        db_index=True,
        help_text=_("Student this message is about")
    )
    student_name = models.CharField(max_length=200)
    
    # Threading
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    is_urgent = models.BooleanField(default=False)
    requires_action = models.BooleanField(default=False)
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['sender_parent', '-sent_at']),
            models.Index(fields=['recipient_parent', '-sent_at']),
            models.Index(fields=['student_id']),
            models.Index(fields=['is_read']),
        ]
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')
    
    def __str__(self):
        return f"{self.subject} - {self.sent_at.strftime('%Y-%m-%d')}"
    
    def mark_as_read(self):
        """Mark message as read"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])


class PortalSession(models.Model):
    """
    Track portal sessions for security
    """
    
    parent = models.ForeignKey(
        ParentProfile,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    
    session_key = models.CharField(
        max_length=64,
        unique=True,
        default=uuid.uuid4().hex
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_activity = models.DateTimeField(auto_now=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['parent', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.parent.full_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def is_valid(self):
        """Check if session is still valid"""
        return self.is_active and timezone.now() < self.expires_at


class ParentAccessLog(models.Model):
    """
    Audit log for parent portal access
    """
    
    parent = models.ForeignKey(
        ParentProfile,
        on_delete=models.CASCADE,
        related_name='access_logs'
    )
    
    action = models.CharField(max_length=50)  # LOGIN, VIEW_RESULTS, VIEW_FEES, etc.
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # For actions related to specific students
    student_id = models.IntegerField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['parent', '-timestamp']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.parent.full_name} - {self.action} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
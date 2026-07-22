"""
Parents Models - Portal and Communication
Depends on: corecode, students (via student_id only)
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator, EmailValidator, RegexValidator
from django.core.exceptions import ValidationError
import uuid
import secrets
from datetime import timedelta

from apps.corecode.models import AcademicSession, AcademicTerm
from .constants import (
    PortalAccessStatus, RelationshipType,
    MAGIC_LINK_EXPIRY_MINUTES,
    SESSION_TIMEOUT_SECONDS
)

User = get_user_model()


class ParentProfileManager(models.Manager):
    """Custom manager for ParentProfile"""
    
    def get_active(self):
        return self.filter(access_status=PortalAccessStatus.ACTIVE)
    
    def get_by_email(self, email):
        try:
            return self.select_related('user').prefetch_related('children').get(email=email)
        except self.model.DoesNotExist:
            return None
    
    def search(self, query):
        return self.filter(
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(email__icontains=query) |
            models.Q(phone__icontains=query)
        )


class ParentProfile(models.Model):
    """
    Parent/Guardian portal profile
    Links Django user to students and manages portal access
    """
    
    objects = ParentProfileManager()
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='parent_profile'
    )
    
    guardian_id = models.IntegerField(
        db_index=True,
        help_text=_("Guardian ID from students app")
    )
    first_name = models.CharField(
        max_length=50,
        validators=[MinLengthValidator(1, "First name is required")]
    )
    last_name = models.CharField(
        max_length=50,
        validators=[MinLengthValidator(1, "Last name is required")]
    )
    email = models.EmailField(
        validators=[EmailValidator()]
    )
    phone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    alternate_phone = models.CharField(
        max_length=15,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    
    # Portal access
    access_status = models.CharField(
        max_length=20,
        choices=PortalAccessStatus.CHOICES,
        default=PortalAccessStatus.PENDING
    )
    access_key = models.CharField(
        max_length=64,
        unique=True,
        default=uuid.uuid4,
        help_text=_("Unique key for portal access URL")
    )
    last_login = models.DateTimeField(null=True, blank=True)
    login_count = models.IntegerField(default=0)
    failed_login_attempts = models.IntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    
    # Preferences - removed notification_preferences JSONField (now handled by central notifications app)
    preferred_language = models.CharField(
        max_length=10,
        default='en',
        help_text=_("Preferred language for communications")
    )
    
    # Security
    device_fingerprint = models.CharField(
        max_length=128,
        blank=True,
        help_text=_("Device fingerprint for security")
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
            models.Index(fields=['access_status']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = _('Parent Profile')
        verbose_name_plural = _('Parent Profiles')
    
    def __str__(self):
        return f"{self.last_name}, {self.first_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_active(self):
        return self.access_status == PortalAccessStatus.ACTIVE
    
    @property
    def is_locked(self):
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False
    
    def save(self, *args, **kwargs):
        if self.pk:
            old = ParentProfile.objects.get(pk=self.pk)
            if old.access_status != self.access_status:
                if not PortalAccessStatus.can_transition(old.access_status, self.access_status):
                    raise ValidationError(
                        f"Cannot transition from {old.access_status} to {self.access_status}"
                    )
        super().save(*args, **kwargs)
    
    def record_login(self, device_fingerprint=None):
        self.last_login = timezone.now()
        self.login_count += 1
        self.failed_login_attempts = 0
        self.last_failed_login = None
        if device_fingerprint:
            self.device_fingerprint = device_fingerprint
        self.save(update_fields=['last_login', 'login_count', 'failed_login_attempts', 
                                  'last_failed_login', 'device_fingerprint'])
    
    def record_failed_login(self):
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        if self.failed_login_attempts >= 5:
            self.account_locked_until = timezone.now() + timedelta(minutes=30)
        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'account_locked_until'])
    
    def reset_failed_attempts(self):
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.account_locked_until = None
        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'account_locked_until'])
    
    def generate_magic_link(self):
        from .models import MagicLink
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(minutes=MAGIC_LINK_EXPIRY_MINUTES)
        magic_link = MagicLink.objects.create(
            parent=self,
            token=token,
            expires_at=expires_at,
        )
        return magic_link


class MagicLink(models.Model):
    """Secure magic link for authentication"""
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='magic_links')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_fingerprint = models.CharField(max_length=128, blank=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['token']), models.Index(fields=['parent', 'expires_at']), models.Index(fields=['is_used'])]
        ordering = ['-created_at']

    def __str__(self):
        return f"Magic link for {self.parent.full_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    def use(self, request):
        if not self.is_valid:
            from .exceptions import MagicLinkExpiredError, MagicLinkAlreadyUsedError
            if self.is_expired:
                raise MagicLinkExpiredError()
            if self.is_used:
                raise MagicLinkAlreadyUsedError()
        self.is_used = True
        self.used_at = timezone.now()
        self.ip_address = request.META.get('REMOTE_ADDR')
        self.user_agent = request.META.get('HTTP_USER_AGENT', '')
        self.save(update_fields=['is_used', 'used_at', 'ip_address', 'user_agent'])
        return self.parent


class ChildLink(models.Model):
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='children')
    application_id = models.IntegerField(null=True, blank=True, help_text=_("Admission application ID that created this student"))
    student_id = models.IntegerField(db_index=True, help_text=_("Student ID from students app"))
    student_name = models.CharField(max_length=200, help_text=_("Denormalized student name"))
    student_class = models.CharField(max_length=100, help_text=_("Current class of student"))
    relationship = models.CharField(max_length=20, choices=RelationshipType.CHOICES, default=RelationshipType.DEFAULT)
    is_primary = models.BooleanField(default=False, help_text=_("Primary guardian for this student"))
    can_view_results = models.BooleanField(default=True)
    can_view_attendance = models.BooleanField(default=True)
    can_view_fees = models.BooleanField(default=True)
    can_make_payments = models.BooleanField(default=True)
    can_communicate = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['student_name']
        unique_together = ['parent', 'student_id']
        indexes = [models.Index(fields=['parent', 'student_id']), models.Index(fields=['student_id']), models.Index(fields=['parent']), models.Index(fields=['relationship'])]
        verbose_name = _('Child Link')
        verbose_name_plural = _('Child Links')

    def __str__(self):
        return f"{self.parent.full_name} → {self.student_name} ({self.get_relationship_display()})"

    def has_permission(self, feature):
        permissions = {
            'view_results': self.can_view_results,
            'view_attendance': self.can_view_attendance,
            'view_fees': self.can_view_fees,
            'make_payments': self.can_make_payments,
            'communicate': self.can_communicate,
        }
        return permissions.get(feature, False)


class Message(models.Model):
    """Parent-teacher messaging system - separate from notifications"""
    sender_parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='sent_messages')
    sender_teacher_id = models.IntegerField(null=True, blank=True, help_text=_("Teacher ID if sent by teacher"))
    sender_name = models.CharField(max_length=100, blank=True, help_text=_("Denormalized sender name"))
    recipient_parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='received_messages')
    recipient_teacher_id = models.IntegerField(null=True, blank=True, help_text=_("Teacher ID if recipient is teacher"))
    recipient_name = models.CharField(max_length=100, blank=True, help_text=_("Denormalized recipient name"))
    subject = models.CharField(max_length=200, validators=[MinLengthValidator(1, "Subject is required")])
    body = models.TextField(validators=[MinLengthValidator(1, "Message body is required")])
    student_id = models.IntegerField(db_index=True, help_text=_("Student this message is about"))
    student_name = models.CharField(max_length=200)
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    is_read = models.BooleanField(default=False, db_index=True)
    is_urgent = models.BooleanField(default=False)
    requires_action = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['sender_parent', '-sent_at']),
            models.Index(fields=['recipient_parent', '-sent_at']),
            models.Index(fields=['student_id']),
            models.Index(fields=['is_read']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['student_id', '-sent_at']),
        ]
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')

    def __str__(self):
        return f"{self.subject} - {self.sent_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        if self.sender_parent and not self.sender_name:
            self.sender_name = self.sender_parent.full_name
        if self.recipient_parent and not self.recipient_name:
            self.recipient_name = self.recipient_parent.full_name
        super().save(*args, **kwargs)

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class PortalSession(models.Model):
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=64, unique=True, db_index=True, default=uuid.uuid4)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    device_fingerprint = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_activity = models.DateTimeField(auto_now=True)
    terminated_at = models.DateTimeField(null=True, blank=True)
    termination_reason = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['parent', '-created_at']),
            models.Index(fields=['is_active']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.parent.full_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def is_valid(self):
        return self.is_active and timezone.now() < self.expires_at

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def validate_security_context(self, request):
        from .exceptions import SessionHijackingError
        ip = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        fingerprint = generate_device_fingerprint(request)
        if self.ip_address != ip:
            raise SessionHijackingError("IP address mismatch")
        if self.user_agent != user_agent:
            raise SessionHijackingError("User agent mismatch")
        if self.device_fingerprint and self.device_fingerprint != fingerprint:
            raise SessionHijackingError("Device fingerprint mismatch")
        return True

    def terminate(self, reason="User logout"):
        self.is_active = False
        self.terminated_at = timezone.now()
        self.termination_reason = reason
        self.save(update_fields=['is_active', 'terminated_at', 'termination_reason'])

    def refresh(self, expiry_seconds=None):
        from django.conf import settings
        if expiry_seconds is None:
            expiry_seconds = SESSION_TIMEOUT_SECONDS
        self.expires_at = timezone.now() + timedelta(seconds=expiry_seconds)
        self.save(update_fields=['expires_at'])

    @classmethod
    def cleanup_expired(cls):
        return cls.objects.filter(
            models.Q(is_active=True, expires_at__lt=timezone.now()) |
            models.Q(is_active=True, terminated_at__isnull=False)
        ).update(is_active=False)


class ParentAccessLog(models.Model):
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, null=True, blank=True, related_name="access_logs")
    action = models.CharField(max_length=50, db_index=True, choices=[
        ('LOGIN', 'Login'),
        ('LOGIN_FAILED', 'Login Failed'),
        ('LOGOUT', 'Logout'),
        ('VIEW_RESULTS', 'View Results'),
        ('VIEW_FEES', 'View Fees'),
        ('VIEW_ATTENDANCE', 'View Attendance'),
        ('VIEW_PROFILE', 'View Profile'),
        ('EDIT_PROFILE', 'Edit Profile'),
        ('SEND_MESSAGE', 'Send Message'),
        ('VIEW_MESSAGE', 'View Message'),
        ('PAYMENT', 'Payment'),
        ('DOWNLOAD_REPORT', 'Download Report'),
        ('SESSION_EXPIRED', 'Session Expired'),
        ('SESSION_TERMINATED', 'Session Terminated'),
        ('SUSPICIOUS_ACTIVITY', 'Suspicious Activity'),
    ])
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    device_fingerprint = models.CharField(max_length=128, blank=True)
    student_id = models.IntegerField(null=True, blank=True, db_index=True)
    details = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['parent', '-timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['parent', 'action']),
            models.Index(fields=['timestamp']),
        ]
        verbose_name = _('Parent Access Log')
        verbose_name_plural = _('Parent Access Logs')

    def __str__(self):
        return f"{self.parent.full_name} - {self.action} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


def generate_device_fingerprint(request):
    import hashlib
    fingerprint_string = (
        f"{request.META.get('HTTP_USER_AGENT', '')}"
        f"{request.META.get('HTTP_ACCEPT_LANGUAGE', '')}"
        f"{request.META.get('HTTP_ACCEPT_ENCODING', '')}"
    )
    return hashlib.sha256(fingerprint_string.encode()).hexdigest()
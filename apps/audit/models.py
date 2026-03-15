"""
Audit Models
Comprehensive audit trail for all sensitive operations
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid

from .constants import AuditAction, AuditStatus, AuditCategory

User = get_user_model()


class AuditLog(models.Model):
    """
    Comprehensive audit log for all sensitive operations
    Immutable - never updated, only created
    """
    
    # Unique identifier
    audit_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    
    # Who
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    username = models.CharField(max_length=150, blank=True)
    user_email = models.EmailField(blank=True)
    user_role = models.CharField(max_length=100, blank=True)
    
    # What
    action = models.CharField(max_length=20, choices=AuditAction.CHOICES)
    category = models.CharField(
        max_length=20,
        choices=AuditCategory.CHOICES,
        default=AuditCategory.DATA_ACCESS
    )
    status = models.CharField(
        max_length=20,
        choices=AuditStatus.CHOICES,
        default=AuditStatus.SUCCESS
    )
    
    # Target
    app_label = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    
    # Changes
    old_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    
    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_method = models.CharField(max_length=10, blank=True, null=True)
    request_path = models.CharField(max_length=500, blank=True, null=True)
    request_id = models.CharField(max_length=100, blank=True)
    
    # Metadata
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['app_label', 'model_name']),
            models.Index(fields=['action']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['object_id']),
        ]
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
    
    def __str__(self):
        return f"{self.timestamp}: {self.user} - {self.action} on {self.model_name}"
    
    def save(self, *args, **kwargs):
        """Ensure audit logs are immutable"""
        if self.pk:
            raise ValueError("Audit logs cannot be modified")
        
        # Set username from user if available
        if self.user and not self.username:
            self.username = self.user.get_username()
            self.user_email = self.user.email
        
        super().save(*args, **kwargs)


class AuditArchive(models.Model):
    """
    Archived audit logs (for long-term storage)
    """
    
    archive_date = models.DateField()
    archive_file = models.FileField(upload_to='audit/archives/%Y/%m/')
    record_count = models.IntegerField()
    date_from = models.DateField()
    date_to = models.DateField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['-archive_date']
        verbose_name = _('Audit Archive')
        verbose_name_plural = _('Audit Archives')
    
    def __str__(self):
        return f"Archive {self.archive_date}: {self.record_count} records"


class AuditRetentionPolicy(models.Model):
    """
    Retention policy for audit logs
    """
    
    app_label = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    retention_days = models.IntegerField(default=365)
    action_retention = models.JSONField(
        default=dict,
        help_text="Per-action retention overrides"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['app_label', 'model_name']
        verbose_name = _('Audit Retention Policy')
        verbose_name_plural = _('Audit Retention Policies')
    
    def __str__(self):
        return f"{self.app_label}.{self.model_name}: {self.retention_days} days"
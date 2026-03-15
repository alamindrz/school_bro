"""
Parents App Constants
Pure constants - no dependencies
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class PortalAccessStatus:
    """Parent portal access status"""
    
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'
    PENDING = 'pending'
    
    CHOICES = [
        (ACTIVE, _('Active')),
        (INACTIVE, _('Inactive')),
        (SUSPENDED, _('Suspended')),
        (PENDING, _('Pending')),
    ]


class NotificationType:
    """Types of notifications sent to parents"""
    
    PAYMENT_RECEIPT = 'payment_receipt'
    PAYMENT_REMINDER = 'payment_reminder'
    RESULT_PUBLISHED = 'result_published'
    ATTENDANCE_ALERT = 'attendance_alert'
    EVENT_REMINDER = 'event_reminder'
    GENERAL_ANNOUNCEMENT = 'general_announcement'
    ACADEMIC_REPORT = 'academic_report'
    FEE_STRUCTURE = 'fee_structure'
    DEADLINE_REMINDER = 'deadline_reminder'
    BEHAVIOR_ALERT = 'behavior_alert'
    
    CHOICES = [
        (PAYMENT_RECEIPT, _('Payment Receipt')),
        (PAYMENT_REMINDER, _('Payment Reminder')),
        (RESULT_PUBLISHED, _('Results Published')),
        (ATTENDANCE_ALERT, _('Attendance Alert')),
        (EVENT_REMINDER, _('Event Reminder')),
        (GENERAL_ANNOUNCEMENT, _('General Announcement')),
        (ACADEMIC_REPORT, _('Academic Report')),
        (FEE_STRUCTURE, _('Fee Structure')),
        (DEADLINE_REMINDER, _('Deadline Reminder')),
        (BEHAVIOR_ALERT, _('Behavior Alert')),
    ]


class NotificationChannel:
    """How notifications are sent"""
    
    EMAIL = 'email'
    SMS = 'sms'
    PUSH = 'push'
    IN_APP = 'in_app'
    
    CHOICES = [
        (EMAIL, _('Email')),
        (SMS, _('SMS')),
        (PUSH, _('Push Notification')),
        (IN_APP, _('In-App Notification')),
    ]


class NotificationPriority:
    """Notification priority levels"""
    
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    URGENT = 'urgent'
    
    CHOICES = [
        (LOW, _('Low')),
        (NORMAL, _('Normal')),
        (HIGH, _('High')),
        (URGENT, _('Urgent')),
    ]


class RelationshipType:
    """Parent-child relationship types"""
    
    FATHER = 'father'
    MOTHER = 'mother'
    GUARDIAN = 'guardian'
    GRANDPARENT = 'grandparent'
    OTHER = 'other'
    
    CHOICES = [
        (FATHER, _('Father')),
        (MOTHER, _('Mother')),
        (GUARDIAN, _('Legal Guardian')),
        (GRANDPARENT, _('Grandparent')),
        (OTHER, _('Other')),
    ]


# Default settings
DEFAULT_NOTIFICATION_PREFERENCES = {
    NotificationType.PAYMENT_RECEIPT: [NotificationChannel.EMAIL, NotificationChannel.SMS],
    NotificationType.PAYMENT_REMINDER: [NotificationChannel.EMAIL, NotificationChannel.SMS],
    NotificationType.RESULT_PUBLISHED: [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
    NotificationType.ATTENDANCE_ALERT: [NotificationChannel.SMS, NotificationChannel.PUSH],
    NotificationType.EVENT_REMINDER: [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
    NotificationType.GENERAL_ANNOUNCEMENT: [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
    NotificationType.ACADEMIC_REPORT: [NotificationChannel.EMAIL],
    NotificationType.FEE_STRUCTURE: [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
    NotificationType.DEADLINE_REMINDER: [NotificationChannel.EMAIL, NotificationChannel.SMS],
    NotificationType.BEHAVIOR_ALERT: [NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.PUSH],
}

# Portal features by relationship
PORTAL_FEATURES = {
    RelationshipType.FATHER: ['view_results', 'view_attendance', 'view_fees', 'make_payments', 'communicate'],
    RelationshipType.MOTHER: ['view_results', 'view_attendance', 'view_fees', 'make_payments', 'communicate'],
    RelationshipType.GUARDIAN: ['view_results', 'view_attendance', 'view_fees', 'make_payments', 'communicate'],
    RelationshipType.GRANDPARENT: ['view_results', 'view_attendance'],
    RelationshipType.OTHER: ['view_results', 'view_attendance'],
}
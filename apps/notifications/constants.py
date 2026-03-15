"""
Notifications App Constants
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationType:
    """Types of notifications"""
    
    # Academic
    RESULT_PUBLISHED = 'result_published'
    REPORT_CARD_READY = 'report_card_ready'
    TERM_BEGINS = 'term_begins'
    TERM_ENDS = 'term_ends'
    
    # Financial
    PAYMENT_RECEIPT = 'payment_receipt'
    PAYMENT_REMINDER = 'payment_reminder'
    INVOICE_GENERATED = 'invoice_generated'
    WAIVER_APPROVED = 'waiver_approved'
    
    # Attendance
    ATTENDANCE_ALERT = 'attendance_alert'
    LOW_ATTENDANCE = 'low_attendance'
    
    # Administrative
    APPLICATION_STATUS = 'application_status'
    ADMISSION_OFFER = 'admission_offer'
    EVENT_REMINDER = 'event_reminder'
    GENERAL_ANNOUNCEMENT = 'general_announcement'
    
    # Staff
    LEAVE_APPROVED = 'leave_approved'
    LEAVE_REJECTED = 'leave_rejected'
    PERFORMANCE_REVIEW = 'performance_review'
    
    CHOICES = [
        # Academic
        (RESULT_PUBLISHED, _('Results Published')),
        (REPORT_CARD_READY, _('Report Card Ready')),
        (TERM_BEGINS, _('Term Begins')),
        (TERM_ENDS, _('Term Ends')),
        
        # Financial
        (PAYMENT_RECEIPT, _('Payment Receipt')),
        (PAYMENT_REMINDER, _('Payment Reminder')),
        (INVOICE_GENERATED, _('Invoice Generated')),
        (WAIVER_APPROVED, _('Waiver Approved')),
        
        # Attendance
        (ATTENDANCE_ALERT, _('Attendance Alert')),
        (LOW_ATTENDANCE, _('Low Attendance Warning')),
        
        # Administrative
        (APPLICATION_STATUS, _('Application Status Update')),
        (ADMISSION_OFFER, _('Admission Offer')),
        (EVENT_REMINDER, _('Event Reminder')),
        (GENERAL_ANNOUNCEMENT, _('General Announcement')),
        
        # Staff
        (LEAVE_APPROVED, _('Leave Approved')),
        (LEAVE_REJECTED, _('Leave Rejected')),
        (PERFORMANCE_REVIEW, _('Performance Review')),
    ]


class NotificationChannel:
    """Delivery channels"""
    
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
    """Priority levels"""
    
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


class NotificationStatus:
    """Delivery status"""
    
    PENDING = 'pending'
    SENT = 'sent'
    DELIVERED = 'delivered'
    READ = 'read'
    FAILED = 'failed'
    
    CHOICES = [
        (PENDING, _('Pending')),
        (SENT, _('Sent')),
        (DELIVERED, _('Delivered')),
        (READ, _('Read')),
        (FAILED, _('Failed')),
    ]


class RecipientType:
    """Types of recipients"""
    
    STUDENT = 'student'
    PARENT = 'parent'
    STAFF = 'staff'
    ALL_STUDENTS = 'all_students'
    ALL_PARENTS = 'all_parents'
    ALL_STAFF = 'all_staff'
    SPECIFIC_CLASS = 'specific_class'
    SPECIFIC_ROLE = 'specific_role'
    
    CHOICES = [
        (STUDENT, _('Single Student')),
        (PARENT, _('Single Parent')),
        (STAFF, _('Single Staff')),
        (ALL_STUDENTS, _('All Students')),
        (ALL_PARENTS, _('All Parents')),
        (ALL_STAFF, _('All Staff')),
        (SPECIFIC_CLASS, _('Specific Class')),
        (SPECIFIC_ROLE, _('Specific Role')),
    ]
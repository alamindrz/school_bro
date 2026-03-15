"""
Notification Template Tags
"""

from django import template
from django.utils.timesince import timesince
from django.utils import timezone

register = template.Library()


@register.filter
def notification_icon(notification_type):
    """Return icon for notification type"""
    icons = {
        'result_published': 'fa-scroll',
        'payment_receipt': 'fa-receipt',
        'payment_reminder': 'fa-clock',
        'attendance_alert': 'fa-calendar-times',
        'event_reminder': 'fa-calendar-check',
        'general_announcement': 'fa-bullhorn',
        'leave_approved': 'fa-check-circle',
        'leave_rejected': 'fa-times-circle',
    }
    return icons.get(notification_type, 'fa-bell')


@register.filter
def notification_color(notification_type):
    """Return color class for notification type"""
    colors = {
        'result_published': 'green',
        'payment_receipt': 'blue',
        'payment_reminder': 'yellow',
        'attendance_alert': 'red',
        'event_reminder': 'purple',
        'general_announcement': 'gray',
        'leave_approved': 'green',
        'leave_rejected': 'red',
    }
    return colors.get(notification_type, 'gray')


@register.simple_tag
def unread_count(recipient_type, recipient_id):
    """Get unread notification count"""
    from ..models import Notification
    return Notification.objects.filter(
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        status='pending'
    ).count()


@register.filter
def time_ago(timestamp):
    """Return human readable time ago"""
    if not timestamp:
        return ''
    return f"{timesince(timestamp, timezone.now())} ago"
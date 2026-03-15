"""
Parents Template Tags
"""

from django import template

register = template.Library()


@register.simple_tag
def notification_icon(notification_type):
    """Return icon for notification type"""
    icons = {
        'payment_receipt': 'fas fa-receipt',
        'payment_reminder': 'fas fa-clock',
        'result_published': 'fas fa-scroll',
        'attendance_alert': 'fas fa-calendar-times',
        'event_reminder': 'fas fa-calendar-check',
        'general_announcement': 'fas fa-bullhorn',
        'academic_report': 'fas fa-chart-line',
        'fee_structure': 'fas fa-file-invoice',
        'deadline_reminder': 'fas fa-hourglass-end',
        'behavior_alert': 'fas fa-exclamation-triangle',
    }
    return icons.get(notification_type, 'fas fa-bell')


@register.filter
def time_ago(timestamp):
    """Return human readable time ago"""
    from django.utils.timesince import timesince
    from django.utils.timezone import now
    
    if not timestamp:
        return ''
    
    return f"{timesince(timestamp, now())} ago"
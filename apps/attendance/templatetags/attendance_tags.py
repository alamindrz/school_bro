"""
Attendance Template Tags
"""

from django import template

register = template.Library()


@register.filter
def attendance_status_color(status):
    """Return color class for attendance status"""
    colors = {
        'present': 'green',
        'absent': 'red',
        'late': 'yellow',
        'excused': 'blue',
        'holiday': 'purple',
        'sick': 'orange',
    }
    return colors.get(status, 'gray')


@register.filter
def attendance_status_icon(status):
    """Return icon for attendance status"""
    icons = {
        'present': 'fa-check-circle',
        'absent': 'fa-times-circle',
        'late': 'fa-clock',
        'excused': 'fa-check',
        'holiday': 'fa-umbrella-beach',
        'sick': 'fa-thermometer-half',
    }
    return icons.get(status, 'fa-circle')


@register.simple_tag
def attendance_percentage(present, total):
    """Calculate attendance percentage"""
    if total == 0:
        return "0%"
    percentage = (present / total) * 100
    return f"{percentage:.1f}%"
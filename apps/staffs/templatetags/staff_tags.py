"""
Staff Template Tags
"""

from django import template

register = template.Library()


@register.filter
def staff_type_category(staff_type):
    """Return category for staff type"""
    from ..constants import STAFF_CATEGORY_MAP
    return STAFF_CATEGORY_MAP.get(staff_type, 'support')


@register.filter
def employment_status_color(status):
    """Return color for employment status"""
    colors = {
        'active': 'green',
        'on_leave': 'yellow',
        'suspended': 'red',
        'terminated': 'gray',
        'resigned': 'gray',
        'retired': 'purple',
        'probation': 'orange',
        'contract': 'blue',
    }
    return colors.get(status, 'gray')


@register.simple_tag
def years_of_service(date_employed):
    """Calculate years of service"""
    from datetime import date
    today = date.today()
    years = today.year - date_employed.year
    if today.month < date_employed.month or (today.month == date_employed.month and today.day < date_employed.day):
        years -= 1
    return years


@register.filter
def duty_post_icon(duty_post):
    """Return icon for duty post"""
    icons = {
        'form_master': 'fas fa-users',
        'housemaster': 'fas fa-home',
        'sports_master': 'fas fa-futbol',
        'club_patron': 'fas fa-users',
        'kitchen_master': 'fas fa-utensils',
        'gate_duty': 'fas fa-shield-alt',
        'lab_duty': 'fas fa-flask',
    }
    return icons.get(duty_post, 'fas fa-tasks')
"""
Admissions Template Tags
"""

from django import template

register = template.Library()


@register.filter
def application_status_color(status):
    """Return color class for application status"""
    colors = {
        'draft': 'gray',
        'submitted': 'yellow',
        'under_review': 'blue',
        'approved': 'green',
        'rejected': 'red',
        'waitlisted': 'purple',
        'enrolled': 'green',
        'cancelled': 'gray',
        'expired': 'gray',
    }
    return colors.get(status, 'gray')


@register.simple_tag
def payment_status_badge(status):
    """Return HTML for payment status badge"""
    colors = {
        'pending': 'yellow',
        'processing': 'blue',
        'completed': 'green',
        'failed': 'red',
        'refunded': 'purple',
    }
    color = colors.get(status, 'gray')
    
    return f'<span class="px-2 py-1 text-xs font-medium rounded-full bg-{color}-100 text-{color}-800">{status.title()}</span>'
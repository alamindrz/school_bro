"""
Student Template Tags
"""
from django import template
from django.utils.http import urlencode

register = template.Library()

@register.simple_tag(takes_context=True)
def remove_param(context, param_name):
    """Remove a parameter from current URL while preserving others."""
    request = context.get('request')
    if not request:
        return ''
    
    params = request.GET.copy()
    if param_name in params:
        del params[param_name]
    
    if params:
        return '?' + urlencode(params)
    return ''

@register.simple_tag
def student_status_badge(status):
    """Return HTML for status badge"""
    colors = {
        'active': 'green',
        'graduated': 'blue',
        'transferred': 'gray',
        'withdrawn': 'gray',
        'suspended': 'yellow',
        'expelled': 'red',
        'deferred': 'purple',
    }
    color = colors.get(status, 'gray')
    
    return f'<span class="px-2 py-1 text-xs font-medium rounded-full bg-{color}-100 text-{color}-800">{status.title()}</span>'


@register.inclusion_tag('students/partials/student_card.html')
def student_card(student):
    """Render student card"""
    return {'student': student}


@register.filter
def admission_year(admission_number):
    """Extract year from admission number"""
    try:
        return admission_number.split('/')[0]
    except (IndexError, AttributeError):
        return ''
"""
Corecode Template Tags
Fixed: Remove cross-app import of GradeSystem
"""

from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get dictionary item by key"""
    return dictionary.get(key) if dictionary else None


@register.filter
def status_color(status):
    """Return color class for status"""
    colors = {
        'active': 'green',
        'pending': 'yellow',
        'completed': 'green',
        'approved': 'green',
        'rejected': 'red',
        'draft': 'gray',
        'published': 'green',
        'paid': 'green',
        'overdue': 'red',
        'present': 'green',
        'absent': 'red',
        'late': 'yellow',
        'excused': 'blue',
        'sick': 'orange',
    }
    return colors.get(status, 'gray')


@register.filter
def status_icon(status):
    """Return icon for status"""
    icons = {
        'present': 'fa-check-circle',
        'absent': 'fa-times-circle',
        'late': 'fa-clock',
        'paid': 'fa-check-circle',
        'pending': 'fa-clock',
        'overdue': 'fa-exclamation-triangle',
        'approved': 'fa-check-circle',
        'rejected': 'fa-times-circle',
        'draft': 'fa-file',
        'published': 'fa-globe',
    }
    return icons.get(status, 'fa-circle')


@register.simple_tag
def grade_from_score(score):
    """
    Convert score to Nigerian grade.
    NOTE: This is a placeholder - the actual grading logic should come from results app.
    """
    if score is None:
        return '-'
    
    # Simple grade mapping (should be replaced with results app logic)
    if score >= 75:
        return 'A1'
    elif score >= 70:
        return 'B2'
    elif score >= 65:
        return 'B3'
    elif score >= 60:
        return 'C4'
    elif score >= 55:
        return 'C5'
    elif score >= 50:
        return 'C6'
    elif score >= 45:
        return 'D7'
    elif score >= 40:
        return 'E8'
    else:
        return 'F9'


@register.simple_tag
def grade_point(grade):
    """
    Get grade point for GPA calculation.
    NOTE: This is a placeholder - actual grade points should come from results app.
    """
    grade_points = {
        'A1': 8,
        'B2': 7,
        'B3': 6,
        'C4': 5,
        'C5': 4,
        'C6': 3,
        'D7': 2,
        'E8': 1,
        'F9': 0,
    }
    return grade_points.get(grade, 0)


@register.filter
def currency(value):
    """Format as Nigerian Naira"""
    try:
        return f"₦{value:,.2f}"
    except (ValueError, TypeError):
        return "₦0.00"


@register.filter
def percentage(value):
    """Format as percentage"""
    try:
        return f"{value:.1f}%"
    except (ValueError, TypeError):
        return "0%"


@register.simple_tag(takes_context=True)
def active_if(context, url_name):
    """Return 'active' class if current URL matches"""
    request = context.get('request')
    if request and request.resolver_match:
        if request.resolver_match.url_name == url_name:
            return 'active'
    return ''


@register.filter
def jsonify(obj):
    """Convert object to JSON string"""
    return mark_safe(json.dumps(obj))


@register.inclusion_tag('corecode/partials/pagination.html', takes_context=True)
def pagination(context):
    """Render pagination links"""
    return {
        'page_obj': context.get('page_obj'),
        'paginator': context.get('paginator'),
        'request': context.get('request'),
    }


@register.filter
def filesize(value):
    """Format file size human readable"""
    if not value:
        return '0 B'
    
    try:
        size = float(value)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    except (ValueError, TypeError):
        return '0 B'


@register.filter
def time_ago(value):
    """Return human readable time ago"""
    from django.utils.timesince import timesince
    from django.utils.timezone import now
    
    if not value:
        return ''
    
    try:
        return f"{timesince(value, now())} ago"
    except Exception:
        return ''


@register.simple_tag
def query_transform(request, **kwargs):
    """Transform query string with new parameters"""
    from django.http import QueryDict
    
    query_dict = QueryDict('', mutable=True)
    if request.GET:
        query_dict = request.GET.copy()
    
    for key, value in kwargs.items():
        if value is not None:
            query_dict[key] = str(value)
        else:
            query_dict.pop(key, None)
    
    return query_dict.urlencode()
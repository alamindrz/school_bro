"""
Results Template Tags
"""

from django import template
from ..constants import GradeSystem

register = template.Library()


@register.filter
def grade_color(grade):
    """Return color class for grade"""
    excellent = ['A1', 'B2', 'B3']
    good = ['C4', 'C5', 'C6']
    pass_grades = ['D7', 'E8']
    
    if grade in excellent:
        return 'green'
    elif grade in good:
        return 'blue'
    elif grade in pass_grades:
        return 'yellow'
    elif grade == 'F9':
        return 'red'
    return 'gray'


@register.simple_tag
def grade_from_score(score):
    """Convert score to Nigerian grade"""
    if score is None:
        return '-'
    
    for grade, (min_score, max_score) in GradeSystem.PERCENTAGE_RANGES.items():
        if min_score <= score <= max_score:
            return grade
    return 'F9'


@register.filter
def grade_point(grade):
    """Get grade point for GPA"""
    return GradeSystem.GRADE_POINTS.get(grade, 0)


@register.filter
def result_status_color(status):
    """Return color for result status"""
    colors = {
        'draft': 'gray',
        'pending_approval': 'yellow',
        'approved': 'blue',
        'published': 'green',
        'archived': 'gray',
    }
    return colors.get(status, 'gray')
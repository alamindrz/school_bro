from django import template

register = template.Library()

@register.filter
def format_changes(changes):
    """Format system log changes dict into readable text"""
    if not changes:
        return ""
    
    parts = []
    for key, value in changes.items():
        key = key.replace('_', ' ').title()
        if isinstance(value, dict):
            if 'old' in value and 'new' in value:
                parts.append(f"{key}: {value['old']} → {value['new']}")
            else:
                parts.append(f"{key}: {dict(value)}")
        elif isinstance(value, list):
            parts.append(f"{key}: {', '.join(str(v) for v in value)}")
        else:
            parts.append(f"{key}: {value}")
    
    return "; ".join(parts)

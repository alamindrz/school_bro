"""
Finance Template Tags
"""

from django import template

register = template.Library()


@register.filter
def invoice_status_color(status):
    """Return color class for invoice status"""
    colors = {
        'draft': 'gray',
        'pending': 'yellow',
        'partial': 'blue',
        'paid': 'green',
        'overdue': 'red',
        'cancelled': 'gray',
        'refunded': 'purple',
    }
    return colors.get(status, 'gray')


@register.filter
def payment_method_icon(method):
    """Return icon for payment method"""
    icons = {
        'cash': 'fas fa-money-bill-wave',
        'pos': 'fas fa-credit-card',
        'transfer': 'fas fa-exchange-alt',
        'paystack': 'fab fa-paystack',
        'cheque': 'fas fa-money-check',
        'waiver': 'fas fa-gift',
    }
    return icons.get(method, 'fas fa-circle')


@register.simple_tag
def format_currency(amount):
    """Format amount as Nigerian Naira"""
    try:
        return f"₦{float(amount):,.2f}"
    except (ValueError, TypeError):
        return "₦0.00"
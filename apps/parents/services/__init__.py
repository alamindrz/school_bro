"""
Parents Services
All business logic for parent portal
"""

# Local services
from .access import AccessService
from .portal import PortalService

# Re-export central notification service for convenience
from apps.notifications.services import (
    NotificationService,
    send_payment_receipt,
    send_payment_reminder,
    send_results_published,
    send_attendance_alert,
    send_application_status_update,
    send_event_reminder,
    send_leave_approved,
    send_leave_rejected,
)

__all__ = [
    'AccessService',
    'PortalService',
    'NotificationService',
    'send_payment_receipt',
    'send_payment_reminder',
    'send_results_published',
    'send_attendance_alert',
    'send_application_status_update',
    'send_event_reminder',
    'send_leave_approved',
    'send_leave_rejected',
]
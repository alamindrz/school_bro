"""
API endpoints for parent portal (AJAX/HTMX)
Uses central notifications app for notification endpoints
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
import logging

from ..services import PortalService, AccessService
from ..selectors import ChildLinkSelector, PortalDashboardSelector
from ..models import generate_device_fingerprint, ParentAccessLog
# get_client_ip is in views/portal.py, not models
from .portal import get_client_ip

# Import central notification API functions
from apps.notifications.views.api import (
    get_unread_count as central_unread_count,
    get_recent_notifications as central_recent,
    mark_as_read as central_mark_read,
    mark_all_as_read as central_mark_all_read,
    get_notification_preferences as central_prefs,
    update_notification_preferences as central_update_prefs,
)

logger = logging.getLogger(__name__)

# Re-export central notification endpoints
get_unread_count = central_unread_count
get_recent_notifications = central_recent
mark_as_read = central_mark_read
mark_all_as_read = central_mark_all_read
get_notification_preferences = central_prefs
update_notification_preferences = central_update_prefs


@never_cache
@require_http_methods(["GET"])
def children_list(request):
    """Get children list with balances"""
    session_key = request.headers.get('X-Parent-Session') or request.GET.get('session')
    if not session_key:
        return JsonResponse({'error': 'No session'}, status=401)
    
    parent = AccessService.validate_session(
        session_key, 
        request,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        device_fingerprint=generate_device_fingerprint(request)
    )
    
    if not parent:
        return JsonResponse({'error': 'Invalid session'}, status=401)
    
    children = ChildLinkSelector.get_for_parent(parent.id)
    from apps.finance.selectors import FinancialStatusSelector
    
    for child in children:
        balance = FinancialStatusSelector.get_student_balance(child['student_id'])
        child['balance'] = balance.get('total_balance', 0)
        child['has_overdue'] = balance.get('has_overdue', False)
    
    return JsonResponse({'children': children})


@never_cache
@require_http_methods(["GET"])
def student_balance(request, student_id):
    """Get student balance"""
    session_key = request.headers.get('X-Parent-Session') or request.GET.get('session')
    if not session_key:
        return JsonResponse({'error': 'No session'}, status=401)
    
    parent = AccessService.validate_session(
        session_key, 
        request,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        device_fingerprint=generate_device_fingerprint(request)
    )
    
    if not parent:
        return JsonResponse({'error': 'Invalid session'}, status=401)
    
    # Verify access
    if not PortalService.verify_child_access(parent.id, student_id, 'view_fees'):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    from apps.finance.selectors import FinancialStatusSelector
    balance = FinancialStatusSelector.get_student_balance(student_id)
    
    return JsonResponse(balance)


@never_cache
@require_http_methods(["GET"])
def dashboard_data(request):
    """Get dashboard data"""
    session_key = request.headers.get('X-Parent-Session') or request.GET.get('session')
    if not session_key:
        return JsonResponse({'error': 'No session'}, status=401)
    
    parent = AccessService.validate_session(
        session_key, 
        request,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        device_fingerprint=generate_device_fingerprint(request)
    )
    
    if not parent:
        return JsonResponse({'error': 'Invalid session'}, status=401)
    
    data = PortalDashboardSelector.get_dashboard_data(parent.id)
    return JsonResponse(data)
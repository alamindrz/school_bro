"""
API endpoints for parent portal (AJAX/HTMX)
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
import json

from ..services import PortalService, NotificationService
from ..selectors import (
    ParentProfileSelector, NotificationSelector,
    ChildLinkSelector, PortalDashboardSelector
)
from apps.finance.selectors import FinancialStatusSelector


def verify_parent_session(view_func):
    """Decorator to verify parent session for API calls"""
    def wrapper(request, *args, **kwargs):
        session_key = request.headers.get('X-Parent-Session') or request.GET.get('session')
        
        if not session_key:
            # For unread_count and recent_notifications, return empty data instead of 401
            if request.path.endswith('/unread/'):
                return JsonResponse({'count': 0})
            if request.path.endswith('/recent/'):
                return JsonResponse({'notifications': []})
            return JsonResponse({'error': 'No session provided'}, status=401)
        
        from ..services import AccessService
        parent = AccessService.validate_magic_link(session_key, request.META.get('REMOTE_ADDR'))
        
        if not parent:
            return JsonResponse({'error': 'Invalid or expired session'}, status=401)
        
        request.parent = parent
        return view_func(request, *args, **kwargs)
    
    return wrapper


@verify_parent_session
@require_http_methods(["GET"])
def unread_count(request):
    """Get unread notification count"""
    count = NotificationSelector.get_unread_count(request.parent.id)
    return JsonResponse({'count': count})


@verify_parent_session
@require_http_methods(["GET"])
def recent_notifications(request):
    """Get recent notifications"""
    limit = int(request.GET.get('limit', 5))
    notifications = NotificationSelector.get_for_parent(
        request.parent.id,
        limit=limit
    )
    return JsonResponse({'notifications': notifications})


@verify_parent_session
@require_http_methods(["GET"])
def children_list(request):
    """Get list of children with quick info"""
    children = ChildLinkSelector.get_for_parent(request.parent.id)
    
    # Enhance with financial summary
    for child in children:
        balance = FinancialStatusSelector.get_student_balance(child['student_id'])
        child['balance'] = balance['total_balance']
        child['has_overdue'] = balance['has_overdue']
    
    return JsonResponse({'children': children})


@verify_parent_session
@require_http_methods(["GET"])
def student_balance(request, student_id):
    """Get student balance information"""
    # Verify access
    if not PortalService.verify_child_access(request.parent.id, student_id, 'view_fees'):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    balance = FinancialStatusSelector.get_student_balance(student_id)
    return JsonResponse(balance)


@verify_parent_session
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    success = NotificationService.mark_as_read(notification_id, request.parent.id)
    return JsonResponse({'success': success})


@verify_parent_session
@require_http_methods(["POST"])
def mark_all_read(request):
    """Mark all notifications as read"""
    count = NotificationService.mark_all_as_read(request.parent.id)
    return JsonResponse({'count': count})


@verify_parent_session
@require_http_methods(["GET"])
def dashboard_data(request):
    """Get complete dashboard data for HTMX updates"""
    data = PortalDashboardSelector.get_dashboard_data(request.parent.id)
    return JsonResponse(data)
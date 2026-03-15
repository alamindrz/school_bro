"""
Notifications API Views - AJAX/HTMX endpoints
ARCHITECTURE COMPLIANT: Uses selectors for reads, services for writes
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json
import logging

from ..selectors import (
    NotificationSelector,
    UserPreferenceSelector,
    NotificationStatsSelector,
)
from ..services import NotificationService
from ..models import Notification
from ..constants import NotificationChannel

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def get_unread_count(request):
    """
    Get unread notification count for current user.
    USES SELECTOR: NotificationSelector
    """
    try:
        # Determine recipient type based on user
        if hasattr(request.user, 'student_profile'):
            recipient_type = 'student'
            recipient_id = request.user.student_profile.id
        elif hasattr(request.user, 'parent_profile'):
            recipient_type = 'parent'
            recipient_id = request.user.parent_profile.id
        elif hasattr(request.user, 'staff_profile'):
            recipient_type = 'staff'
            recipient_id = request.user.staff_profile.id
        else:
            recipient_type = 'staff'
            recipient_id = None
        
        count = NotificationSelector.get_unread_count(
            recipient_type=recipient_type,
            recipient_id=recipient_id
        )
        
        return JsonResponse({'count': count})
        
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        return JsonResponse({'count': 0, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def get_recent_notifications(request):
    """
    Get recent notifications for current user.
    USES SELECTOR: NotificationSelector
    """
    try:
        limit = int(request.GET.get('limit', 5))
        
        # Determine recipient type based on user
        if hasattr(request.user, 'student_profile'):
            recipient_type = 'student'
            recipient_id = request.user.student_profile.id
        elif hasattr(request.user, 'parent_profile'):
            recipient_type = 'parent'
            recipient_id = request.user.parent_profile.id
        elif hasattr(request.user, 'staff_profile'):
            recipient_type = 'staff'
            recipient_id = request.user.staff_profile.id
        else:
            recipient_type = 'staff'
            recipient_id = None
        
        notifications = NotificationSelector.list_for_recipient(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            limit=limit,
            unread_only=False
        )
        
        return JsonResponse({'notifications': notifications})
        
    except Exception as e:
        logger.error(f"Error getting recent notifications: {e}")
        return JsonResponse({'notifications': [], 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def mark_as_read(request):
    """
    Mark a notification as read.
    USES SERVICE: NotificationService
    """
    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        # Verify ownership
        notification = get_object_or_404(Notification, id=notification_id)
        
        # Check if notification belongs to user
        if not NotificationService.belongs_to_user(notification, request.user):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        NotificationService.mark_as_read(notification_id)
        
        # Get updated count
        count = NotificationSelector.get_unread_count(
            recipient_type=notification.recipient_type,
            recipient_id=notification.recipient_id
        )
        
        return JsonResponse({
            'success': True,
            'unread_count': count
        })
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def mark_all_as_read(request):
    """
    Mark all notifications as read for current user.
    USES SERVICE: NotificationService
    """
    try:
        # Determine recipient type based on user
        if hasattr(request.user, 'student_profile'):
            recipient_type = 'student'
            recipient_id = request.user.student_profile.id
        elif hasattr(request.user, 'parent_profile'):
            recipient_type = 'parent'
            recipient_id = request.user.parent_profile.id
        elif hasattr(request.user, 'staff_profile'):
            recipient_type = 'staff'
            recipient_id = request.user.staff_profile.id
        else:
            recipient_type = 'staff'
            recipient_id = None
        
        count = NotificationService.mark_all_as_read(
            recipient_type=recipient_type,
            recipient_id=recipient_id
        )
        
        return JsonResponse({
            'success': True,
            'count': count
        })
        
    except Exception as e:
        logger.error(f"Error marking all as read: {e}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def get_notification_preferences(request):
    """
    Get notification preferences for current user.
    USES SELECTOR: UserPreferenceSelector
    """
    try:
        preferences = UserPreferenceSelector.get_for_user(request.user.id)
        
        return JsonResponse({'preferences': preferences})
        
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def update_notification_preferences(request):
    """
    Update notification preferences for current user.
    USES SERVICE: NotificationService
    """
    try:
        data = json.loads(request.body)
        
        NotificationService.update_user_preferences(
            user_id=request.user.id,
            preferences=data
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@permission_required('notifications.add_notification')
@require_http_methods(["POST"])
def send_test_notification(request):
    """
    Send a test notification.
    USES SERVICE: NotificationService
    """
    try:
        data = json.loads(request.body)
        
        notification = NotificationService.send_notification(
            notification_type=data.get('notification_type', 'test'),
            title=data.get('title', 'Test Notification'),
            message=data.get('message', 'This is a test notification'),
            recipient_type='staff',
            recipient_id=request.user.staff_profile.id if hasattr(request.user, 'staff_profile') else None,
            channels=data.get('channels', [NotificationChannel.IN_APP]),
            created_by_id=request.user.id
        )
        
        return JsonResponse({
            'success': True,
            'notification_id': notification.id
        })
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@permission_required('notifications.view_notification')
@require_http_methods(["GET"])
def get_notification_stats(request):
    """
    Get notification statistics.
    USES SELECTOR: NotificationStatsSelector
    """
    try:
        days = int(request.GET.get('days', 30))
        
        stats = NotificationStatsSelector.get_detailed_stats(days=days)
        
        return JsonResponse(stats)
        
    except Exception as e:
        logger.error(f"Error getting notification stats: {e}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def check_notifications(request):
    """
    Check for new notifications (for polling).
    USES SELECTOR: NotificationSelector
    """
    try:
        last_check = request.GET.get('last_check')
        
        # Determine recipient
        if hasattr(request.user, 'student_profile'):
            recipient_type = 'student'
            recipient_id = request.user.student_profile.id
        elif hasattr(request.user, 'parent_profile'):
            recipient_type = 'parent'
            recipient_id = request.user.parent_profile.id
        elif hasattr(request.user, 'staff_profile'):
            recipient_type = 'staff'
            recipient_id = request.user.staff_profile.id
        else:
            return JsonResponse({'error': 'Unknown user type'}, status=400)
        
        # Get unread count
        unread_count = NotificationSelector.get_unread_count(
            recipient_type=recipient_type,
            recipient_id=recipient_id
        )
        
        # Get new notifications since last check
        new_notifications = []
        if last_check:
            from datetime import datetime
            last_check_dt = datetime.fromisoformat(last_check)
            
            new_notifications = NotificationSelector.list_for_recipient(
                recipient_type=recipient_type,
                recipient_id=recipient_id,
                created_after=last_check_dt,
                limit=5
            )
        
        return JsonResponse({
            'unread_count': unread_count,
            'has_new': len(new_notifications) > 0,
            'new_notifications': new_notifications[:3],  # Limit to 3
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error checking notifications: {e}")
        return JsonResponse({'error': str(e)}, status=400)
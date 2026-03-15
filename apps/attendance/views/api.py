"""
API endpoints for attendance app (AJAX/HTMX)
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from datetime import date
import json
import logging

from ..selectors import (
    AttendanceRecordSelector, AttendanceSummarySelector,
    AttendanceRegisterSelector, QRCodeSelector
)
from ..services import AttendanceService
from ..models import AttendanceRegister, QRCode
from ..exceptions import InvalidQRCodeError, DuplicateAttendanceError

logger = logging.getLogger(__name__)


@login_required
@permission_required('attendance.view_attendanceregister')
@require_http_methods(["GET"])
def daily_summary(request):
    """Get daily attendance summary via AJAX"""
    summary_date = request.GET.get('date', date.today().isoformat())
    class_id = request.GET.get('class_id')
    
    try:
        summary_date = date.fromisoformat(summary_date)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    summary = AttendanceRecordSelector.get_daily_summary(
        date=summary_date,
        class_id=class_id
    )
    
    return JsonResponse(summary)


@login_required
@permission_required('attendance.view_attendancesummary')
@require_http_methods(["GET"])
def student_summary(request, student_id):
    """Get student attendance summary via AJAX"""
    session_id = request.GET.get('session_id')
    term_id = request.GET.get('term_id')
    
    summary = AttendanceSummarySelector.get_student_summary(
        student_id=student_id,
        session_id=session_id,
        term_id=term_id
    )
    
    if not summary:
        return JsonResponse({'error': 'Summary not found'}, status=404)
    
    return JsonResponse(summary)


@login_required
@permission_required('attendance.view_attendancesummary')
@require_http_methods(["GET"])
def class_summary(request, class_id):
    """Get class attendance summary via AJAX"""
    session_id = request.GET.get('session_id')
    term_id = request.GET.get('term_id')
    
    summary = AttendanceSummarySelector.get_class_summary(
        class_id=class_id,
        session_id=session_id,
        term_id=term_id
    )
    
    return JsonResponse(summary)


@csrf_exempt
@require_http_methods(["POST"])
def process_qr_code(request):
    """
    Process QR code scan (public endpoint, but validated)
    """
    try:
        data = json.loads(request.body)
        qr_code = data.get('code')
        session_type = data.get('session_type', 'morning')
        
        if not qr_code:
            return JsonResponse({'error': 'QR code required'}, status=400)
        
        # Process check-in
        record = AttendanceService.process_qr_check_in(
            qr_code=qr_code,
            session_type=session_type
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Check-in successful for {record.student_name}',
            'student_name': record.student_name,
            'time': record.check_in_time.isoformat() if record.check_in_time else None,
        })
        
    except InvalidQRCodeError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except DuplicateAttendanceError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"QR code processing error: {e}")
        return JsonResponse({'error': 'Server error'}, status=500)


@login_required
@permission_required('attendance.view_attendanceregister')
@require_http_methods(["GET"])
def register_status(request, register_id):
    """Get register status via AJAX"""
    register = get_object_or_404(AttendanceRegister, id=register_id)
    
    return JsonResponse({
        'id': register.id,
        'is_closed': register.is_closed,
        'total_students': register.total_students,
        'present_count': register.present_count,
        'present_percentage': register.present_percentage,
        'records_count': register.records.count(),
    })
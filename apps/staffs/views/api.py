"""
API endpoints for staffs app (AJAX/HTMX)
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from datetime import date, datetime
import json
import logging

from ..models import Staff, LeaveRequest, StaffAttendance
from ..selectors import (
    StaffSelector, TeacherQualificationSelector, LeaveRequestSelector,
    StaffAttendanceSelector, PerformanceSelector
)
from ..services import StaffService, LeaveService, StaffAttendanceService

logger = logging.getLogger(__name__)


@login_required
@permission_required('staffs.view_staff')
@require_http_methods(["GET"])
def search_staff(request):
    """Search staff via AJAX"""
    query = request.GET.get('q', '')
    staff_type = request.GET.get('type', '')

    staff_list = StaffSelector.list_staff(
        staff_type=staff_type,
        search=query,
        limit=10
    )

    return JsonResponse({'staff': staff_list})


@login_required
@permission_required('staffs.view_staff')
@require_http_methods(["GET"])
def get_staff_stats(request):
    """Get staff statistics"""
    stats = StaffSelector.get_statistics()
    return JsonResponse(stats)


@login_required
@permission_required('staffs.view_leaverequest')
@require_http_methods(["GET"])
def get_pending_leaves(request):
    """Get pending leave requests"""
    leaves = LeaveRequestSelector.get_pending_requests()
    return JsonResponse({'pending_leaves': leaves})


@login_required
@permission_required('staffs.view_staffattendance')
@require_http_methods(["GET"])
def get_today_attendance(request):
    """Get today's attendance"""
    today = date.today()
    attendance = StaffAttendanceSelector.get_for_date(today)

    # Count by status
    summary = {
        'present': sum(1 for a in attendance if a['status'] == 'present'),
        'absent': sum(1 for a in attendance if a['status'] == 'absent'),
        'late': sum(1 for a in attendance if a['status'] == 'late'),
        'on_leave': sum(1 for a in attendance if a['status'] == 'on_leave'),
        'total': len(attendance),
    }

    return JsonResponse({
        'attendance': attendance,
        'summary': summary
    })


@login_required
@permission_required('staffs.view_staffattendance')
@require_http_methods(["GET"])
def get_staff_attendance(request, staff_id):
    """Get attendance for a specific staff member"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date and end_date:
        summary = StaffAttendanceSelector.get_staff_summary(
            staff_id=int(staff_id),
            start_date=date.fromisoformat(start_date),
            end_date=date.fromisoformat(end_date)
        )
        return JsonResponse(summary)

    return JsonResponse({'error': 'Date range required'}, status=400)


@login_required
@permission_required('staffs.view_subjectassignment')
@require_http_methods(["GET"])
def get_teaching_load(request, staff_id):
    """Get teaching qualifications for a staff member"""
    from ..selectors import TeacherQualificationSelector
    
    qualifications = TeacherQualificationSelector.get_for_teacher(int(staff_id))
    
    return JsonResponse({
        'qualifications': qualifications,
        'subject_count': len(qualifications),
        'primary_subject': next((q for q in qualifications if q['is_primary']), None)
    })


@login_required
@permission_required('staffs.add_staffattendance')
@require_http_methods(["POST"])
def quick_check_in(request):
    """Quick check-in via QR code or manual entry"""
    try:
        data = json.loads(request.body)
        staff_id = data.get('staff_id')
        method = data.get('method', 'manual')

        staff = Staff.objects.get(id=int(staff_id))

        attendance = StaffAttendanceService.check_in(
            staff_id=int(staff_id),
            marked_by_id=request.user.id
        )

        return JsonResponse({
            'success': True,
            'staff_name': staff.get_full_name,
            'check_in_time': attendance.check_in_time.isoformat() if attendance.check_in_time else None,
            'status': attendance.status
        })

    except Staff.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Staff not found'}, status=404)
    except Exception as e:
        logger.error(f"Attendance recording failed: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@permission_required('staffs.change_staff')
@require_http_methods(["POST"])
def update_staff_status_ajax(request):
    """Update staff status via AJAX"""
    try:
        data = json.loads(request.body)
        staff_id = data.get('staff_id')
        new_status = data.get('status')
        reason = data.get('reason', '')

        staff = StaffService.update_staff_status(
            staff_id=int(staff_id),
            new_status=new_status,
            reason=reason,
            updated_by_id=request.user.id
        )

        return JsonResponse({
            'success': True,
            'staff_id': staff.id,
            'status': staff.employment_status,
            'status_display': staff.get_employment_status_display()
        })

    except Exception as e:
        logger.error(f"Staff status update failed: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@permission_required('staffs.view_performanceevaluation')
@require_http_methods(["GET"])
def get_performance_chart(request, staff_id):
    """Get performance data for charts"""
    evaluations = PerformanceSelector.get_for_teacher(int(staff_id), limit=20)

    chart_data = {
        'labels': [e['evaluation_period'] for e in evaluations],
        'punctuality': [e['punctuality'] for e in evaluations],
        'job_knowledge': [e['job_knowledge'] for e in evaluations],
        'quality': [e['quality_of_work'] for e in evaluations],
        'communication': [e['communication'] for e in evaluations],
        'teamwork': [e['teamwork'] for e in evaluations],
        'initiative': [e['initiative'] for e in evaluations],
        'overall': [e['overall_rating'] for e in evaluations],
    }

    return JsonResponse(chart_data)


@login_required
@permission_required('staffs.view_staff')
@require_http_methods(["GET"])
def get_birthdays(request):
    """Get staff birthdays for current month"""
    from datetime import date

    today = date.today()
    staff_list = Staff.objects.filter(
        date_of_birth__month=today.month,
        employment_status=EmploymentStatus.ACTIVE
    ).order_by('date_of_birth')

    birthdays = []
    for staff in staff_list:
        birthdays.append({
            'id': staff.id,
            'name': staff.get_full_name,
            'date': staff.date_of_birth.strftime('%B %d'),
            'staff_type': staff.get_staff_type_display(),
            'department': staff.department,
        })

    return JsonResponse({'birthdays': birthdays})
    
    
@login_required
@permission_required('staffs.view_subjectassignment')
@require_http_methods(["GET"])
def get_class_form_master(request):
    """Get form master for a specific class"""
    class_id = request.GET.get('class_id')
    
    if not class_id:
        return JsonResponse({'error': 'Class ID required'}, status=400)
    
    from ..selectors import TeacherQualificationSelector
    form_master = TeacherQualificationSelector.get_form_master_for_class(int(class_id))
    
    if form_master:
        return JsonResponse({
            'form_master': {
                'id': form_master['staff_id'],
                'name': form_master['staff_name'],
                'staff_id': form_master['staff_id'],
            }
        })
    else:
        return JsonResponse({'form_master': None})
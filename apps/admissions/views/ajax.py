"""
AJAX/HTMX endpoints for admissions
"""

from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone
import json

from ..selectors import ApplicationSelector, ApplicationPaymentSelector
from ..services import ApplicationService, PaymentService
from ..models import Application
from ..constants import ApplicationStatus


@login_required
@permission_required('admissions.view_application')
@require_http_methods(["GET"])
def search_applications(request):
    """Search applications via HTMX"""
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')
    
    applications = ApplicationSelector.list_applications(
        search=query,
        status=status,
        limit=10
    )
    
    return render(request, 'admissions/partials/search_results.html', {
        'applications': applications
    })


@login_required
@permission_required('admissions.view_application')
@require_http_methods(["GET"])
def load_statistics(request):
    """Load admission statistics via HTMX"""
    session_id = request.GET.get('session_id')
    stats = ApplicationSelector.get_statistics(session_id)
    
    return render(request, 'admissions/partials/statistics.html', {
        'stats': stats
    })


@login_required
@permission_required('admissions.change_application')
@require_http_methods(["POST"])
def update_status_ajax(request):
    """Update application status via AJAX"""
    try:
        data = json.loads(request.body)
        application_id = data.get('application_id')
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        application = ApplicationService.review_application(
            application_id=application_id,
            new_status=new_status,
            review_notes=notes,
            reviewed_by_id=request.user.id
        )
        
        return JsonResponse({
            'success': True,
            'status': application.status,
            'message': f'Status updated to {application.get_status_display()}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def check_admissions_status(request):
    """Check if admissions are open"""
    from ..services import ApplicationService
    is_open = ApplicationService.is_admissions_open()
    
    return JsonResponse({
        'is_open': is_open,
        'deadline': None,  # TODO: Get from config
    })


@login_required
@permission_required('admissions.view_application')
@require_http_methods(["GET"])
def get_class_availability(request):
    """Get class availability for admissions"""
    class_id = request.GET.get('class_id')
    session_id = request.GET.get('session_id')
    
    if not class_id or not session_id:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    from ..validators import ApplicationValidator
    from apps.corecode.selectors import StudentClassSelector
    from apps.students.models import Student
    
    try:
        student_class = StudentClassSelector.get_by_id(class_id)
        if not student_class:
            return JsonResponse({'error': 'Class not found'}, status=404)
        
        # Count approved applications
        approved_count = Application.objects.filter(
            applying_for_class_id=class_id,
            applying_for_session_id=session_id,
            status__in=[ApplicationStatus.APPROVED, ApplicationStatus.ENROLLED]
        ).count()
        
        # Count enrolled students
        enrolled_count = Student.objects.filter(
            current_class_id=class_id,
            enrollment_session_id=session_id,
            status='active'
        ).count()
        
        total_taken = approved_count + enrolled_count
        available = student_class.max_students - total_taken
        
        return JsonResponse({
            'class_id': class_id,
            'class_name': student_class.display_name,
            'max_capacity': student_class.max_students,
            'approved': approved_count,
            'enrolled': enrolled_count,
            'total_taken': total_taken,
            'available': available,
            'is_full': available <= 0,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
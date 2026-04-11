"""
AJAX/HTMX endpoints for admissions
"""

from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone
import json
import logging

from ..selectors import ApplicationSelector
from ..services import ApplicationService
from ..models import Application
from ..constants import ApplicationStatus

logger = logging.getLogger(__name__)


@login_required
@permission_required('admissions.view_application', raise_exception=True)
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
@permission_required('admissions.view_application', raise_exception=True)
@require_http_methods(["GET"])
def load_statistics(request):
    """Load admission statistics via HTMX"""
    session_id = request.GET.get('session_id')
    stats = ApplicationSelector.get_statistics(session_id)
    
    return render(request, 'admissions/partials/statistics.html', {
        'stats': stats
    })


@login_required
@permission_required('admissions.change_application', raise_exception=True)
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
        logger.exception("Status update failed")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def check_admissions_status(request):
    """Check if admissions are open"""
    from ..services import ApplicationService
    is_open = ApplicationService.is_admissions_open()
    
    return JsonResponse({
        'is_open': is_open,
        'deadline': None,
    })


@login_required
@permission_required('admissions.view_application', raise_exception=True)
@require_http_methods(["GET"])
def get_class_availability(request):
    """Get class availability for admissions"""
    class_id = request.GET.get('class_id')
    
    if not class_id:
        return JsonResponse({'error': 'Class ID required'}, status=400)
    
    try:
        class_id = int(class_id)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid class ID'}, status=400)
    
    from ..validators import ApplicationValidator
    from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector
    
    # Get current session
    current_session = AcademicSessionSelector.get_current_session()
    if not current_session:
        return JsonResponse({'error': 'No active academic session'}, status=400)
    
    try:
        student_class = StudentClassSelector.get_by_id(class_id)
        if not student_class:
            return JsonResponse({'error': 'Class not found'}, status=404)
        
        # Count approved applications
        approved_count = Application.objects.filter(
            applying_for_class_id=class_id,
            applying_for_session_id=current_session.id,
            status__in=[ApplicationStatus.APPROVED, ApplicationStatus.ENROLLED]
        ).count()
        
        # Count enrolled students
        from apps.students.models import Student
        enrolled_count = Student.objects.filter(
            current_class_id=class_id,
            status='active'
        ).count()
        
        total_taken = approved_count + enrolled_count
        max_capacity = student_class.get('max_students', 40)
        available = max_capacity - total_taken
        
        return JsonResponse({
            'class_id': class_id,
            'class_name': student_class.get('display_name', 'Unknown'),
            'max_capacity': max_capacity,
            'approved': approved_count,
            'enrolled': enrolled_count,
            'total_taken': total_taken,
            'available': available,
            'is_full': available <= 0,
        })
        
    except Exception as e:
        logger.exception("Class availability check failed")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def validate_age_for_class(request):
    """Check if student age is appropriate for selected class"""
    class_id = request.GET.get('class_id')
    date_of_birth = request.GET.get('date_of_birth')
    
    if not class_id or not date_of_birth:
        return JsonResponse({'valid': True, 'message': ''})
    
    try:
        from datetime import datetime
        dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
        today = datetime.now().date()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        from apps.corecode.selectors import StudentClassSelector
        student_class = StudentClassSelector.get_by_id(int(class_id))
        
        if not student_class:
            return JsonResponse({'valid': True, 'message': ''})
        
        class_name = student_class.get('name', '')
        
        # Age ranges based on Nigerian education system
        age_ranges = {
            'NURSERY_1': (3, 4), 'NURSERY_2': (4, 5), 'NURSERY_3': (5, 6),
            'PRIMARY_1': (6, 7), 'PRIMARY_2': (7, 8), 'PRIMARY_3': (8, 9),
            'PRIMARY_4': (9, 10), 'PRIMARY_5': (10, 11), 'PRIMARY_6': (11, 12),
            'JSS_1': (12, 13), 'JSS_2': (13, 14), 'JSS_3': (14, 15),
            'SS_1': (15, 16), 'SS_2': (16, 17), 'SS_3': (17, 18),
        }
        
        min_age, max_age = age_ranges.get(class_name, (0, 30))
        
        if age < min_age:
            return JsonResponse({
                'valid': False,
                'message': f'Student is {age} years old. Minimum age for this class is {min_age}.'
            })
        elif age > max_age:
            return JsonResponse({
                'valid': False,
                'message': f'Student is {age} years old. Maximum age for this class is {max_age}.'
            })
        
        return JsonResponse({'valid': True, 'message': f'✓ Age {age} is appropriate for this class.'})
        
    except Exception as e:
        return JsonResponse({'valid': True, 'message': ''})


@login_required
@require_http_methods(["GET"])
def get_staff_children(request):
    """Get existing children for staff member to copy from"""
    from apps.students.models import Student
    from apps.parents.models import ParentProfile, ChildLink
    from apps.staffs.models import Staff
    
    try:
        staff = Staff.objects.get(user=request.user)
        
        # Find parent profile linked to this staff
        parent = ParentProfile.objects.filter(email=staff.email).first()
        
        if not parent:
            return JsonResponse({'children': []})
        
        # Get all children linked to this parent
        children = ChildLink.objects.filter(parent=parent)
        
        result = []
        for child in children:
            student = Student.objects.filter(id=child.student_id).first()
            if student:
                result.append({
                    'id': student.id,
                    'name': student.get_full_name,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'class': child.student_class,
                    'class_id': student.current_class_id,
                })
        
        return JsonResponse({'children': result})
        
    except Exception as e:
        return JsonResponse({'children': [], 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def get_sibling_details(request):
    """Get sibling details for copying information"""
    sibling_id = request.GET.get('sibling_id')
    
    if not sibling_id:
        return JsonResponse({'success': False, 'error': 'No sibling ID provided'})
    
    from apps.students.models import Student
    from apps.parents.models import ParentProfile, ChildLink
    from apps.staffs.models import Staff
    
    try:
        student = Student.objects.get(id=int(sibling_id))
        
        # Find parent linked to this student
        child_link = ChildLink.objects.filter(student_id=student.id).first()
        
        if child_link:
            parent = child_link.parent
            return JsonResponse({
                'success': True,
                'guardian_first_name': parent.first_name,
                'guardian_last_name': parent.last_name,
                'guardian_email': parent.email,
                'guardian_phone': parent.phone,
                'guardian_address': parent.address,
                'last_name': student.last_name,
            })
        
        return JsonResponse({'success': False, 'error': 'No parent found'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
"""
Student AJAX Views - HTMX and JSON endpoints for student data
ARCHITECTURE COMPLIANT: Uses selectors for all data access
"""

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import models
import json
import logging

from ..selectors import StudentSelector, GuardianSelector, StudentHistorySelector
from ..models import Student
from ..forms import StudentSearchForm
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector

logger = logging.getLogger(__name__)


@login_required
@permission_required('students.view_student')
@require_http_methods(["GET"])
def search_students(request):
    """
    AJAX endpoint for searching students.
    Returns JSON results for autocomplete.
    """
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'students': []})
    
    # Use selector to search students
    students = StudentSelector.search_students(query=query, limit=10)
    
    return JsonResponse({
        'students': students
    })


@login_required
@permission_required('students.view_student')
@require_http_methods(["GET"])
def search_students_htmx(request):
    """
    HTMX endpoint for searching students.
    Returns HTML partial for dropdown results.
    """
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return HttpResponse('<div class="p-2 text-gray-500">Type at least 2 characters...</div>')
    
    # Use selector to search students
    students = StudentSelector.search_students(query=query, limit=10)
    
    return render(request, 'students/partials/search_results.html', {
        'students': students,
        'query': query
    })


@login_required
@permission_required('students.view_student')
@require_http_methods(["GET"])
def get_student_details(request):
    """
    AJAX endpoint to get detailed student information by ID.
    """
    student_id = request.GET.get('id')
    
    if not student_id:
        return JsonResponse({'error': 'Student ID required'}, status=400)
    
    try:
        student_id = int(student_id)
    except ValueError:
        return JsonResponse({'error': 'Invalid student ID'}, status=400)
    
    # Use selector to get student data
    student = StudentSelector.get_by_id(student_id)
    
    if not student:
        return JsonResponse({'error': 'Student not found'}, status=404)
    
    return JsonResponse({
        'student': student
    })


@login_required
@permission_required('students.view_student')
@require_http_methods(["GET"])
def get_student_quick_info(request):
    """
    HTMX endpoint to get quick student info card.
    """
    student_id = request.GET.get('id')
    
    if not student_id:
        return HttpResponse('<div class="text-red-500">Student ID required</div>')
    
    try:
        student_id = int(student_id)
    except ValueError:
        return HttpResponse('<div class="text-red-500">Invalid student ID</div>')
    
    # Use selector to get student data
    student = StudentSelector.get_by_id(student_id)
    
    if not student:
        return HttpResponse('<div class="text-red-500">Student not found</div>')
    
    return render(request, 'students/partials/student_quick_info.html', {
        'student': student
    })


@login_required
@permission_required('students.view_student')
@require_http_methods(["GET"])
def filter_students(request):
    """
    HTMX endpoint for advanced filtering of students.
    Returns HTML table of filtered results.
    """
    form = StudentSearchForm(request.GET)
    
    if form.is_valid():
        search_params = form.get_search_params()
        students = StudentSelector.search_students(
            query=search_params.get('search', ''),
            class_id=search_params.get('class_id'),
            status=search_params.get('status'),
            gender=search_params.get('gender'),
            session_id=search_params.get('session_id'),
            limit=50
        )
    else:
        students = []
    
    return render(request, 'students/partials/filter_results.html', {
        'students': students,
        'total': len(students)
    })


@login_required
@permission_required('students.view_student')
@require_http_methods(["GET"])
def get_class_students(request):
    """
    AJAX endpoint to get students in a specific class.
    """
    class_id = request.GET.get('class_id')
    session_id = request.GET.get('session_id')
    
    if not class_id:
        return JsonResponse({'error': 'Class ID required'}, status=400)
    
    try:
        class_id = int(class_id)
        if session_id:
            session_id = int(session_id)
    except ValueError:
        return JsonResponse({'error': 'Invalid ID format'}, status=400)
    
    # Use selector to get class students
    students = StudentSelector.get_class_students(
        class_id=class_id,
        academic_session_id=session_id,
        include_inactive=False
    )
    
    return JsonResponse({
        'class_id': class_id,
        'students': students,
        'count': len(students)
    })


@login_required
@permission_required('students.view_student')
@require_http_methods(["GET"])
def get_student_counts(request):
    """
    AJAX endpoint to get student counts by class.
    """
    session_id = request.GET.get('session_id')
    
    if session_id:
        try:
            session_id = int(session_id)
        except ValueError:
            session_id = None
    
    # Use selector to get counts
    counts = StudentSelector.get_student_counts_by_class(academic_session_id=session_id)
    
    return JsonResponse({
        'class_counts': counts,
        'total': sum(c['student_count'] for c in counts)
    })


@login_required
@permission_required('students.view_student')
@require_http_methods(["GET"])
def get_student_timeline(request):
    """
    AJAX endpoint to get student history timeline.
    """
    student_id = request.GET.get('student_id')
    limit = request.GET.get('limit', 20)
    
    if not student_id:
        return JsonResponse({'error': 'Student ID required'}, status=400)
    
    try:
        student_id = int(student_id)
        limit = int(limit)
    except ValueError:
        return JsonResponse({'error': 'Invalid ID format'}, status=400)
    
    # Use selector to get timeline
    timeline = StudentHistorySelector.get_student_timeline(
        student_id=student_id,
        limit=limit
    )
    
    return JsonResponse({
        'student_id': student_id,
        'timeline': timeline,
        'count': len(timeline)
    })


@login_required
@permission_required('students.view_student')
@require_http_methods(["GET"])
def check_admission_number(request):
    """
    AJAX endpoint to check if an admission number is available.
    Used during student creation/editing.
    """
    admission_number = request.GET.get('admission_number')
    exclude_id = request.GET.get('exclude_id')
    
    if not admission_number:
        return JsonResponse({'available': False, 'error': 'Admission number required'})
    
    # Check if admission number exists
    queryset = Student.objects.filter(admission_number=admission_number)
    
    if exclude_id:
        try:
            queryset = queryset.exclude(id=int(exclude_id))
        except ValueError:
            pass
    
    exists = queryset.exists()
    
    return JsonResponse({
        'admission_number': admission_number,
        'available': not exists,
        'exists': exists
    })


@login_required
@permission_required('students.view_student')
@require_http_methods(["GET"])
def get_filter_options(request):
    """
    HTMX endpoint to get filter options dynamically.
    Returns HTML for filter dropdowns.
    """
    filter_type = request.GET.get('type')
    
    if filter_type == 'classes':
        classes = StudentClassSelector.get_all_classes(active_only=True)
        return render(request, 'students/partials/filter_classes.html', {
            'classes': classes
        })
    
    elif filter_type == 'sessions':
        sessions = AcademicSessionSelector.list_sessions(include_past=False)
        return render(request, 'students/partials/filter_sessions.html', {
            'sessions': sessions
        })
    
    elif filter_type == 'status':
        from ..constants import StudentStatus
        return render(request, 'students/partials/filter_status.html', {
            'statuses': StudentStatus.CHOICES
        })
    
    return HttpResponse('')


@login_required
@permission_required('students.view_student')
@require_http_methods(["GET"])
def export_students(request):
    """
    Export filtered students as CSV.
    """
    import csv
    from django.http import HttpResponse
    
    # Get filter parameters
    search = request.GET.get('search', '')
    class_id = request.GET.get('class_id')
    status = request.GET.get('status')
    gender = request.GET.get('gender')
    session_id = request.GET.get('session_id')
    
    # Get filtered students
    students = StudentSelector.search_students(
        query=search,
        class_id=class_id,
        status=status,
        gender=gender,
        session_id=session_id,
        limit=5000  # Reasonable limit for export
    )
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="students_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write headers
    writer.writerow([
        'Admission Number', 'Full Name', 'First Name', 'Last Name', 'Middle Name',
        'Gender', 'Date of Birth', 'Age', 'Email', 'Phone', 'Address', 'City',
        'State of Origin', 'Current Class', 'Status', 'Enrollment Date'
    ])
    
    # Write data
    for student in students:
        writer.writerow([
            student.get('admission_number', ''),
            student.get('full_name', ''),
            student.get('first_name', ''),
            student.get('last_name', ''),
            student.get('middle_name', ''),
            student.get('gender', ''),
            student.get('date_of_birth', ''),
            student.get('age', ''),
            student.get('email', ''),
            student.get('phone', ''),
            student.get('address', ''),
            student.get('city', ''),
            student.get('state_of_origin', ''),
            student.get('current_class', {}).get('display_name', '') if student.get('current_class') else '',
            student.get('status_display', ''),
            student.get('enrollment_date', ''),
        ])
    
    return response


@login_required
@permission_required('students.view_student')
@require_http_methods(["POST"])
def bulk_action(request):
    """
    Handle bulk actions on selected students.
    """
    action = request.POST.get('action')
    student_ids = request.POST.getlist('student_ids', [])
    
    if not student_ids:
        return JsonResponse({'error': 'No students selected'}, status=400)
    
    try:
        student_ids = [int(id) for id in student_ids]
    except ValueError:
        return JsonResponse({'error': 'Invalid student IDs'}, status=400)
    
    if action == 'export_selected':
        # Export selected students
        import csv
        from django.http import HttpResponse
        
        students = []
        for student_id in student_ids:
            student = StudentSelector.get_by_id(student_id)
            if student:
                students.append(student)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="selected_students_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Admission Number', 'Full Name', 'Email', 'Phone', 'Class', 'Status'])
        
        for student in students:
            writer.writerow([
                student.get('admission_number', ''),
                student.get('full_name', ''),
                student.get('email', ''),
                student.get('phone', ''),
                student.get('current_class', {}).get('display_name', '') if student.get('current_class') else '',
                student.get('status_display', ''),
            ])
        
        return response
    
    elif action == 'update_status':
        new_status = request.POST.get('status')
        if not new_status:
            return JsonResponse({'error': 'Status required'}, status=400)
        
        from ..services import StudentService
        results = {
            'success': [],
            'failed': []
        }
        
        for student_id in student_ids:
            try:
                student = StudentService.update_student_status(
                    student_id=student_id,
                    new_status=new_status,
                    reason="Bulk status update",
                    performed_by_id=request.user.id
                )
                results['success'].append(student_id)
            except Exception as e:
                results['failed'].append({
                    'id': student_id,
                    'error': str(e)
                })
        
        return JsonResponse(results)
    
    return JsonResponse({'error': 'Invalid action'}, status=400)
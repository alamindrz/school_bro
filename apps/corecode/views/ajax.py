"""
AJAX/HTMX Views for Corecode
Handles dynamic content loading without page refresh
"""

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
import json

from ..selectors import (
    AcademicSessionSelector,
    AcademicTermSelector,
    StudentClassSelector,
    SiteConfigSelector,
    SystemLogSelector
)
from ..services import SystemLogService
from ..models import SystemLog

@login_required
@require_http_methods(["GET"])
def search_classes(request):
    """Search classes via HTMX"""
    query = request.GET.get('q', '')
    classes = StudentClassSelector.search_classes(query)
    
    return render(request, 'corecode/partials/class_search_results.html', {
        'classes': classes[:10]
    })


@login_required
@require_http_methods(["GET"])
def load_term_details(request):
    """Load term details via HTMX"""
    term_id = request.GET.get('term_id')
    if term_id:
        from ..models import AcademicTerm
        try:
            term = AcademicTerm.objects.select_related('session').get(id=term_id)
            return JsonResponse({
                'success': True,
                'data': {
                    'id': term.id,
                    'name': term.name,
                    'session': term.session.name,
                    'term': term.get_term_display(),
                    'start_date': term.start_date.isoformat(),
                    'end_date': term.end_date.isoformat(),
                    'is_current': term.is_current,
                }
            })
        except AcademicTerm.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Term not found'})
    
    return JsonResponse({'success': False, 'error': 'No term ID provided'})


@login_required
@staff_member_required
@require_http_methods(["POST"])
def update_config_ajax(request):
    """Update site configuration via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
    
    try:
        data = json.loads(request.body)
        key = data.get('key')
        value = data.get('value')
        
        if not key:
            return JsonResponse({'success': False, 'error': 'Key is required'})
        
        from ..services import SiteConfigService
        SiteConfigService.set_config(
            key=key,
            value=value,
            user=request.user,
            description=f"Updated via AJAX on {timezone.now()}"
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Configuration {key} updated successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def load_recent_logs(request):
    """Load recent system logs via HTMX"""
    limit = int(request.GET.get('limit', 10))
    logs = SystemLogSelector.get_recent_actions(limit)
    
    return render(request, 'corecode/partials/recent_logs.html', {
        'logs': logs
    })


@login_required
@require_http_methods(["GET"])
def check_session_status(request):
    """Check current academic session status"""
    current_session = AcademicSessionSelector.get_current_session()
    current_term = AcademicTermSelector.get_current_term()
    
    return JsonResponse({
        'has_session': current_session is not None,
        'has_term': current_term is not None,
        'session_name': current_session.name if current_session else None,
        'term_name': current_term.get_term_display() if current_term else None,
        'term_dates': {
            'start': current_term.start_date.isoformat() if current_term else None,
            'end': current_term.end_date.isoformat() if current_term else None,
        } if current_term else None
    })


@login_required
@require_http_methods(["GET"])
def get_class_capacity(request):
    """Get class capacity information via HTMX"""
    class_id = request.GET.get('class_id')
    if not class_id:
        return HttpResponse("Please select a class")
    
    try:
        from ..models import StudentClass
        student_class = StudentClass.objects.get(id=class_id)
        
        # Get current enrollment count
        from apps.students.models import Student
        enrolled = Student.objects.filter(
            current_class=student_class,
            status='active'
        ).count()
        
        return render(request, 'corecode/partials/class_capacity.html', {
            'class_obj': student_class,
            'enrolled': enrolled,
            'available': student_class.max_students - enrolled,
            'percentage': (enrolled / student_class.max_students) * 100 if student_class.max_students > 0 else 0
        })
    except StudentClass.DoesNotExist:
        return HttpResponse("Class not found")


@login_required
@require_http_methods(["GET"])
def quick_stats(request):
    """Quick statistics dashboard component"""
    from apps.students.models import Student
    from apps.staffs.models import Staff
    
    total_students = Student.objects.count()
    active_students = Student.objects.filter(status='active').count()
    total_staff = Staff.objects.count() if hasattr(Staff, 'objects') else 0
    
    current_term = AcademicTermSelector.get_current_term()
    
    # Get total classes
    from ..models import StudentClass
    total_classes = StudentClass.objects.filter(is_active=True).count()
    
    return render(request, 'corecode/partials/quick_stats.html', {
        'total_students': total_students,
        'active_students': active_students,
        'total_staff': total_staff,
        'total_classes': total_classes,
        'current_term': current_term.name if current_term else 'Not set',
        'completion_percentage': 85  # Placeholder - calculate from actual data
    })
    


@login_required
def load_lgas(request):
    """
    HTMX endpoint to load LGAs for selected state.
    """
    state = request.GET.get('state')
    
    if not state:
        return HttpResponse("")
    
    lgas = NigeriaDataService.get_lgas(state)
    
    return render(request, 'corecode/partials/lga_options.html', {
        'lgas': lgas
    })


@login_required
def search_location(request):
    """
    Search for states or LGAs.
    """
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    results = NigeriaDataService.search_location(query)
    
    return JsonResponse({'results': results})
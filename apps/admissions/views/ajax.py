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



@require_http_methods(["GET"])
def get_class_availability(request):
    """Get class availability for admissions - Public endpoint (no login required)"""
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
        from ..models import Application
        from ..constants import ApplicationStatus
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





@login_required
@require_http_methods(["GET"])
def get_application_payment_status(request):
    """Get payment status for an application (from apps.finance)"""
    application_id = request.GET.get('application_id')
    
    if not application_id:
        return JsonResponse({'error': 'Application ID required'}, status=400)
    
    try:
        application = Application.objects.get(id=application_id)
        
        if not application.invoice_id:
            return JsonResponse({
                'has_invoice': False,
                'payment_completed': False,
                'message': 'No invoice found'
            })
        
        # Get invoice from apps.finance
        from apps.finance.selectors import InvoiceSelector
        invoice = InvoiceSelector.get_by_id(application.invoice_id)
        
        if invoice:
            return JsonResponse({
                'has_invoice': True,
                'invoice_id': application.invoice_id,
                'invoice_number': invoice.get('invoice_number'),
                'amount': invoice.get('total'),
                'paid_amount': invoice.get('amount_paid'),
                'balance': invoice.get('balance'),
                'status': invoice.get('status'),
                'status_display': invoice.get('status_display'),
                'payment_completed': invoice.get('status') == 'paid',
            })
        else:
            return JsonResponse({
                'has_invoice': True,
                'invoice_id': application.invoice_id,
                'payment_completed': False,
                'message': 'Invoice not found in finance system'
            })
            
    except Application.DoesNotExist:
        return JsonResponse({'error': 'Application not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
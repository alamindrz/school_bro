"""
AJAX/HTMX endpoints for finance
"""

from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from decimal import Decimal
import json
import logging

from ..selectors import (
    InvoiceSelector, PaymentSelector, FeeStructureSelector,
    FinancialStatusSelector
)
from ..services import InvoiceService, PaymentService, ReportService
from ..models import Invoice, Payment
from ..constants import InvoiceStatus

logger = logging.getLogger(__name__)


@login_required
@permission_required('finance.view_invoice')
@require_http_methods(["GET"])
def search_invoices(request):
    """Search invoices via HTMX"""
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')
    
    invoices = InvoiceSelector.list_invoices(
        search=query,
        status=status,
        limit=10
    )
    
    return render(request, 'finance/partials/search_results.html', {
        'invoices': invoices
    })


@login_required
@permission_required('finance.view_invoice')
@require_http_methods(["GET"])
def load_statistics(request):
    """Load financial statistics via HTMX"""
    session_id = request.GET.get('session_id')
    stats = InvoiceSelector.get_statistics(session_id)
    
    return render(request, 'finance/partials/statistics.html', {
        'stats': stats
    })


@login_required
@permission_required('finance.view_invoice')
@require_http_methods(["GET"])
def get_student_balance(request):
    """Get student balance via AJAX"""
    student_id = request.GET.get('student_id')
    
    if not student_id:
        return JsonResponse({'error': 'Student ID required'}, status=400)
    
    balance = InvoiceSelector.get_student_balance(student_id)
    return JsonResponse(balance)


@login_required
@permission_required('finance.view_invoice')
@require_http_methods(["GET"])
def check_exam_clearance(request):
    """Check if student is cleared for exams"""
    student_id = request.GET.get('student_id')
    
    if not student_id:
        return JsonResponse({'error': 'Student ID required'}, status=400)
    
    clearance = FinancialStatusSelector.is_student_cleared_for_exams(student_id)
    return JsonResponse(clearance)


@login_required
@permission_required('finance.view_feestructure')
@require_http_methods(["GET"])
def get_fee_structure(request):
    """Get fee structure for a class"""
    class_id = request.GET.get('class_id')
    session_id = request.GET.get('session_id')
    
    if not class_id:
        return JsonResponse({'error': 'Class ID required'}, status=400)
    
    fees = FeeStructureSelector.get_for_class(
        class_id=class_id,
        session_id=session_id
    )
    
    return JsonResponse({'fees': fees})


@login_required
@permission_required('finance.view_invoice')
@require_http_methods(["GET"])
def get_invoice_details(request):
    """Get invoice details for quick view"""
    invoice_id = request.GET.get('invoice_id')
    
    if not invoice_id:
        return JsonResponse({'error': 'Invoice ID required'}, status=400)
    
    invoice = InvoiceSelector.get_by_id(invoice_id)
    if not invoice:
        return JsonResponse({'error': 'Invoice not found'}, status=404)
    
    return JsonResponse(invoice)


@login_required
@permission_required('finance.change_invoice')
@require_http_methods(["POST"])
def update_invoice_status_ajax(request):
    """Update invoice status via AJAX"""
    try:
        data = json.loads(request.body)
        invoice_id = data.get('invoice_id')
        new_status = data.get('status')
        
        invoice = InvoiceService.update_invoice_status(
            invoice_id=invoice_id,
            new_status=new_status,
            updated_by_id=request.user.id
        )
        
        return JsonResponse({
            'success': True,
            'status': invoice.status,
            'status_display': invoice.get_status_display(),
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permission_required('finance.view_report')
@require_http_methods(["GET"])
def get_revenue_chart_data(request):
    """Get revenue data for charts"""
    session_id = request.GET.get('session_id')
    
    revenue = ReportService.get_revenue_report(session_id)
    
    # Format for charts
    chart_data = {
        'monthly': [
            {'month': item['month'], 'total': item['total']}
            for item in revenue['monthly']
        ],
        'by_method': [
            {'method': item['method_display'], 'total': item['total']}
            for item in revenue['by_payment_method']
        ],
        'by_class': [
            {'class': item['class_name'], 'total': item['total']}
            for item in revenue['by_class']
        ],
    }
    
    return JsonResponse(chart_data)


@login_required
@permission_required('finance.view_invoice')
@require_http_methods(["GET"])
def get_outstanding_chart_data(request):
    """Get outstanding data for charts"""
    session_id = request.GET.get('session_id')
    
    outstanding = ReportService.get_outstanding_report(session_id)
    
    chart_data = {
        'by_class': [
            {
                'class': item['class_name'],
                'total': item['total'],
                'student_count': item['student_count']
            }
            for item in outstanding['by_class']
        ],
        'aging': outstanding['aging'] if 'aging' in outstanding else {},
    }
    
    return JsonResponse(chart_data)


@login_required
@permission_required('finance.view_payment')
@require_http_methods(["GET"])
def verify_payment_status(request):
    """Verify payment status with Paystack"""
    reference = request.GET.get('reference')
    
    if not reference:
        return JsonResponse({'error': 'Reference required'}, status=400)
    
    try:
        # Check if payment exists in our system
        payment = PaymentSelector.get_by_gateway_ref(reference)
        
        if payment:
            return JsonResponse({
                'verified': True,
                'status': payment['status_code'],
                'payment': payment
            })
        
        # Verify with Paystack
        result = PaymentService.verify_paystack_payment(reference)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'verified': False, 'error': str(e)})


@login_required
@permission_required('finance.add_payment')
@require_http_methods(["POST"])
def calculate_partial_payment(request):
    """Calculate partial payment allocation"""
    try:
        data = json.loads(request.body)
        invoice_ids = data.get('invoice_ids', [])
        amount = Decimal(str(data.get('amount', 0)))
        allocation = data.get('allocation', 'even')
        
        invoices = Invoice.objects.filter(
            id__in=invoice_ids,
            balance__gt=0
        ).order_by('due_date')
        
        result = []
        remaining = amount
        
        if allocation == 'even' and invoices:
            per_invoice = amount / len(invoices)
            for invoice in invoices:
                pay_amount = min(per_invoice, invoice.balance)
                result.append({
                    'invoice_id': invoice.id,
                    'invoice_number': invoice.invoice_number,
                    'balance': float(invoice.balance),
                    'suggested': float(pay_amount),
                    'will_be_paid': pay_amount > 0,
                })
                remaining -= pay_amount
        else:
            for invoice in invoices:
                pay_amount = min(invoice.balance, remaining)
                if pay_amount > 0:
                    result.append({
                        'invoice_id': invoice.id,
                        'invoice_number': invoice.invoice_number,
                        'balance': float(invoice.balance),
                        'suggested': float(pay_amount),
                        'will_be_paid': True,
                    })
                    remaining -= pay_amount
        
        return JsonResponse({
            'allocations': result,
            'remaining': float(remaining),
            'total_invoiced': float(amount),
            'total_allocated': float(amount - remaining),
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@permission_required('finance.view_feewaiver')
@require_http_methods(["GET"])
def get_pending_waivers(request):
    """Get pending waiver requests"""
    from ..models import FeeWaiver
    
    waivers = FeeWaiver.objects.filter(
        status='pending'
    ).select_related('invoice', 'requested_by').order_by('-requested_at')[:10]
    
    data = []
    for w in waivers:
        data.append({
            'id': w.id,
            'invoice_number': w.invoice.invoice_number,
            'student_name': w.invoice.student_name,
            'amount': float(w.amount),
            'reason': w.reason,
            'requested_by': w.requested_by.get_full_name() if w.requested_by else None,
            'requested_at': w.requested_at.isoformat(),
        })
    
    return JsonResponse({'pending_waivers': data})
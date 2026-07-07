"""
Staff views for finance management
"""

from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, View, FormView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
import csv
import logging

from ..models import Invoice, Payment, FeeStructure, FeeWaiver
from ..selectors import (
    InvoiceSelector, PaymentSelector, FeeStructureSelector,
    FinancialStatusSelector
)
from ..services import InvoiceService, PaymentService, WaiverService, ReportService
from ..constants import InvoiceStatus, PaymentMethod, FeeType
from ..exceptions import (
    InvoiceNotFoundError, InvalidInvoiceStatusError,
    PaymentError, WaiverError, WaiverLimitExceededError
)

from apps.corecode.selectors import (
    StudentClassSelector, AcademicSessionSelector, AcademicTermSelector
)
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog
from apps.students.selectors import StudentSelector

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Finance dashboard with key metrics"""
    template_name = 'finance/pages/dashboard.html'
    permission_required = 'finance.view_invoice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current session
        current_session = AcademicSessionSelector.get_current_session()
        session_id = current_session.id if current_session else None
        
        # Get statistics
        context['stats'] = InvoiceSelector.get_statistics(session_id)
        
        # Get outstanding report
        context['outstanding'] = ReportService.get_outstanding_report(session_id)
        
        # Get collection efficiency
        context['efficiency'] = ReportService.get_collection_efficiency(session_id)
        
        # Recent transactions
        context['recent_payments'] = PaymentSelector.list_payments(limit=10)
        
        # Overdue invoices
        context['overdue_invoices'] = InvoiceSelector.list_invoices(
            overdue_only=True,
            limit=5
        )
        
        # Pending waivers count
        context['pending_waivers'] = WaiverService.get_pending_waivers_count()
        
        return context


class InvoiceListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List all invoices with filtering"""
    template_name = 'finance/pages/invoice_list.html'
    context_object_name = 'invoices'
    permission_required = 'finance.view_invoice'
    paginate_by = 25
    
    def get_queryset(self):
        """Get filtered queryset"""
        student_id = self.request.GET.get('student_id')
        status = self.request.GET.get('status')
        session_id = self.request.GET.get('session_id')
        term_id = self.request.GET.get('term_id')
        class_id = self.request.GET.get('class_id')
        fee_type = self.request.GET.get('fee_type')
        search = self.request.GET.get('search')
        overdue_only = self.request.GET.get('overdue') == 'true'
        
        if student_id:
            # Single student view
            return InvoiceSelector.list_invoices(
                student_id=student_id,
                limit=100
            )
        
        return InvoiceSelector.list_invoices(
            status=status,
            session_id=session_id,
            term_id=term_id,
            class_id=class_id,
            fee_type=fee_type,
            overdue_only=overdue_only,
            search=search
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get student if specified
        student_id = self.request.GET.get('student_id')
        if student_id:
            context['student'] = StudentSelector.get_by_id(student_id)
        
        context['status_choices'] = InvoiceStatus.CHOICES
        context['fee_type_choices'] = FeeType.CHOICES
        context['classes'] = StudentClassSelector.get_all_classes()
        context['sessions'] = AcademicSessionSelector.list_sessions(limit=5)
        
        # Get current session's terms
        current_session = AcademicSessionSelector.get_current_session()
        if current_session:
            from apps.corecode.selectors import AcademicTermSelector
            context['terms'] = AcademicTermSelector.get_terms_for_session(current_session.id)
        
        # Preserve filter values
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_session'] = self.request.GET.get('session_id', '')
        context['selected_term'] = self.request.GET.get('term_id', '')
        context['selected_class'] = self.request.GET.get('class_id', '')
        context['selected_fee_type'] = self.request.GET.get('fee_type', '')
        context['search_query'] = self.request.GET.get('search', '')
        context['overdue_only'] = self.request.GET.get('overdue') == 'true'
        
        return context


class InvoiceDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detailed invoice view"""
    model = Invoice
    template_name = 'finance/pages/invoice_detail.html'
    context_object_name = 'invoice'
    permission_required = 'finance.view_invoice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invoice_data'] = InvoiceSelector.get_by_id(self.object.id)
        context['student'] = StudentSelector.get_by_id(self.object.student_id)
        return context


class InvoiceCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create a single invoice"""
    model = Invoice
    template_name = 'finance/pages/invoice_form.html'
    fields = [
        'student_id', 'student_name', 'student_class', 'fee_type',
        'description', 'subtotal', 'due_date', 'academic_session', 'academic_term'
    ]
    permission_required = 'finance.add_invoice'
    success_url = reverse_lazy('finance:invoice_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Limit choices using selectors - NO DIRECT MODEL ACCESS
        from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector, AcademicTermSelector
        
        # Student class choices - using selector
        form.fields['student_class'].queryset = StudentClassSelector.get_queryset_for_forms(active_only=True)
        
        # Academic session choices - using selector instead of direct model access
        form.fields['academic_session'].queryset = AcademicSessionSelector.get_queryset_for_forms(active_only=True)
        
        # Make student fields read-only if student_id provided
        student_id = self.request.GET.get('student_id')
        if student_id:
            from apps.students.selectors import StudentSelector
            student = StudentSelector.get_by_id(student_id)
            if student:
                form.fields['student_id'].initial = student_id
                form.fields['student_id'].widget.attrs['readonly'] = True
                form.fields['student_name'].initial = student['full_name']
                form.fields['student_name'].widget.attrs['readonly'] = True
                form.fields['student_class'].initial = student['current_class']['id']
                form.fields['student_class'].widget.attrs['disabled'] = True
                
                # Also pre-select academic session if available
                from apps.corecode.selectors import AcademicSessionSelector
                current_session = AcademicSessionSelector.get_current_session()
                if current_session:
                    form.fields['academic_session'].initial = current_session.id
        
        return form
    
    def form_valid(self, form):
        try:
            from .services import InvoiceService
            invoice = InvoiceService.create_invoice(
                student_id=form.cleaned_data['student_id'],
                student_name=form.cleaned_data['student_name'],
                class_id=form.cleaned_data['student_class'].id,
                fee_type=form.cleaned_data['fee_type'],
                amount=form.cleaned_data['subtotal'],
                description=form.cleaned_data['description'],
                session_id=form.cleaned_data['academic_session'].id,
                term_id=form.cleaned_data['academic_term'].id if form.cleaned_data['academic_term'] else None,
                due_date=form.cleaned_data['due_date'].isoformat() if form.cleaned_data['due_date'] else None,
                created_by_id=self.request.user.id
            )
            
            messages.success(
                self.request,
                f'Invoice {invoice.invoice_number} created successfully.'
            )
            
            return redirect('finance:invoice_detail', pk=invoice.id)
            
        except Exception as e:
            messages.error(self.request, f'Error creating invoice: {str(e)}')
            return self.form_invalid(form)


class BulkInvoiceCreateView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Bulk create invoices for multiple students"""
    template_name = 'finance/pages/bulk_invoice.html'
    permission_required = 'finance.add_invoice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['classes'] = StudentClassSelector.get_all_classes()
        context['fee_types'] = FeeType.CHOICES
        context['sessions'] = AcademicSessionSelector.list_sessions(limit=5)
        return context
    
    def post(self, request, *args, **kwargs):
        class_id = request.POST.get('class_id')
        fee_type = request.POST.get('fee_type')
        amount = request.POST.get('amount')
        session_id = request.POST.get('session_id')
        term_id = request.POST.get('term_id')
        due_date = request.POST.get('due_date')
        
        if not all([class_id, fee_type, amount]):
            messages.error(request, 'Please fill all required fields')
            return self.get(request, *args, **kwargs)
        
        try:
            # Get all active students in this class
            from apps.students.selectors import StudentSelector
            students = StudentSelector.get_class_students(
                class_id=class_id,
                academic_session_id=session_id
            )
            
            if not students:
                messages.warning(request, 'No active students found in this class')
                return redirect('finance:invoice_list')
            
            student_ids = [s['id'] for s in students]
            
            # Create invoices
            results = InvoiceService.bulk_create_invoices(
                student_ids=student_ids,
                fee_type=fee_type,
                amount=Decimal(amount),
                description=f"{dict(FeeType.CHOICES).get(fee_type)} Fee",
                session_id=session_id,
                term_id=term_id,
                due_date=due_date,
                created_by_id=request.user.id
            )
            
            if results['successful']:
                messages.success(
                    request,
                    f"Created {len(results['successful'])} invoices successfully."
                )
            
            if results['skipped']:
                messages.info(
                    request,
                    f"Skipped {len(results['skipped'])} students (already have invoices)."
                )
            
            if results['failed']:
                messages.warning(
                    request,
                    f"Failed to create {len(results['failed'])} invoices."
                )
            
        except Exception as e:
            messages.error(request, f'Bulk invoice creation failed: {str(e)}')
        
        return redirect('finance:invoice_list')


class GenerateInvoicesFromStructureView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Generate invoices from fee structure (automated)"""
    permission_required = 'finance.add_invoice'
    
    def post(self, request, *args, **kwargs):
        class_id = request.POST.get('class_id')
        session_id = request.POST.get('session_id')
        term_id = request.POST.get('term_id')
        
        if not class_id:
            messages.error(request, 'Please select a class')
            return redirect('finance:bulk_invoice')
        
        try:
            results = InvoiceService.generate_invoices_from_fee_structure(
                class_id=class_id,
                session_id=session_id,
                term_id=term_id,
                created_by_id=request.user.id
            )
            
            messages.success(
                request,
                f"Generated {len(results['successful'])} invoices from fee structure. "
                f"Skipped {len(results['skipped'])} duplicates."
            )
            
        except Exception as e:
            messages.error(request, f'Invoice generation failed: {str(e)}')
        
        return redirect('finance:invoice_list')


class RecordPaymentView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Record a payment (cash/POS)"""
    template_name = 'finance/pages/record_payment.html'
    permission_required = 'finance.add_payment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        invoice_id = self.request.GET.get('invoice_id')
        if invoice_id:
            context['invoice'] = InvoiceSelector.get_by_id(invoice_id)
        
        context['payment_methods'] = [
            (PaymentMethod.CASH, 'Cash'),
            (PaymentMethod.POS, 'POS'),
            (PaymentMethod.TRANSFER, 'Bank Transfer'),
            (PaymentMethod.CHEQUE, 'Cheque'),
        ]
        
        return context
    
    def post(self, request, *args, **kwargs):
        invoice_id = request.POST.get('invoice_id')
        amount = request.POST.get('amount')
        method = request.POST.get('method')
        notes = request.POST.get('notes', '')
        
        if not all([invoice_id, amount, method]):
            messages.error(request, 'Please fill all required fields')
            return self.get(request, *args, **kwargs)
        
        try:
            amount_decimal = Decimal(amount)
            
            payment = PaymentService.record_cash_payment(
                invoice_id=invoice_id,
                amount=amount_decimal,
                received_by_id=request.user.id,
                notes=notes
            )
            
            messages.success(
                request,
                f'Payment recorded successfully. Receipt: {payment.receipt_number}'
            )
            
            return redirect('finance:invoice_detail', pk=invoice_id)
            
        except Exception as e:
            messages.error(request, f'Payment failed: {str(e)}')
            return self.get(request, *args, **kwargs)


class BulkPaymentView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Record a payment covering multiple invoices"""
    template_name = 'finance/pages/bulk_payment.html'
    permission_required = 'finance.add_payment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        student_id = self.request.GET.get('student_id')
        if student_id:
            # Get all unpaid invoices for this student
            context['invoices'] = InvoiceSelector.list_invoices(
                student_id=student_id,
                status__in=InvoiceStatus.REQUIRES_PAYMENT
            )
            context['student'] = StudentSelector.get_by_id(student_id)
            context['total_due'] = sum(i['balance'] for i in context['invoices'])
        
        context['payment_methods'] = [
            (PaymentMethod.CASH, 'Cash'),
            (PaymentMethod.POS, 'POS'),
            (PaymentMethod.TRANSFER, 'Bank Transfer'),
        ]
        
        return context
    
    def post(self, request, *args, **kwargs):
        invoice_ids = request.POST.getlist('invoice_ids')
        amount = request.POST.get('amount')
        method = request.POST.get('method')
        allocation = request.POST.get('allocation', 'even')
        notes = request.POST.get('notes', '')
        
        if not invoice_ids:
            messages.error(request, 'Please select at least one invoice')
            return self.get(request, *args, **kwargs)
        
        try:
            amount_decimal = Decimal(amount)
            allocate_evenly = (allocation == 'even')
            
            payments = PaymentService.record_bulk_payment(
                invoice_ids=[int(id) for id in invoice_ids],
                amount=amount_decimal,
                payment_method=method,
                received_by_id=request.user.id,
                notes=notes,
                allocate_evenly=allocate_evenly
            )
            
            messages.success(
                request,
                f'Successfully recorded {len(payments)} payments.'
            )
            
            # Redirect to first invoice
            if payments:
                return redirect('finance:invoice_detail', pk=payments[0].invoice_id)
            
        except Exception as e:
            messages.error(request, f'Bulk payment failed: {str(e)}')
        
        return redirect('finance:dashboard')


class WaiverRequestView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Request a fee waiver"""
    permission_required = 'finance.add_feewaiver'
    
    def post(self, request, *args, **kwargs):
        invoice_id = kwargs.get('pk')
        amount = request.POST.get('amount')
        reason = request.POST.get('reason')
        
        if not amount or not reason:
            messages.error(request, 'Please provide amount and reason')
            return redirect('finance:invoice_detail', pk=invoice_id)
        
        try:
            waiver = WaiverService.request_waiver(
                invoice_id=invoice_id,
                amount=Decimal(amount),
                reason=reason,
                requested_by_id=request.user.id
            )
            
            messages.success(request, 'Waiver request submitted successfully.')
            
        except WaiverLimitExceededError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Waiver request failed: {str(e)}')
        
        return redirect('finance:invoice_detail', pk=invoice_id)


class WaiverApproveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Approve a waiver request"""
    permission_required = 'finance.approve_waiver'
    
    def post(self, request, *args, **kwargs):
        waiver_id = kwargs.get('pk')
        notes = request.POST.get('notes', '')
        
        try:
            waiver = WaiverService.approve_waiver(
                waiver_id=waiver_id,
                approved_by_id=request.user.id,
                notes=notes
            )
            
            messages.success(
                request,
                f'Waiver of ₦{waiver.amount} approved and applied to invoice.'
            )
            
            return redirect('finance:invoice_detail', pk=waiver.invoice_id)
            
        except Exception as e:
            messages.error(request, f'Waiver approval failed: {str(e)}')
            return redirect('finance:dashboard')


class WaiverRejectView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Reject a waiver request"""
    permission_required = 'finance.approve_waiver'
    
    def post(self, request, *args, **kwargs):
        waiver_id = kwargs.get('pk')
        reason = request.POST.get('reason', '')
        
        try:
            waiver = WaiverService.reject_waiver(
                waiver_id=waiver_id,
                rejected_by_id=request.user.id,
                reason=reason
            )
            
            messages.info(request, 'Waiver request rejected.')
            
            return redirect('finance:invoice_detail', pk=waiver.invoice_id)
            
        except Exception as e:
            messages.error(request, f'Waiver rejection failed: {str(e)}')
            return redirect('finance:dashboard')


class ReceiptView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """View payment receipt"""
    model = Payment
    template_name = 'finance/pages/receipt.html'
    context_object_name = 'payment'
    permission_required = 'finance.view_payment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payment_data'] = PaymentSelector.get_by_id(self.object.id)
        context['invoice'] = InvoiceSelector.get_by_id(self.object.invoice_id)
        return context


class ExportTransactionsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Export transactions to CSV"""
    permission_required = 'finance.view_report'
    
    def get(self, request, *args, **kwargs):
        from apps.shared.csv_export import build_csv_response

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not start_date or not end_date:
            messages.error(request, 'Please provide start and end dates')
            return redirect('finance:dashboard')
        
        data = ReportService.export_transactions(start_date, end_date)
        
        headers = list(data[0].keys()) if data else []
        rows = [list(row.values()) for row in data] if data else []

        return build_csv_response(
            filename=f"transactions_{start_date}_to_{end_date}",
            headers=headers,
            rows=rows,
            date_suffix=False,
        )


class StudentFinancialView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Complete financial view for a single student"""
    template_name = 'finance/pages/student_financial.html'
    permission_required = 'finance.view_invoice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        student_id = kwargs.get('student_id')
        context['student'] = StudentSelector.get_by_id(student_id)
        
        if not context['student']:
            return context
        
        # Get all invoices for this student
        context['invoices'] = InvoiceSelector.list_invoices(
            student_id=student_id,
            limit=100
        )
        
        # Get balance summary
        context['balance'] = InvoiceSelector.get_student_balance(student_id)
        
        # Get payment history
        context['payments'] = FinancialStatusSelector.get_student_payment_history(
            student_id=student_id,
            limit=50
        )
        
        # Check exam clearance
        context['exam_clearance'] = FinancialStatusSelector.is_student_cleared_for_exams(
            student_id=student_id
        )
        
        return context
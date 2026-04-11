"""
Finance Selectors - READ Layer
Returns dicts, never model instances
Fixed: Proper imports and Decimal handling
"""

from django.db.models import Q, Sum, Count, Avg, F, Value
from django.db.models.functions import Coalesce
from django.db.models import DecimalField, IntegerField, FloatField
from django.utils import timezone
from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime, timedelta
from decimal import Decimal

from .models import Invoice, Payment, FeeStructure, FeeWaiver
from .constants import InvoiceStatus, PaymentStatus, PaymentMethod, FeeType
from apps.corecode.selectors import AcademicSessionSelector, StudentClassSelector


class InvoiceSelector:
    """All invoice read operations"""
    
    @staticmethod
    def get_by_id(invoice_id: int) -> Optional[Dict[str, Any]]:
        """Get invoice by ID. Returns dict for cross-app safety."""
        try:
            inv = Invoice.objects.select_related(
                'student_class', 'academic_session', 'academic_term',
                'created_by', 'waiver_approved_by'
            ).prefetch_related('payments', 'waivers').get(id=invoice_id)
            
            return {
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'student_id': inv.student_id,
                'student_name': inv.student_name,
                'student_class': {
                    'id': inv.student_class.id,
                    'name': inv.student_class.name,
                    'display_name': inv.student_class.display_name,
                },
                'academic_session': {
                    'id': inv.academic_session.id,
                    'name': inv.academic_session.name,
                },
                'academic_term': {
                    'id': inv.academic_term.id,
                    'name': inv.academic_term.name,
                    'term': inv.academic_term.term,
                } if inv.academic_term else None,
                'fee_type': inv.fee_type,
                'fee_type_display': inv.get_fee_type_display(),
                'description': inv.description,
                'subtotal': float(inv.subtotal),
                'discount_type': inv.discount_type,
                'discount_value': float(inv.discount_value) if inv.discount_value else 0,
                'discount_amount': float(inv.discount_amount),
                'total': float(inv.total),
                'amount_paid': float(inv.amount_paid),
                'balance': float(inv.balance),
                'status': inv.status,
                'status_display': inv.get_status_display(),
                'issue_date': inv.issue_date.isoformat(),
                'due_date': inv.due_date.isoformat(),
                'is_overdue': inv.is_overdue,
                'payment_progress': inv.payment_progress,
                
                # Waiver info
                'has_waiver': inv.has_waiver,
                'waiver_amount': float(inv.waiver_amount) if inv.waiver_amount else 0,
                'waiver_reason': inv.waiver_reason,
                'waiver_approved_by': inv.waiver_approved_by.get_full_name() if inv.waiver_approved_by else None,
                
                # Payments
                'payments': [
                    {
                        'id': p.id,
                        'transaction_id': p.transaction_id,
                        'amount': float(p.amount),
                        'method': p.get_payment_method_display(),
                        'status': p.get_status_display(),
                        'payment_date': p.payment_date.isoformat() if p.payment_date else None,
                        'receipt_number': p.receipt_number,
                    }
                    for p in inv.payments.all().order_by('-payment_date')
                ],
                
                # Waivers
                'waivers': [
                    {
                        'id': w.id,
                        'amount': float(w.amount),
                        'reason': w.reason,
                        'status': w.status,
                        'requested_by': w.requested_by.get_full_name() if w.requested_by else None,
                        'requested_at': w.requested_at.isoformat(),
                        'approved_by': w.approved_by.get_full_name() if w.approved_by else None,
                        'approved_at': w.approved_at.isoformat() if w.approved_at else None,
                    }
                    for w in inv.waivers.all().order_by('-requested_at')
                ],
                
                # Metadata
                'created_by': inv.created_by.get_full_name() if inv.created_by else None,
                'created_at': inv.created_at.isoformat(),
                'updated_at': inv.updated_at.isoformat(),
            }
        except Invoice.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_number(invoice_number: str) -> Optional[Dict[str, Any]]:
        """Get invoice by invoice number"""
        try:
            inv = Invoice.objects.get(invoice_number=invoice_number)
            return InvoiceSelector.get_by_id(inv.id)
        except Invoice.DoesNotExist:
            return None
    

    @staticmethod
    def list_invoices(
        student_id: Optional[int] = None,
        status: Optional[Union[str, List[str]]] = None,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        class_id: Optional[int] = None,
        fee_type: Optional[str] = None,
        overdue_only: bool = False,
        search: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List invoices with filters. Status can be a single string or a list of strings."""
        queryset = Invoice.objects.select_related(
            'student_class', 'academic_session', 'academic_term'
        ).prefetch_related('payments')
        
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        # Handle both single status and list of statuses
        if status:
            if isinstance(status, list):
                queryset = queryset.filter(status__in=status)
            else:
                queryset = queryset.filter(status=status)
        
        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        
        if term_id:
            queryset = queryset.filter(academic_term_id=term_id)
        
        if class_id:
            queryset = queryset.filter(student_class_id=class_id)
        
        if fee_type:
            queryset = queryset.filter(fee_type=fee_type)
        
        if overdue_only:
            queryset = queryset.filter(
                status__in=InvoiceStatus.REQUIRES_PAYMENT,
                due_date__lt=timezone.now().date()
            )
        
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(student_name__icontains=search) |
                Q(description__icontains=search)
            )
        
        invoices = []
        for inv in queryset.order_by('-issue_date')[:limit]:
            invoices.append({
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'student_id': inv.student_id,
                'student_name': inv.student_name,
                'student_class': inv.student_class.display_name,
                'session': inv.academic_session.name,
                'term': inv.academic_term.get_term_display() if inv.academic_term else 'N/A',
                'fee_type': inv.get_fee_type_display(),
                'total': float(inv.total),
                'amount_paid': float(inv.amount_paid),
                'balance': float(inv.balance),
                'status': inv.status,
                'status_display': inv.get_status_display(),
                'due_date': inv.due_date.isoformat(),
                'is_overdue': inv.is_overdue,
                'payment_progress': inv.payment_progress,
                'has_waiver': inv.has_waiver,
            })
        
        return invoices
    
    
    @staticmethod
    def get_student_balance(student_id: int, session_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get complete balance information for a student.
        
        Returns:
            Dictionary with:
            - total_invoiced: Total amount invoiced
            - total_paid: Total amount paid
            - total_balance: Current outstanding balance
            - overdue_balance: Amount overdue
            - has_overdue: Boolean indicating if any overdue exists
            - invoice_count: Total number of invoices
            - paid_count: Number of paid invoices
            - pending_count: Number of pending invoices
            - upcoming_due: List of upcoming due invoices
        """
        from django.db.models import Sum, Value, Q, DecimalField
        from django.db.models.functions import Coalesce
        from decimal import Decimal
        
        # Base queryset
        queryset = Invoice.objects.filter(student_id=student_id)
        
        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        
        # Calculate totals using DecimalField consistently
        # This prevents the mixed type error
        total_invoiced = queryset.aggregate(
            total=Coalesce(
                Sum('total', output_field=DecimalField()), 
                Value(Decimal('0'), output_field=DecimalField())
            )
        )['total']
        
        total_paid = queryset.aggregate(
            paid=Coalesce(
                Sum('amount_paid', output_field=DecimalField()), 
                Value(Decimal('0'), output_field=DecimalField())
            )
        )['paid']
        
        total_balance = queryset.aggregate(
            balance=Coalesce(
                Sum('balance', output_field=DecimalField()), 
                Value(Decimal('0'), output_field=DecimalField())
            )
        )['balance']
        
        # Get overdue invoices (balance > 0 and due date passed)
        from django.utils import timezone
        today = timezone.now().date()
        
        overdue_invoices = queryset.filter(
            balance__gt=0,
            due_date__lt=today,
            status__in=[InvoiceStatus.PENDING, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE]
        )
        
        overdue_total = overdue_invoices.aggregate(
            total=Coalesce(
                Sum('balance', output_field=DecimalField()), 
                Value(Decimal('0'), output_field=DecimalField())
            )
        )['total']
        
        # Get upcoming due invoices (balance > 0 and due date in future)
        upcoming = queryset.filter(
            balance__gt=0,
            due_date__gte=today,
            status__in=[InvoiceStatus.PENDING, InvoiceStatus.PARTIAL]
        ).order_by('due_date')[:5]
        
        # Convert Decimal to float for JSON serialization
        return {
            'student_id': student_id,
            'total_invoiced': float(total_invoiced),
            'total_paid': float(total_paid),
            'total_balance': float(total_balance),
            'overdue_balance': float(overdue_total),
            'has_overdue': overdue_total > 0,
            'invoice_count': queryset.count(),
            'paid_count': queryset.filter(status=InvoiceStatus.PAID).count(),
            'pending_count': queryset.filter(status__in=InvoiceStatus.REQUIRES_PAYMENT).count(),
            'upcoming_due': [
                {
                    'id': inv.id,
                    'invoice_number': inv.invoice_number,
                    'description': inv.description,
                    'balance': float(inv.balance),
                    'due_date': inv.due_date.isoformat(),
                    'days_until': (inv.due_date - today).days,
                }
                for inv in upcoming
            ],
        }
    

    @staticmethod
    def get_statistics(session_id: Optional[int] = None) -> Dict[str, Any]:
        """Get financial statistics with proper Decimal handling"""
        queryset = Invoice.objects.all()
        
        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        
        # Totals - All using DecimalField to avoid type mixing
        totals = queryset.aggregate(
            total_invoiced=Coalesce(
                Sum('total', output_field=DecimalField()), 
                Value(0, output_field=DecimalField())
            ),
            total_collected=Coalesce(
                Sum('amount_paid', output_field=DecimalField()), 
                Value(0, output_field=DecimalField())
            ),
            outstanding=Coalesce(
                Sum('balance', output_field=DecimalField()), 
                Value(0, output_field=DecimalField())
            )
        )
        
        total_invoiced = totals['total_invoiced']
        total_collected = totals['total_collected']
        outstanding = totals['outstanding']
        
        # Overdue invoices total
        overdue_result = queryset.filter(
            status__in=InvoiceStatus.REQUIRES_PAYMENT,
            due_date__lt=timezone.now().date()
        ).aggregate(
            overdue=Coalesce(
                Sum('balance', output_field=DecimalField()), 
                Value(0, output_field=DecimalField())
            )
        )
        overdue = overdue_result['overdue']
        
        # Counts by status (integers - no Decimal needed)
        status_counts = {}
        for status, _ in InvoiceStatus.CHOICES:
            count = queryset.filter(status=status).count()
            if count > 0:
                status_counts[status] = count
        
        # Collection rate - calculate as float
        if total_invoiced and total_invoiced > 0:
            collection_rate = (total_collected / total_invoiced * 100)
        else:
            collection_rate = Decimal('0')
        
        # Payment methods breakdown
        payment_methods = Payment.objects.filter(
            invoice__in=queryset,
            status=PaymentStatus.COMPLETED
        ).values('payment_method').annotate(
            total=Coalesce(
                Sum('amount', output_field=DecimalField()), 
                Value(0, output_field=DecimalField())
            ),
            count=Count('id')
        )
        
        # Calculate percentages for payment methods
        total_payments = sum([m['total'] for m in payment_methods if m['total']]) or Decimal('0')
        payment_methods_with_percentage = []
        for method in payment_methods:
            method_total = method['total'] or Decimal('0')
            percentage = (method_total / total_payments * 100) if total_payments > 0 else 0
            payment_methods_with_percentage.append({
                'method': method['payment_method'],
                'method_display': dict(PaymentMethod.CHOICES).get(method['payment_method'], method['payment_method']),
                'total': float(method_total),
                'count': method['count'],
                'percentage': float(percentage),
            })
        
        return {
            'total_invoiced': float(total_invoiced),
            'total_collected': float(total_collected),
            'outstanding': float(outstanding),
            'overdue': float(overdue),
            'collection_rate': float(collection_rate),
            'invoice_count': queryset.count(),
            'paid_count': queryset.filter(status=InvoiceStatus.PAID).count(),
            'pending_count': queryset.filter(status__in=InvoiceStatus.REQUIRES_PAYMENT).count(),
            'overdue_count': queryset.filter(
                status__in=InvoiceStatus.REQUIRES_PAYMENT,
                due_date__lt=timezone.now().date()
            ).count(),
            'status_breakdown': status_counts,
            'payment_methods': payment_methods_with_percentage,
        }



class PaymentSelector:
    """Payment read operations"""
    
    @staticmethod
    def get_by_id(payment_id: int) -> Optional[Dict[str, Any]]:
        """Get payment by ID"""
        try:
            payment = Payment.objects.select_related(
                'invoice', 'received_by'
            ).get(id=payment_id)
            
            return {
                'id': payment.id,
                'transaction_id': payment.transaction_id,
                'invoice': {
                    'id': payment.invoice.id,
                    'number': payment.invoice.invoice_number,
                    'student_name': payment.invoice.student_name,
                },
                'amount': float(payment.amount),
                'method': payment.get_payment_method_display(),
                'method_code': payment.payment_method,
                'status': payment.get_status_display(),
                'status_code': payment.status,
                'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                'gateway_reference': payment.gateway_reference,
                'receipt_number': payment.receipt_number,
                'notes': payment.notes,
                'received_by': payment.received_by.get_full_name() if payment.received_by else None,
                'created_at': payment.created_at.isoformat(),
            }
        except Payment.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_receipt(receipt_number: str) -> Optional[Dict[str, Any]]:
        """Get payment by receipt number"""
        try:
            payment = Payment.objects.get(receipt_number=receipt_number)
            return PaymentSelector.get_by_id(payment.id)
        except Payment.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_gateway_ref(gateway_reference: str) -> Optional[Dict[str, Any]]:
        """Get payment by gateway reference (Paystack)"""
        try:
            payment = Payment.objects.get(gateway_reference=gateway_reference)
            return PaymentSelector.get_by_id(payment.id)
        except Payment.DoesNotExist:
            return None
    
    @staticmethod
    def list_payments(
        invoice_id: Optional[int] = None,
        student_id: Optional[int] = None,
        method: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List payments with filters"""
        queryset = Payment.objects.select_related('invoice', 'received_by')
        
        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)
        
        if student_id:
            queryset = queryset.filter(invoice__student_id=student_id)
        
        if method:
            queryset = queryset.filter(payment_method=method)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if date_from:
            queryset = queryset.filter(payment_date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(payment_date__lte=date_to)
        
        payments = []
        for p in queryset.order_by('-payment_date', '-created_at')[:limit]:
            payments.append({
                'id': p.id,
                'transaction_id': p.transaction_id,
                'invoice_number': p.invoice.invoice_number,
                'student_name': p.invoice.student_name,
                'amount': float(p.amount),
                'method': p.get_payment_method_display(),
                'status': p.get_status_display(),
                'payment_date': p.payment_date.isoformat() if p.payment_date else None,
                'receipt_number': p.receipt_number,
                'received_by': p.received_by.get_full_name() if p.received_by else None,
            })
        
        return payments


class FeeStructureSelector:
    """Fee structure read operations"""
    
    @staticmethod
    def get_for_class(
        class_id: int,
        session_id: Optional[int] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get fee structures for a class"""
        queryset = FeeStructure.objects.filter(
            student_class_id=class_id
        ).select_related('student_class', 'academic_session')
        
        if session_id:
            queryset = queryset.filter(
                Q(academic_session_id=session_id) | Q(academic_session__isnull=True)
            )
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        fees = []
        for fee in queryset.order_by('fee_type'):
            fees.append({
                'id': fee.id,
                'fee_type': fee.fee_type,
                'fee_type_display': fee.get_fee_type_display(),
                'amount': float(fee.amount),
                'term': fee.term,
                'term_display': fee.get_term_display(),
                'description': fee.description,
                'is_active': fee.is_active,
                'session': fee.academic_session.name if fee.academic_session else 'All Sessions',
            })
        
        return fees
    
    @staticmethod
    def get_summary_by_class(session_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get fee summary grouped by class"""
        queryset = FeeStructure.objects.filter(is_active=True)
        
        if session_id:
            queryset = queryset.filter(
                Q(academic_session_id=session_id) | Q(academic_session__isnull=True)
            )
        
        classes = StudentClassSelector.get_all_classes()
        summary = []
        
        for class_obj in classes:
            class_fees = queryset.filter(student_class_id=class_obj.id)
            
            total_mandatory = class_fees.filter(
                fee_type__in=FeeType.CATEGORIES['mandatory']
            ).aggregate(total=Coalesce(Sum('amount'), Value(0)))['total']
            
            total_academic = class_fees.filter(
                fee_type__in=FeeType.CATEGORIES['academic']
            ).aggregate(total=Coalesce(Sum('amount'), Value(0)))['total']
            
            total_ancillary = class_fees.filter(
                fee_type__in=FeeType.CATEGORIES['ancillary']
            ).aggregate(total=Coalesce(Sum('amount'), Value(0)))['total']
            
            summary.append({
                'class_id': class_obj.id,
                'class_name': class_obj.display_name,
                'total_fees': float(total_mandatory + total_academic + total_ancillary),
                'mandatory_total': float(total_mandatory),
                'academic_total': float(total_academic),
                'ancillary_total': float(total_ancillary),
                'fee_count': class_fees.count(),
                'fee_breakdown': [
                    {
                        'type': fee.get_fee_type_display(),
                        'amount': float(fee.amount),
                        'term': fee.get_term_display(),
                    }
                    for fee in class_fees.order_by('fee_type')
                ],
            })
        
        return summary


class FinancialStatusSelector:
    """
    CRITICAL: Used by other apps (results, attendance) to check student financial status
    This is the PUBLIC INTERFACE for finance app
    """
    
    @staticmethod
    def is_student_cleared_for_exams(student_id: int, session_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Check if student is financially cleared for exams
        Used by Results app before allowing result entry
        """
        from django.db.models import Sum, Value, Q, DecimalField
        from django.db.models.functions import Coalesce
        from decimal import Decimal
        from django.utils import timezone
        
        if not session_id:
            session = AcademicSessionSelector.get_current_session()
            session_id = session.id if session else None
        
        # Get all pending invoices for this student
        pending_invoices = Invoice.objects.filter(
            student_id=student_id,
            academic_session_id=session_id,
            status__in=InvoiceStatus.REQUIRES_PAYMENT
        )
        
        # Calculate total due with proper Decimal handling
        total_due = pending_invoices.aggregate(
            total=Coalesce(
                Sum('balance', output_field=DecimalField()), 
                Value(Decimal('0'), output_field=DecimalField())
            )
        )['total']
        
        has_overdue = pending_invoices.filter(
            due_date__lt=timezone.now().date()
        ).exists()
        
        # Prepare pending invoices list safely
        pending_list = []
        for inv in pending_invoices:
            pending_list.append({
                'id': inv.id,
                'number': inv.invoice_number,
                'description': inv.description,
                'balance': float(inv.balance),
                'due_date': inv.due_date.isoformat(),
                'is_overdue': inv.due_date < timezone.now().date(),
            })
        
        return {
            'student_id': student_id,
            'session_id': session_id,
            'is_cleared': total_due == 0 and not has_overdue,
            'total_due': float(total_due),
            'has_overdue': has_overdue,
            'pending_count': pending_invoices.count(),
            'pending_invoices': pending_list,
        }
    

    
    @staticmethod
    def get_student_payment_history(student_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get complete payment history for a student"""
        payments = Payment.objects.filter(
            invoice__student_id=student_id,
            status=PaymentStatus.COMPLETED
        ).select_related('invoice').order_by('-payment_date')[:limit]
        
        return [
            {
                'id': p.id,
                'date': p.payment_date.isoformat() if p.payment_date else None,
                'amount': float(p.amount),
                'method': p.get_payment_method_display(),
                'receipt': p.receipt_number,
                'invoice': {
                    'number': p.invoice.invoice_number,
                    'description': p.invoice.description,
                    'session': p.invoice.academic_session.name,
                    'term': p.invoice.academic_term.get_term_display() if p.invoice.academic_term else None,
                },
                'received_by': p.received_by.get_full_name() if p.received_by else None,
            }
            for p in payments
        ]
    
    @staticmethod
    def get_class_payment_summary(class_id: int, session_id: Optional[int] = None) -> Dict[str, Any]:
        """Get payment summary for an entire class"""
        if not session_id:
            session = AcademicSessionSelector.get_current_session()
            session_id = session.id if session else None
        
        invoices = Invoice.objects.filter(
            student_class_id=class_id,
            academic_session_id=session_id
        )
        
        total_invoiced = invoices.aggregate(
            total=Coalesce(Sum('total'), Value(0))
        )['total']
        
        total_collected = invoices.aggregate(
            collected=Coalesce(Sum('amount_paid'), Value(0))
        )['collected']
        
        student_count = invoices.values('student_id').distinct().count()
        
        return {
            'class_id': class_id,
            'session_id': session_id,
            'student_count': student_count,
            'total_invoiced': float(total_invoiced),
            'total_collected': float(total_collected),
            'outstanding': float(total_invoiced - total_collected),
            'collection_rate': (total_collected / total_invoiced * 100) if total_invoiced > 0 else 0,
            'paid_students': invoices.filter(status=InvoiceStatus.PAID).values('student_id').distinct().count(),
            'partial_students': invoices.filter(status=InvoiceStatus.PARTIAL).values('student_id').distinct().count(),
            'pending_students': invoices.filter(status__in=[InvoiceStatus.PENDING, InvoiceStatus.OVERDUE]).values('student_id').distinct().count(),
        }
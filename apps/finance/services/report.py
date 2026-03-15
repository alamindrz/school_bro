"""
Report Service - Financial reporting and analytics
"""

from django.db.models import Sum, Count, Q, F, Avg
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..models import Invoice, Payment
from ..constants import InvoiceStatus, PaymentStatus, PaymentMethod, FeeType
from ..selectors import InvoiceSelector, PaymentSelector
from apps.corecode.selectors import AcademicSessionSelector, StudentClassSelector


class ReportService:
    """
    Financial reporting and analytics
    Used for dashboards, exports, and insights
    """
    
    @staticmethod
    def get_revenue_report(
        session_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate revenue report with breakdowns
        """
        payments = Payment.objects.filter(status=PaymentStatus.COMPLETED)
        
        if session_id:
            payments = payments.filter(invoice__academic_session_id=session_id)
        
        if start_date:
            payments = payments.filter(payment_date__gte=start_date)
        
        if end_date:
            payments = payments.filter(payment_date__lte=end_date)
        
        # Total revenue
        total_revenue = payments.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Revenue by payment method
        by_method = payments.values('payment_method').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Revenue by fee type
        by_fee_type = payments.values('invoice__fee_type').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Revenue by class
        by_class = payments.values(
            'invoice__student_class__name',
            'invoice__student_class__display_name'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Monthly breakdown
        monthly = payments.annotate(
            month=TruncMonth('payment_date')
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('month')
        
        # Daily averages
        days = payments.dates('payment_date', 'day').count()
        daily_average = total_revenue / days if days > 0 else 0
        
        return {
            'total_revenue': float(total_revenue),
            'total_transactions': payments.count(),
            'daily_average': float(daily_average),
            'by_payment_method': [
                {
                    'method': item['payment_method'],
                    'method_display': dict(PaymentMethod.CHOICES).get(item['payment_method']),
                    'total': float(item['total']),
                    'count': item['count'],
                    'percentage': (item['total'] / total_revenue * 100) if total_revenue > 0 else 0,
                }
                for item in by_method
            ],
            'by_fee_type': [
                {
                    'fee_type': item['invoice__fee_type'],
                    'fee_type_display': dict(FeeType.CHOICES).get(item['invoice__fee_type']),
                    'total': float(item['total']),
                    'count': item['count'],
                }
                for item in by_fee_type
            ],
            'by_class': [
                {
                    'class_name': item['invoice__student_class__display_name'],
                    'total': float(item['total']),
                    'count': item['count'],
                }
                for item in by_class
            ],
            'monthly': [
                {
                    'month': item['month'].strftime('%Y-%m') if item['month'] else None,
                    'total': float(item['total']),
                    'count': item['count'],
                }
                for item in monthly
            ],
        }
    
    @staticmethod
    def get_outstanding_report(
        session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate report on outstanding fees
        """
        invoices = Invoice.objects.filter(
            balance__gt=0,
            status__in=[InvoiceStatus.PENDING, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE]
        )
        
        if session_id:
            invoices = invoices.filter(academic_session_id=session_id)
        
        total_outstanding = invoices.aggregate(
            total=Sum('balance')
        )['total'] or 0
        
        # By class
        by_class = invoices.values(
            'student_class__id',
            'student_class__display_name'
        ).annotate(
            total=Sum('balance'),
            count=Count('id'),
            student_count=Count('student_id', distinct=True)
        ).order_by('-total')
        
        # Overdue
        overdue = invoices.filter(
            due_date__lt=timezone.now().date()
        )
        total_overdue = overdue.aggregate(
            total=Sum('balance')
        )['total'] or 0
        
        # By fee type
        by_fee_type = invoices.values('fee_type').annotate(
            total=Sum('balance'),
            count=Count('id')
        ).order_by('-total')
        
        # Top defaulters
        top_defaulters = invoices.values(
            'student_id',
            'student_name'
        ).annotate(
            total=Sum('balance'),
            invoice_count=Count('id'),
            overdue_count=Count('id', filter=Q(due_date__lt=timezone.now().date()))
        ).order_by('-total')[:10]
        
        return {
            'total_outstanding': float(total_outstanding),
            'total_overdue': float(total_overdue),
            'invoice_count': invoices.count(),
            'student_count': invoices.values('student_id').distinct().count(),
            'overdue_invoice_count': overdue.count(),
            'overdue_student_count': overdue.values('student_id').distinct().count(),
            'by_class': [
                {
                    'class_id': item['student_class__id'],
                    'class_name': item['student_class__display_name'],
                    'total': float(item['total']),
                    'invoice_count': item['count'],
                    'student_count': item['student_count'],
                }
                for item in by_class
            ],
            'by_fee_type': [
                {
                    'fee_type': item['fee_type'],
                    'fee_type_display': dict(FeeType.CHOICES).get(item['fee_type']),
                    'total': float(item['total']),
                    'count': item['count'],
                }
                for item in by_fee_type
            ],
            'top_defaulters': [
                {
                    'student_id': item['student_id'],
                    'student_name': item['student_name'],
                    'total': float(item['total']),
                    'invoice_count': item['invoice_count'],
                    'overdue_count': item['overdue_count'],
                }
                for item in top_defaulters
            ],
        }
    
    @staticmethod
    def get_collection_efficiency(
        session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate collection efficiency metrics
        """
        invoices = Invoice.objects.all()
        
        if session_id:
            invoices = invoices.filter(academic_session_id=session_id)
        
        total_invoiced = invoices.aggregate(
            total=Sum('total')
        )['total'] or 0
        
        total_collected = invoices.aggregate(
            total=Sum('amount_paid')
        )['total'] or 0
        
        # Collection rate by class
        by_class = invoices.values(
            'student_class__id',
            'student_class__display_name'
        ).annotate(
            invoiced=Sum('total'),
            collected=Sum('amount_paid'),
            balance=Sum('balance'),
            count=Count('id')
        ).order_by('student_class__sort_order')
        
        # Aging analysis
        today = timezone.now().date()
        aging = {
            'current': invoices.filter(
                balance__gt=0,
                due_date__gte=today
            ).aggregate(total=Sum('balance'))['total'] or 0,
            '1_30_days': invoices.filter(
                balance__gt=0,
                due_date__lt=today,
                due_date__gte=today - timedelta(days=30)
            ).aggregate(total=Sum('balance'))['total'] or 0,
            '31_60_days': invoices.filter(
                balance__gt=0,
                due_date__lt=today - timedelta(days=30),
                due_date__gte=today - timedelta(days=60)
            ).aggregate(total=Sum('balance'))['total'] or 0,
            '61_90_days': invoices.filter(
                balance__gt=0,
                due_date__lt=today - timedelta(days=60),
                due_date__gte=today - timedelta(days=90)
            ).aggregate(total=Sum('balance'))['total'] or 0,
            '90_plus_days': invoices.filter(
                balance__gt=0,
                due_date__lt=today - timedelta(days=90)
            ).aggregate(total=Sum('balance'))['total'] or 0,
        }
        
        return {
            'total_invoiced': float(total_invoiced),
            'total_collected': float(total_collected),
            'overall_rate': (total_collected / total_invoiced * 100) if total_invoiced > 0 else 0,
            'by_class': [
                {
                    'class_id': item['student_class__id'],
                    'class_name': item['student_class__display_name'],
                    'invoiced': float(item['invoiced']),
                    'collected': float(item['collected']),
                    'rate': (item['collected'] / item['invoiced'] * 100) if item['invoiced'] > 0 else 0,
                    'balance': float(item['balance']),
                }
                for item in by_class
            ],
            'aging': {k: float(v) for k, v in aging.items()},
        }
    
    @staticmethod
    def export_transactions(
        start_date: str,
        end_date: str,
        format: str = 'csv'
    ) -> List[Dict[str, Any]]:
        """
        Export transactions for external use
        """
        payments = Payment.objects.filter(
            status=PaymentStatus.COMPLETED,
            payment_date__date__gte=start_date,
            payment_date__date__lte=end_date
        ).select_related('invoice', 'received_by').order_by('payment_date')
        
        data = []
        for p in payments:
            data.append({
                'date': p.payment_date.strftime('%Y-%m-%d') if p.payment_date else '',
                'receipt_number': p.receipt_number,
                'transaction_id': p.transaction_id,
                'student_name': p.invoice.student_name,
                'student_id': p.invoice.student_id,
                'class': p.invoice.student_class.display_name,
                'invoice_number': p.invoice.invoice_number,
                'fee_type': p.invoice.get_fee_type_display(),
                'description': p.invoice.description,
                'amount': float(p.amount),
                'payment_method': p.get_payment_method_display(),
                'received_by': p.received_by.get_full_name() if p.received_by else '',
                'notes': p.notes,
            })
        
        return data
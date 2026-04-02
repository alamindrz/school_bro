"""
Admissions Selectors - READ Layer
Returns dicts, never model instances
"""

from django.db.models import Q, Count, Sum, Prefetch
from django.utils import timezone
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from .models import Application, ApplicationDocument, ApplicationNote
from .constants import ApplicationStatus
from apps.corecode.selectors import AcademicSessionSelector, StudentClassSelector
from apps.corecode.services import SiteConfigService
from apps.corecode.constants import SiteConfigKey


class ApplicationSelector:
    """All application read operations"""
    
    @staticmethod
    def get_by_id(application_id: int) -> Optional[Dict[str, Any]]:
        """Get application by ID. Returns dict for cross-app safety."""
        try:
            app = Application.objects.select_related(
                'applying_for_class', 'applying_for_session', 'reviewed_by'
            ).prefetch_related('documents', 'notes').get(id=application_id)
            
            # Get payment status from finance invoice if linked
            payment_info = None
            if app.invoice_id:
                from finance.selectors import InvoiceSelector
                invoice = InvoiceSelector.get_by_id(app.invoice_id)
                if invoice:
                    payment_info = {
                        'status': invoice.get('status'),
                        'status_display': invoice.get('status_display'),
                        'amount': invoice.get('total'),
                        'paid_amount': invoice.get('amount_paid'),
                        'balance': invoice.get('balance'),
                        'payment_completed': invoice.get('status') == 'paid',
                    }
            
            return {
                'id': app.id,
                'application_number': app.application_number,
                'full_name': app.full_name,
                'first_name': app.first_name,
                'last_name': app.last_name,
                'middle_name': app.middle_name,
                'gender': app.gender,
                'date_of_birth': app.date_of_birth.isoformat(),
                'email': app.email,
                'phone': app.phone,
                'address': app.address,
                'city': app.city,
                'state_of_origin': app.state_of_origin,
                'nationality': app.nationality,
                'applying_for_class': {
                    'id': app.applying_for_class.id,
                    'name': app.applying_for_class.name,
                    'display_name': app.applying_for_class.display_name,
                },
                'application_type': app.application_type,
                'application_type_display': app.get_application_type_display(),
                'previous_school': app.previous_school,
                'previous_class': app.previous_class,
                'guardian_first_name': app.guardian_first_name,
                'guardian_last_name': app.guardian_last_name,
                'guardian_full_name': f"{app.guardian_last_name}, {app.guardian_first_name}",
                'guardian_relationship': app.guardian_relationship,
                'guardian_phone': app.guardian_phone,
                'guardian_email': app.guardian_email,
                'status': app.status,
                'status_display': app.get_status_display(),
                'applying_for_session': {
                    'id': app.applying_for_session.id,
                    'name': app.applying_for_session.name,
                },
                'invoice_id': app.invoice_id,
                'payment': payment_info,
                'payment_completed': payment_info.get('payment_completed') if payment_info else False,
                'reviewed_by': app.reviewed_by.get_full_name() if app.reviewed_by else None,
                'reviewed_at': app.reviewed_at.isoformat() if app.reviewed_at else None,
                'review_notes': app.review_notes,
                'enrolled_student_id': app.enrolled_student_id,
                'enrolled_at': app.enrolled_at.isoformat() if app.enrolled_at else None,
                'submitted_at': app.submitted_at.isoformat() if app.submitted_at else None,
                'created_at': app.created_at.isoformat(),
                'updated_at': app.updated_at.isoformat(),
                
                # Related data
                'documents': [
                    {
                        'id': doc.id,
                        'type': doc.get_document_type_display(),
                        'filename': doc.filename,
                        'file_size': doc.file_size,
                        'uploaded_at': doc.uploaded_at.isoformat(),
                    }
                    for doc in app.documents.all()
                ],
                'notes': [
                    {
                        'id': note.id,
                        'note': note.note,
                        'created_by': note.created_by.get_full_name() if note.created_by else 'System',
                        'created_at': note.created_at.isoformat(),
                    }
                    for note in app.notes.all()[:5]  # Last 5 notes
                ],
            }
        except Application.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_number(application_number: str) -> Optional[Dict[str, Any]]:
        """Get application by application number"""
        try:
            app = Application.objects.get(application_number=application_number)
            return ApplicationSelector.get_by_id(app.id)
        except Application.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_invoice_id(invoice_id: int) -> Optional[Dict[str, Any]]:
        """Get application by finance invoice ID"""
        try:
            app = Application.objects.get(invoice_id=invoice_id)
            return ApplicationSelector.get_by_id(app.id)
        except Application.DoesNotExist:
            return None
    
    @staticmethod
    def list_applications(
        status: Optional[str] = None,
        class_id: Optional[int] = None,
        session_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List applications with filters"""
        queryset = Application.objects.select_related(
            'applying_for_class', 'applying_for_session'
        )
        
        if status:
            queryset = queryset.filter(status=status)
        
        if class_id:
            queryset = queryset.filter(applying_for_class_id=class_id)
        
        if session_id:
            queryset = queryset.filter(applying_for_session_id=session_id)
        
        if search:
            queryset = queryset.filter(
                Q(application_number__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(guardian_email__icontains=search) |
                Q(guardian_phone__icontains=search)
            )
        
        applications = []
        for app in queryset.order_by('-created_at')[:limit]:
            # Check payment status from finance
            payment_completed = False
            payment_status = None
            if app.invoice_id:
                from finance.selectors import InvoiceSelector
                invoice = InvoiceSelector.get_by_id(app.invoice_id)
                if invoice:
                    payment_completed = invoice.get('status') == 'paid'
                    payment_status = invoice.get('status_display')
            
            applications.append({
                'id': app.id,
                'application_number': app.application_number,
                'full_name': app.full_name,
                'email': app.email,
                'phone': app.phone,
                'applying_for_class': app.applying_for_class.display_name,
                'status': app.status,
                'status_display': app.get_status_display(),
                'payment_completed': payment_completed,
                'payment_status': payment_status,
                'submitted_at': app.submitted_at.isoformat() if app.submitted_at else None,
                'created_at': app.created_at.isoformat(),
            })
        
        return applications
    
    @staticmethod
    def get_pending_review_count() -> int:
        """Get count of applications pending review"""
        return Application.objects.filter(
            status=ApplicationStatus.SUBMITTED
        ).count()
    
    @staticmethod
    def get_statistics(session_id: Optional[int] = None) -> Dict[str, Any]:
        """Get admissions statistics"""
        queryset = Application.objects.all()
        
        if session_id:
            queryset = queryset.filter(applying_for_session_id=session_id)
        
        total = queryset.count()
        
        # Count applications with paid invoices
        paid_count = 0
        for app in queryset.filter(invoice_id__isnull=False):
            if app.payment_completed:
                paid_count += 1
        
        return {
            'total': total,
            'by_status': {
                status: queryset.filter(status=status).count()
                for status, _ in ApplicationStatus.CHOICES
            },
            'submitted_today': queryset.filter(
                submitted_at__date=timezone.now().date()
            ).count(),
            'pending_review': queryset.filter(
                status=ApplicationStatus.SUBMITTED
            ).count(),
            'approved': queryset.filter(status=ApplicationStatus.APPROVED).count(),
            'enrolled': queryset.filter(status=ApplicationStatus.ENROLLED).count(),
            'paid_count': paid_count,
            'completion_rate': (
                (queryset.filter(status=ApplicationStatus.ENROLLED).count() / total * 100)
                if total > 0 else 0
            ),
        }


# REMOVED: ApplicationPaymentSelector class entirely


class ApplicationDocumentSelector:
    """Document read operations"""
    
    @staticmethod
    def list_for_application(application_id: int) -> List[Dict[str, Any]]:
        """List documents for an application"""
        docs = ApplicationDocument.objects.filter(application_id=application_id)
        
        return [
            {
                'id': doc.id,
                'type': doc.get_document_type_display(),
                'filename': doc.filename,
                'file_size': doc.file_size,
                'file_size_kb': round(doc.file_size / 1024, 1),
                'uploaded_at': doc.uploaded_at.isoformat(),
                'url': doc.file.url if doc.file else None,
            }
            for doc in docs
        ]
        
class AdmissionsPeriodSelector:
    """Read operations for admissions periods"""
    
    @staticmethod
    def get_current_period() -> Optional[Dict[str, Any]]:
        """
        Get the currently active admissions period.
        Returns the first active period that is currently open.
        """
        from .models import AdmissionsPeriod
        
        now = timezone.now()
        period = AdmissionsPeriod.objects.filter(
            is_active=True,
            start_date__lte=now,
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        ).order_by('-start_date').first()
        
        if not period:
            return None
        
        # Check capacity
        if period.max_applications and period.current_applications >= period.max_applications:
            return None
        
        return {
            'id': period.id,
            'name': period.name,
            'academic_session': {
                'id': period.academic_session.id,
                'name': period.academic_session.name,
                'code': period.academic_session.code,
            },
            'start_date': period.start_date.isoformat(),
            'end_date': period.end_date.isoformat() if period.end_date else None,
            'application_fee': float(period.application_fee),
            'is_active': period.is_active,
            'has_capacity': period.has_capacity(),
            'current_applications': period.current_applications,
            'max_applications': period.max_applications,
        }
    
    @staticmethod
    def get_periods_for_session(session_id: int) -> List[Dict[str, Any]]:
        """Get all admission periods for a specific academic session"""
        from .models import AdmissionsPeriod
        
        periods = AdmissionsPeriod.objects.filter(
            academic_session_id=session_id
        ).order_by('start_date')
        
        return [
            {
                'id': p.id,
                'name': p.name,
                'start_date': p.start_date.isoformat(),
                'end_date': p.end_date.isoformat() if p.end_date else None,
                'application_fee': float(p.application_fee),
                'is_active': p.is_active,
                'current_applications': p.current_applications,
                'max_applications': p.max_applications,
                'is_open': p.is_currently_open(),
            }
            for p in periods
        ]
    
    @staticmethod
    def get_upcoming_periods(limit: int = 3) -> List[Dict[str, Any]]:
        """Get upcoming admission periods that haven't started yet"""
        from .models import AdmissionsPeriod
        
        now = timezone.now()
        periods = AdmissionsPeriod.objects.filter(
            is_active=True,
            start_date__gt=now
        ).order_by('start_date')[:limit]
        
        return [
            {
                'id': p.id,
                'name': p.name,
                'academic_session': p.academic_session.name,
                'start_date': p.start_date.isoformat(),
                'application_fee': float(p.application_fee),
            }
            for p in periods
        ]
    
    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """Get statistics about all admission periods"""
        from .models import AdmissionsPeriod
        from django.db.models import Sum, Count, Q
        
        now = timezone.now()
        
        stats = {
            'total_periods': AdmissionsPeriod.objects.count(),
            'active_periods': AdmissionsPeriod.objects.filter(is_active=True).count(),
            'open_now': AdmissionsPeriod.objects.filter(
                is_active=True,
                start_date__lte=now,
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=now)
            ).count(),
            'upcoming': AdmissionsPeriod.objects.filter(
                is_active=True,
                start_date__gt=now
            ).count(),
            'total_applications': AdmissionsPeriod.objects.aggregate(
                total=Sum('current_applications')
            )['total'] or 0,
            'at_capacity': AdmissionsPeriod.objects.filter(
                max_applications__isnull=False,
                current_applications__gte=models.F('max_applications')
            ).count(),
        }
        
        return stats
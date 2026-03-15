"""
Admissions Selectors - READ Layer
Returns dicts, never model instances
"""

from django.db.models import Q, Count, Sum, Prefetch
from django.utils import timezone
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from .models import Application, ApplicationPayment, ApplicationDocument, ApplicationNote
from .constants import ApplicationStatus, PaymentStatus
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
                'reviewed_by': app.reviewed_by.get_full_name() if app.reviewed_by else None,
                'reviewed_at': app.reviewed_at.isoformat() if app.reviewed_at else None,
                'review_notes': app.review_notes,
                'enrolled_student_id': app.enrolled_student_id,
                'enrolled_at': app.enrolled_at.isoformat() if app.enrolled_at else None,
                'submitted_at': app.submitted_at.isoformat() if app.submitted_at else None,
                'created_at': app.created_at.isoformat(),
                'updated_at': app.updated_at.isoformat(),
                
                # Related data
                'payment': ApplicationPaymentSelector.get_for_application(app.id),
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
        ).prefetch_related('payment')
        
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
                Q(email__icontains=search)
            )
        
        applications = []
        for app in queryset.order_by('-created_at')[:limit]:
            payment = None
            if hasattr(app, 'payment'):
                payment = {
                    'status': app.payment.status,
                    'status_display': app.payment.get_status_display(),
                    'amount': str(app.payment.amount),
                }
            
            applications.append({
                'id': app.id,
                'application_number': app.application_number,
                'full_name': app.full_name,
                'email': app.email,
                'phone': app.phone,
                'applying_for_class': app.applying_for_class.display_name,
                'status': app.status,
                'status_display': app.get_status_display(),
                'payment_status': payment['status_display'] if payment else 'No Payment',
                'payment_completed': payment and payment['status'] == 'completed',
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
            'completion_rate': (
                (queryset.filter(status=ApplicationStatus.ENROLLED).count() / total * 100)
                if total > 0 else 0
            ),
        }


class ApplicationPaymentSelector:
    """Payment read operations"""
    
    @staticmethod
    def get_for_application(application_id: int) -> Optional[Dict[str, Any]]:
        """Get payment details for an application"""
        try:
            payment = ApplicationPayment.objects.get(application_id=application_id)
            return {
                'id': payment.id,
                'amount': str(payment.amount),
                'status': payment.status,
                'status_display': payment.get_status_display(),
                'payment_method': payment.get_payment_method_display(),
                'paystack_reference': payment.paystack_reference,
                'transaction_date': payment.transaction_date.isoformat() if payment.transaction_date else None,
                'verified_at': payment.verified_at.isoformat() if payment.verified_at else None,
                'created_at': payment.created_at.isoformat(),
            }
        except ApplicationPayment.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_reference(reference: str) -> Optional[Dict[str, Any]]:
        """Get payment by Paystack reference"""
        try:
            payment = ApplicationPayment.objects.get(paystack_reference=reference)
            return ApplicationPaymentSelector.get_for_application(payment.application_id)
        except ApplicationPayment.DoesNotExist:
            return None
    
    @staticmethod
    def get_pending_payments_count() -> int:
        """Get count of pending payments"""
        return ApplicationPayment.objects.filter(
            status=PaymentStatus.PENDING
        ).count()


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
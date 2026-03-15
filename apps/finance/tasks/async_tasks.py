"""
Celery tasks for finance app
"""

from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import date, timedelta
import logging

from ..services import InvoiceService, PaymentService, ReportService
from ..models import Invoice, Payment
from ..constants import InvoiceStatus, PaymentStatus

logger = logging.getLogger(__name__)


@shared_task
def mark_overdue_invoices():
    """
    Mark overdue invoices as OVERDUE
    Run daily at midnight
    """
    count = InvoiceService.mark_overdue_invoices()
    logger.info(f"Marked {count} invoices as overdue")
    return count


@shared_task
def send_payment_reminders(days_before=7):
    """
    Send payment reminders for upcoming due dates
    Run daily at 8 AM
    """
    from apps.parents.services import NotificationService
    from apps.parents.selectors import ChildLinkSelector
    
    due_date = date.today() + timedelta(days=days_before)
    
    upcoming = Invoice.objects.filter(
        status__in=[InvoiceStatus.PENDING, InvoiceStatus.PARTIAL],
        due_date=due_date,
        balance__gt=0
    ).select_related('student_class', 'academic_session')
    
    count = 0
    for invoice in upcoming:
        # Get parents for this student
        parents = ChildLinkSelector.get_for_student(invoice.student_id)
        
        for parent in parents:
            NotificationService.send_payment_reminder(
                parent_id=parent['parent_id'],
                student_id=invoice.student_id,
                amount=float(invoice.balance),
                due_date=invoice.due_date.isoformat(),
                invoice_number=invoice.invoice_number
            )
            count += 1
    
    logger.info(f"Sent {count} payment reminders for due date {due_date}")
    return count


@shared_task
def generate_monthly_reports():
    """
    Generate monthly financial reports
    Run on 1st of each month at 2 AM
    """
    from apps.corecode.selectors import AcademicSessionSelector
    
    current_session = AcademicSessionSelector.get_current_session()
    if not current_session:
        logger.error("No current session found")
        return 0
    
    # Get last month's date range
    today = date.today()
    first_day = date(today.year, today.month - 1, 1) if today.month > 1 else date(today.year - 1, 12, 1)
    last_day = date(today.year, today.month, 1) - timedelta(days=1)
    
    # Generate revenue report
    revenue = ReportService.get_revenue_report(
        session_id=current_session.id,
        start_date=first_day.isoformat(),
        end_date=last_day.isoformat()
    )
    
    # Generate outstanding report
    outstanding = ReportService.get_outstanding_report(current_session.id)
    
    # Email to finance team
    if hasattr(settings, 'FINANCE_EMAIL'):
        send_mail(
            subject=f"Monthly Financial Report - {first_day.strftime('%B %Y')}",
            message=f"""
            Revenue: ₦{revenue['total_revenue']:,.2f}
            Transactions: {revenue['total_transactions']}
            Outstanding: ₦{outstanding['total_outstanding']:,.2f}
            Overdue: ₦{outstanding['total_overdue']:,.2f}
            
            See attached report for details.
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.FINANCE_EMAIL],
            fail_silently=True,
        )
    
    logger.info(f"Monthly financial report generated for {first_day.strftime('%B %Y')}")
    return 1


@shared_task
def process_paystack_webhook(payload):
    """
    Process Paystack webhook asynchronously
    """
    from ..services import PaymentService
    
    try:
        result = PaymentService.handle_webhook(payload)
        logger.info(f"Webhook processed: {result}")
        return result
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise


@shared_task
def cleanup_old_payments(days=365):
    """
    Archive or clean up old payment records
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Mark old payments as archived (soft delete)
    old_payments = Payment.objects.filter(
        created_at__lt=cutoff_date,
        status=PaymentStatus.COMPLETED
    )
    
    count = old_payments.count()
    # Instead of deleting, we could archive or mark as read-only
    # For now, just log
    logger.info(f"Found {count} payments older than {days} days")
    
    return count
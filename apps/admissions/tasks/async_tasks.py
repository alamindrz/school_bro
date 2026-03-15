"""
Celery tasks for admissions
Heavy operations that should run asynchronously
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import logging

from ..models import Application
from ..services import EnrollmentService
from ..constants import ApplicationStatus

logger = logging.getLogger(__name__)


@shared_task
def send_application_confirmation_email(application_id: int):
    """Send confirmation email after application submission"""
    try:
        application = Application.objects.get(id=application_id)
        
        subject = f"Application Received - {application.application_number}"
        message = f"""
        Dear {application.full_name},
        
        Thank you for submitting your application to our school.
        
        Application Number: {application.application_number}
        Submitted: {application.submitted_at.strftime('%B %d, %Y at %H:%M')}
        
        We will review your application and contact you soon.
        
        You can check your application status at:
        {settings.SITE_URL}/admissions/apply/{application.application_number}/
        
        Regards,
        Admissions Office
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            fail_silently=True,
        )
        
        logger.info(f"Confirmation email sent for {application.application_number}")
        
    except Application.DoesNotExist:
        logger.error(f"Application {application_id} not found for email")
    except Exception as e:
        logger.error(f"Failed to send email for {application_id}: {e}")


@shared_task
def send_application_status_email(application_id: int):
    """Send email when application status changes"""
    try:
        application = Application.objects.get(id=application_id)
        
        status_messages = {
            ApplicationStatus.APPROVED: "Congratulations! Your application has been approved.",
            ApplicationStatus.REJECTED: "We regret to inform you that your application was not approved.",
            ApplicationStatus.WAITLISTED: "Your application has been waitlisted.",
        }
        
        message_template = status_messages.get(application.status)
        if not message_template:
            return
        
        subject = f"Application Status Update - {application.application_number}"
        message = f"""
        Dear {application.full_name},
        
        {message_template}
        
        Application Number: {application.application_number}
        New Status: {application.get_status_display()}
        
        """
        
        if application.status == ApplicationStatus.APPROVED:
            message += """
            Please complete the enrollment process by paying the acceptance fee.
            """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            fail_silently=True,
        )
        
        logger.info(f"Status email sent for {application.application_number}")
        
    except Application.DoesNotExist:
        logger.error(f"Application {application_id} not found for email")
    except Exception as e:
        logger.error(f"Failed to send status email for {application_id}: {e}")


@shared_task
def expire_old_approved_applications():
    """
    Automatically expire approved applications after deadline
    Run daily via celery beat
    """
    from django.utils import timezone
    from datetime import timedelta
    
    deadline_days = getattr(settings, 'ADMISSION_DEADLINE_DAYS', 30)
    cutoff_date = timezone.now() - timedelta(days=deadline_days)
    
    expired = Application.objects.filter(
        status=ApplicationStatus.APPROVED,
        reviewed_at__lte=cutoff_date,
        enrolled_student_id__isnull=True
    )
    
    count = expired.count()
    expired.update(status=ApplicationStatus.EXPIRED)
    
    logger.info(f"Expired {count} approved applications")
    return count


@shared_task
def process_bulk_enrollment(application_ids: list, enrolled_by_id: int = None):
    """
    Process bulk enrollment asynchronously
    """
    results = EnrollmentService.bulk_enroll(application_ids, enrolled_by_id)
    
    logger.info(
        f"Bulk enrollment completed: {len(results['successful'])} successful, "
        f"{len(results['failed'])} failed"
    )
    
    return results
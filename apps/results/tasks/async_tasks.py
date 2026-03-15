"""
Celery tasks for results app
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from ..models import ResultSheet, CumulativeRecord
from ..services import ResultService, ReportService
from ..constants import ResultStatus

logger = logging.getLogger(__name__)


@shared_task
def calculate_cumulative_records(session_id=None):
    """
    Calculate cumulative records for all students
    Run at end of term
    """
    from apps.students.selectors import StudentSelector

    if not session_id:
        from apps.corecode.selectors import AcademicSessionSelector
        current_session = AcademicSessionSelector.get_current_session()
        if not current_session:
            logger.error("No current session found")
            return 0
        session_id = current_session.id

    # Get all students with results in this session
    students_with_results = ResultSheet.objects.filter(
        academic_session_id=session_id,
        status=ResultStatus.PUBLISHED
    ).values_list('results__student_id', flat=True).distinct()

    count = 0
    for student_id in students_with_results:
        try:
            ResultService.update_cumulative_record(
                student_id=student_id,
                session_id=session_id
            )
            count += 1
        except Exception as e:
            logger.error(f"Failed to update cumulative record for student {student_id}: {e}")

    logger.info(f"Updated cumulative records for {count} students")
    return count


@shared_task
def send_result_notifications(sheet_id):
    """
    Send result publication notifications to parents
    """
    from apps.parents.services import NotificationService
    from apps.parents.selectors import ChildLinkSelector

    try:
        sheet = ResultSheet.objects.get(id=sheet_id)
    except ResultSheet.DoesNotExist:
        logger.error(f"Result sheet {sheet_id} not found")
        return 0

    # Get all students in this sheet
    student_ids = sheet.results.values_list('student_id', flat=True).distinct()

    count = 0
    for student_id in student_ids:
        parents = ChildLinkSelector.get_for_student(student_id)

        for parent in parents:
            try:
                NotificationService.send_results_published(
                    parent_id=parent['parent_id'],
                    student_id=student_id,
                    term=sheet.academic_term.get_term_display(),
                    session=sheet.academic_session.name
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to notify parent {parent['parent_id']}: {e}")

    logger.info(f"Sent {count} result notifications for sheet {sheet_id}")
    return count


@shared_task
def archive_old_results(years=2):
    """
    Archive result sheets older than specified years
    """
    cutoff_date = timezone.now() - timedelta(days=365 * years)

    old_sheets = ResultSheet.objects.filter(
        created_at__lt=cutoff_date,
        status=ResultStatus.PUBLISHED
    )

    count = old_sheets.count()
    old_sheets.update(status=ResultStatus.ARCHIVED)

    logger.info(f"Archived {count} old result sheets")
    return count


@shared_task
def generate_term_reports():
    """
    Generate term reports for all published sheets
    Run at end of term
    """
    from django.core.mail import send_mail
    from django.conf import settings

    published_sheets = ResultSheet.objects.filter(
        status=ResultStatus.PUBLISHED
    ).select_related('student_class', 'academic_session', 'academic_term')

    count = 0
    for sheet in published_sheets:
        try:
            report = ReportService.generate_term_report(sheet.id)

            # Email report to class teacher/principal
            if hasattr(settings, 'RESULTS_EMAIL'):
                send_mail(
                    subject=f"Term Report - {sheet.student_class.display_name} - {sheet.academic_term.name}",
                    message=f"""
                    Class: {sheet.student_class.display_name}
                    Term: {sheet.academic_term.name}
                    Session: {sheet.academic_session.name}
                    
                    Class Average: {report['summary']['class_average']:.2f}
                    Total Students: {report['summary']['total_students']}
                    
                    See attached for full report.
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.RESULTS_EMAIL],
                    fail_silently=True,
                )
            count += 1

        except Exception as e:
            logger.error(f"Failed to generate report for sheet {sheet.id}: {e}")

    logger.info(f"Generated term reports for {count} sheets")
    return count
"""
Celery tasks for attendance app
"""

from celery import shared_task
from django.utils import timezone
from datetime import date, timedelta
import logging

from ..services import AttendanceService, ReportService
from ..models import AttendanceRegister, AttendanceSummary
from ..constants import LOW_ATTENDANCE_THRESHOLD

logger = logging.getLogger(__name__)


@shared_task
def update_all_summaries():
    """
    Update attendance summaries for all students
    Run daily at midnight
    """
    count = AttendanceService.update_all_summaries()
    logger.info(f"Updated attendance summaries for {count} students")
    return count


@shared_task
def send_daily_attendance_reports():
    """
    Send daily attendance reports to staff
    Run daily at 6 PM
    """
    from apps.parents.services import NotificationService
    from apps.staffs.selectors import StaffSelector
    
    today = date.today()
    summary = ReportService.generate_daily_report(today)
    
    if summary['has_data']:
        # Send to admin staff
        admins = StaffSelector.get_admin_staff()
        
        for admin in admins:
            NotificationService.send_notification(
                parent_id=None,  # Staff notification would need its own system
                notification_type='attendance_report',
                title=f"Daily Attendance Report - {today}",
                message=f"Present: {summary['summary']['present']}, "
                        f"Absent: {summary['summary']['absent']}, "
                        f"Rate: {summary['summary']['present_percentage']:.1f}%",
                data=summary
            )
    
    logger.info(f"Daily attendance report sent for {today}")


@shared_task
def cleanup_old_registers(days=90):
    """
    Archive old attendance registers
    """
    cutoff_date = date.today() - timedelta(days=days)
    
    # Soft delete by marking as closed if not already
    old_registers = AttendanceRegister.objects.filter(
        date__lt=cutoff_date,
        is_closed=False
    )
    
    count = old_registers.count()
    old_registers.update(is_closed=True, closed_at=timezone.now())
    
    logger.info(f"Closed {count} old attendance registers")
    return count


@shared_task
def process_attendance_alerts():
    """
    Check for attendance alerts and send notifications
    Run daily at 9 AM
    """
    from apps.parents.services import NotificationService
    
    # Get students with low attendance
    alerts = AttendanceSummary.objects.filter(
        attendance_alert=True,
        present_percentage__lt=LOW_ATTENDANCE_THRESHOLD
    ).select_related('academic_session', 'academic_term')
    
    count = 0
    for alert in alerts:
        # Get parents for this student
        from apps.parents.selectors import ChildLinkSelector
        parents = ChildLinkSelector.get_for_student(alert.student_id)
        
        for parent in parents:
            NotificationService.send_notification(
                parent_id=parent['parent_id'],
                notification_type='attendance_alert',
                title="Attendance Alert",
                message=f"Your child's attendance has dropped to {alert.present_percentage:.1f}%. "
                        f"Please contact the school.",
                data={
                    'student_id': alert.student_id,
                    'student_name': alert.student_name,
                    'attendance': alert.present_percentage,
                },
                priority='high'
            )
            count += 1
    
    logger.info(f"Sent {count} attendance alerts")
    return count
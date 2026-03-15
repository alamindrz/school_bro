"""
Celery tasks for audit
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging
import csv
import os
from django.conf import settings

from .models import AuditLog, AuditArchive, AuditRetentionPolicy

logger = logging.getLogger(__name__)


@shared_task
def archive_old_logs():
    """Archive audit logs based on retention policy"""
    
    # Get default retention (365 days)
    default_days = 365
    
    # Process each app/model combination
    policies = AuditRetentionPolicy.objects.filter(is_active=True)
    
    archived_count = 0
    
    for policy in policies:
        cutoff = timezone.now() - timedelta(days=policy.retention_days)
        
        logs = AuditLog.objects.filter(
            app_label=policy.app_label,
            model_name=policy.model_name,
            timestamp__lt=cutoff
        )
        
        if logs.exists():
            # Create archive file
            archive_date = timezone.now().date()
            filename = f"audit_{policy.app_label}_{policy.model_name}_{archive_date}.csv"
            filepath = os.path.join(settings.MEDIA_ROOT, 'audit/archives', 
                                    str(archive_date.year), str(archive_date.month), filename)
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Write logs to CSV
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    'timestamp', 'user', 'action', 'category', 'status',
                    'app_label', 'model_name', 'object_id', 'object_repr',
                    'old_value', 'new_value', 'ip_address'
                ])
                
                for log in logs:
                    writer.writerow([
                        log.timestamp,
                        log.username,
                        log.action,
                        log.category,
                        log.status,
                        log.app_label,
                        log.model_name,
                        log.object_id,
                        log.object_repr,
                        log.old_value,
                        log.new_value,
                        log.ip_address,
                    ])
            
            # Create archive record
            archive = AuditArchive.objects.create(
                archive_date=archive_date,
                archive_file=filepath,
                record_count=logs.count(),
                date_from=logs.aggregate(min_date=models.Min('timestamp'))['min_date'].date(),
                date_to=logs.aggregate(max_date=models.Max('timestamp'))['max_date'].date(),
            )
            
            # Delete archived logs
            count = logs.delete()[0]
            archived_count += count
            
            logger.info(f"Archived {count} logs for {policy.app_label}.{policy.model_name}")
    
    # Handle apps without specific policies
    cutoff = timezone.now() - timedelta(days=default_days)
    other_logs = AuditLog.objects.filter(
        timestamp__lt=cutoff
    ).exclude(
        app_label__in=[p.app_label for p in policies],
        model_name__in=[p.model_name for p in policies]
    )
    
    if other_logs.exists():
        count = other_logs.delete()[0]
        archived_count += count
        logger.info(f"Deleted {count} old logs without retention policy")
    
    logger.info(f"Total archived logs: {archived_count}")
    return archived_count


@shared_task
def cleanup_audit_trail(days=90):
    """Clean up old audit logs (soft delete/archive)"""
    cutoff = timezone.now() - timedelta(days=days)
    old_logs = AuditLog.objects.filter(timestamp__lt=cutoff)
    count = old_logs.count()
    old_logs.delete()
    logger.info(f"Cleaned up {count} audit logs older than {days} days")
    return count


@shared_task
def generate_audit_report(date_from, date_to, email_to):
    """Generate and email audit report"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    
    logs = AuditLog.objects.filter(
        timestamp__date__gte=date_from,
        timestamp__date__lte=date_to
    )
    
    # Generate statistics
    stats = {
        'total': logs.count(),
        'by_action': dict(logs.values_list('action').annotate(count=models.Count('id'))),
        'by_user': dict(logs.values_list('username').annotate(count=models.Count('id'))[:10]),
    }
    
    # Generate CSV attachment
    # ... (implementation)
    
    send_mail(
        subject=f"Audit Report {date_from} to {date_to}",
        message=render_to_string('audit/email/report.txt', {'stats': stats}),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email_to],
        fail_silently=False,
    )
    
    logger.info(f"Audit report sent to {email_to}")
"""
Management command to expire old applications
Run: python manage.py expire_applications [--days=30]
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.admissions.models import Application
from apps.admissions.constants import ApplicationStatus


class Command(BaseCommand):
    help = 'Expire applications older than specified days'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Days after which to expire')

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        expired = Application.objects.filter(
            status=ApplicationStatus.SUBMITTED,
            submitted_at__lt=cutoff_date
        )
        
        count = expired.count()
        expired.update(status=ApplicationStatus.EXPIRED)
        
        self.stdout.write(
            self.style.SUCCESS(f"Expired {count} applications older than {days} days")
        )
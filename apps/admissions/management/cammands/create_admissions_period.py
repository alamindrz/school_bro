"""
Management command to create a default admissions period
Run: python manage.py create_admissions_period --session=2024/2025 --name="Regular Admission"
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime, timedelta
from apps.corecode.models import AcademicSession
from apps.admissions.models import AdmissionsPeriod


class Command(BaseCommand):
    help = 'Create an admissions period for a specific academic session'
    
    def add_arguments(self, parser):
        parser.add_argument('--session', type=str, required=True, help='Session name (e.g., 2024/2025)')
        parser.add_argument('--name', type=str, default='Regular Admission', help='Period name')
        parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
        parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
        parser.add_argument('--fee', type=int, default=5000, help='Application fee')
        parser.add_argument('--max', type=int, help='Maximum applications (unlimited if not set)')
    
    def handle(self, *args, **options):
        try:
            session = AcademicSession.objects.get(name=options['session'])
        except AcademicSession.DoesNotExist:
            raise CommandError(f"Session '{options['session']}' not found")
        
        # Set default dates if not provided
        start_date = options.get('start')
        if not start_date:
            start_date = timezone.now()
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        
        end_date = options.get('end')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        period = AdmissionsPeriod.objects.create(
            academic_session=session,
            name=options['name'],
            start_date=start_date,
            end_date=end_date,
            application_fee=options['fee'],
            max_applications=options['max'],
            is_active=True
        )
        
        self.stdout.write(self.style.SUCCESS(
            f"Created admissions period: {period.name} for {session.name}"
        ))
        self.stdout.write(f"  Start: {period.start_date}")
        self.stdout.write(f"  End: {period.end_date or 'Open-ended'}")
        self.stdout.write(f"  Fee: ₦{period.application_fee}")
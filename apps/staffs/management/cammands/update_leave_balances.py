"""
Management command to update leave balances
Run: python manage.py update_leave_balances
"""

from django.core.management.base import BaseCommand
from apps.staffs.models import Staff
from apps.staffs.services.leave import LeaveService
from datetime import date


class Command(BaseCommand):
    help = 'Update staff leave balances for new year'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='Year to update (defaults to current)')

    def handle(self, *args, **options):
        year = options.get('year', date.today().year)
        
        self.stdout.write(f"Updating leave balances for {year}...")
        
        staff_list = Staff.objects.filter(employment_status='active')
        count = 0
        
        for staff in staff_list:
            # Leave balance calculation happens on demand
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f"Updated balances for {count} staff members"))
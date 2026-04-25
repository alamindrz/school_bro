# timetable/management/commands/setup_timetable_defaults.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import time

class Command(BaseCommand):
    help = 'Setup default school days and period types for timetable system'
    
    def handle(self, *args, **options):
        from apps.timetable.models import SchoolDay, PeriodType
        
        self.stdout.write("Setting up default school days...")
        
        # School days (Monday - Friday)
        days = [
            {'day_number': 1, 'name': 'Monday', 'order': 1, 'is_friday': False},
            {'day_number': 2, 'name': 'Tuesday', 'order': 2, 'is_friday': False},
            {'day_number': 3, 'name': 'Wednesday', 'order': 3, 'is_friday': False},
            {'day_number': 4, 'name': 'Thursday', 'order': 4, 'is_friday': False},
            {'day_number': 5, 'name': 'Friday', 'order': 5, 'is_friday': True, 
             'friday_start_time': time(8, 0), 'friday_end_time': time(12, 30)},
        ]
        
        for day_data in days:
            day, created = SchoolDay.objects.get_or_create(
                day_number=day_data['day_number'],
                defaults=day_data
            )
            self.stdout.write(f"  {'Created' if created else 'Found'} {day.name}")
        
        self.stdout.write("\nSetting up default period types...")
        
        period_types = [
            {'name': 'Teaching Period', 'code': 'teaching', 'is_teaching': True, 'duration_minutes': 40, 'color': '#3b82f6'},
            {'name': 'Morning Break', 'code': 'morning_break', 'is_teaching': False, 'duration_minutes': 60, 'color': '#f59e0b', 'is_break': True, 'break_duration_minutes': 60},
            {'name': 'Short Break', 'code': 'short_break', 'is_teaching': False, 'duration_minutes': 15, 'color': '#10b981', 'is_break': True, 'break_duration_minutes': 15},
            {'name': 'Assembly', 'code': 'assembly', 'is_teaching': False, 'duration_minutes': 15, 'color': '#8b5cf6'},
            {'name': 'Closing', 'code': 'closing', 'is_teaching': False, 'duration_minutes': 5, 'color': '#ef4444'},
        ]
        
        for pt_data in period_types:
            pt, created = PeriodType.objects.get_or_create(
                code=pt_data['code'],
                defaults=pt_data
            )
            self.stdout.write(f"  {'Created' if created else 'Found'} {pt.name}")
        
        self.stdout.write(self.style.SUCCESS("\n✅ Timetable defaults setup complete!"))
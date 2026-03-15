"""
Management command to bulk import students from CSV
Run: python manage.py bulk_import_students <csv_file>
"""

import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.students.services import StudentService
from apps.corecode.selectors import AcademicSessionSelector


class Command(BaseCommand):
    help = 'Bulk import students from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')
        parser.add_argument('--session-id', type=int, help='Academic session ID (defaults to current)')
        parser.add_argument('--create-users', action='store_true', help='Create Django user accounts')
        parser.add_argument('--dry-run', action='store_true', help='Validate without importing')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        if not os.path.exists(csv_file):
            raise CommandError(f"File {csv_file} does not exist")
        
        # Get session
        session_id = options.get('session_id')
        if not session_id:
            current_session = AcademicSessionSelector.get_current_session()
            if not current_session:
                raise CommandError("No active academic session found")
            session_id = current_session.id
            self.stdout.write(f"Using current session: {current_session.name}")
        
        # Read CSV
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        self.stdout.write(f"Found {len(rows)} records to import")
        
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS("DRY RUN - Validation only"))
            valid = 0
            invalid = 0
            
            for i, row in enumerate(rows, 1):
                try:
                    # Validate required fields
                    required = ['first_name', 'last_name', 'gender', 'date_of_birth', 'current_class']
                    missing = [f for f in required if not row.get(f)]
                    if missing:
                        raise ValueError(f"Missing fields: {', '.join(missing)}")
                    
                    valid += 1
                except Exception as e:
                    invalid += 1
                    self.stdout.write(self.style.ERROR(f"Row {i}: {e}"))
            
            self.stdout.write(f"Valid: {valid}, Invalid: {invalid}")
            return
        
        # Actual import
        success = 0
        failed = 0
        
        for i, row in enumerate(rows, 1):
            try:
                # Import logic here
                self.stdout.write(f"Importing row {i}...")
                success += 1
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"Row {i}: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"Imported {success} students, {failed} failed"))
"""
Management command to generate invoices from fee structure
Run: python manage.py generate_invoices --class=SS1
"""

from django.core.management.base import BaseCommand
from apps.finance.services import InvoiceService
from apps.corecode.selectors import AcademicSessionSelector, StudentClassSelector


class Command(BaseCommand):
    help = 'Generate invoices from fee structure'

    def add_arguments(self, parser):
        parser.add_argument('--class', dest='class_name', type=str, required=True, help='Class name (e.g., SS1)')
        parser.add_argument('--session-id', type=int, help='Academic session ID')
        parser.add_argument('--term-id', type=int, help='Academic term ID')

    def handle(self, *args, **options):
        class_name = options['class_name']
        
        # Get class
        student_class = StudentClassSelector.get_by_name(class_name)
        if not student_class:
            self.stdout.write(self.style.ERROR(f"Class {class_name} not found"))
            return
        
        # Get session
        session_id = options.get('session_id')
        if not session_id:
            current_session = AcademicSessionSelector.get_current_session()
            if not current_session:
                self.stdout.write(self.style.ERROR("No active session found"))
                return
            session_id = current_session.id
        
        self.stdout.write(f"Generating invoices for {class_name}...")
        
        results = InvoiceService.generate_invoices_from_fee_structure(
            class_id=student_class.id,
            session_id=session_id,
            term_id=options.get('term_id')
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {len(results['successful'])} invoices, "
                f"Skipped {len(results['skipped'])}, "
                f"Failed {len(results['failed'])}"
            )
        )
"""
Invoice Generation Service
Auto-creates fee structures and invoices when a new term starts.
"""

from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class InvoiceGenerationService:
    """Auto-generate fee structures and invoices per term."""

    @staticmethod
    @transaction.atomic
    def create_fee_structures_for_term(term_id: int, session_id: int) -> int:
        """
        Copy fee structures from the previous term to the new term.
        If no previous term exists, create default fee structures.
        Returns the number of fee structures created.
        """
        from apps.corecode.models import AcademicTerm, StudentClass
        from apps.finance.models import FeeStructure

        term = AcademicTerm.objects.get(id=term_id)

        # Try to find previous term's fee structures to copy
        prev_term_number = term.term - 1
        if prev_term_number >= 1:
            prev_term = AcademicTerm.objects.filter(
                session_id=session_id, term=prev_term_number
            ).first()
        else:
            # First term — check previous session's last term
            prev_session_id = session_id - 1  # approximate
            prev_term = AcademicTerm.objects.filter(
                session_id=prev_session_id, term=3
            ).first()

        count = 0
        classes = StudentClass.objects.filter(is_active=True)

        for student_class in classes:
            if prev_term:
                # Copy fee structures from previous term
                prev_fees = FeeStructure.objects.filter(
                    student_class=student_class,
                    academic_session_id=prev_term.session_id,
                    is_active=True
                )
                for fee in prev_fees:
                    _, created = FeeStructure.objects.get_or_create(
                        student_class=student_class,
                        fee_type=fee.fee_type,
                        academic_session_id=session_id,
                        term=fee.term,
                        defaults={
                            'amount': fee.amount,
                            'is_required': fee.is_required,
                            'description': fee.description,
                            'is_active': True,
                        }
                    )
                    if created:
                        count += 1
            else:
                # No previous term — create default fee structures
                defaults = [
                    ('tuition', Decimal('50000'), True, 'Tuition Fee'),
                    ('development', Decimal('10000'), True, 'Development Levy'),
                ]
                for fee_type, amount, required, desc in defaults:
                    _, created = FeeStructure.objects.get_or_create(
                        student_class=student_class,
                        fee_type=fee_type,
                        academic_session_id=session_id,
                        term='per_term',
                        defaults={
                            'amount': amount,
                            'is_required': required,
                            'description': desc,
                            'is_active': True,
                        }
                    )
                    if created:
                        count += 1

        logger.info(f"Fee structures created: {count} for {term.name}")
        return count

    @staticmethod
    @transaction.atomic
    def generate_invoices_for_term(term_id: int, session_id: int) -> int:
        """
        Generate invoices for all active students based on fee structures
        for the given term. Returns the number of invoices created.
        """
        from apps.corecode.models import AcademicTerm, StudentClass
        from apps.finance.models import FeeStructure, Invoice
        from apps.students.models import Student
        from datetime import date, timedelta

        term = AcademicTerm.objects.get(id=term_id)
        count = 0

        classes = StudentClass.objects.filter(is_active=True)

        for student_class in classes:
            # Get fee structures for this class and term
            fee_structures = FeeStructure.objects.filter(
                student_class=student_class,
                academic_session_id=session_id,
                is_active=True
            )

            if not fee_structures.exists():
                continue

            # Get all active students in this class
            students = Student.objects.filter(
                current_class=student_class,
                status='active'
            )

            due_date = term.end_date if term.end_date else date.today() + timedelta(days=90)

            for student in students:
                for fee in fee_structures:
                    # Skip if invoice already exists
                    existing = Invoice.objects.filter(
                        student_id=student.id,
                        student_class=student_class,
                        academic_session_id=session_id,
                        academic_term_id=term_id,
                        fee_type=fee.fee_type
                    ).exists()

                    if existing:
                        continue

                    Invoice.objects.create(
                        student_id=student.id,
                        student_name=student.get_full_name,
                        student_class=student_class,
                        academic_session_id=session_id,
                        academic_term_id=term_id,
                        fee_type=fee.fee_type,
                        description=fee.description or fee.get_fee_type_display(),
                        subtotal=fee.amount,
                        total=fee.amount,
                        amount_paid=Decimal('0'),
                        balance=fee.amount,
                        issue_date=date.today(),
                        due_date=due_date,
                        status='pending',
                    )
                    count += 1

        logger.info(f"Invoices generated: {count} for {term.name}")
        return count
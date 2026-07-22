"""
Invoice Service - Core invoicing business logic
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, List, Dict, Any
from decimal import Decimal
import logging

from ..models import Invoice, FeeStructure
from ..constants import InvoiceStatus, FeeType, FeeTerm, DEFAULT_DUE_DAYS
from ..exceptions import (
    InvoiceNotFoundError,
    DuplicateInvoiceError,
    InvalidInvoiceStatusError,
    StudentNotEligibleError,
    FeeStructureError,
)
from ..selectors import InvoiceSelector, FeeStructureSelector
from apps.corecode.services import SystemLogService

from apps.corecode.selectors import AcademicSessionSelector, AcademicTermSelector
from apps.corecode.selectors import StudentClassSelector
from apps.corecode.models import SystemLog
from apps.students.selectors import StudentSelector  # READ only, no WRITE

logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Invoice business operations
    Single source of truth for invoice management
    """
    
    @staticmethod
    @transaction.atomic
    def create_invoice(
        student_id: int,
        student_name: str,
        class_id: int,
        fee_type: str,
        amount: Decimal,
        description: str = "",
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        due_date: Optional[str] = None,
        created_by_id: Optional[int] = None
    ) -> Invoice:
        
        print(f"student_id: {student_id}")
        print(f"student_name: {student_name}")
        print(f"class_id: {class_id}")
        print(f"fee_type: {fee_type}")
        print(f"amount: {amount}")
        
        # Get academic context
        if not session_id:
            current_session = AcademicSessionSelector.get_current_session()
            if not current_session:
                raise ValidationError("No active academic session configured")
            session_id = current_session.id
        
        print(f"session_id: {session_id}")
        
        # Validate student exists ONLY if student_id is provided
        if student_id is not None:
            student = StudentSelector.get_by_id(student_id)
            if not student:
                raise StudentNotEligibleError(f"Student with id {student_id} not found")
            print("Student validation passed")
        
        # Validate class
        student_class = StudentClassSelector.get_by_id(class_id)
        if not student_class:
            raise ValidationError(f"Class with id {class_id} not found")
        print("Class validation passed")
        
        # Check for duplicate invoice (skip if no student_id)
        if student_id is not None:
            existing = Invoice.objects.filter(
                student_id=student_id,
                academic_session_id=session_id,
                academic_term_id=term_id,
                fee_type=fee_type
            ).exists()
            
            if existing:
                raise DuplicateInvoiceError(
                    f"An invoice for {fee_type} already exists for this student in this session/term"
                )
        
        # Generate invoice number
        invoice_number = InvoiceService._generate_invoice_number()
        
        # Calculate due date
        if not due_date:
            due_date = timezone.now().date() + timezone.timedelta(days=DEFAULT_DUE_DAYS)
        print(f"due_date: {due_date}")
        
        # Create invoice
        print("Creating invoice object...")
        invoice = Invoice.objects.create(
            invoice_number=invoice_number,
            student_id=student_id,
            student_name=student_name,
            student_class_id=class_id,
            academic_session_id=session_id,
            academic_term_id=term_id,
            fee_type=fee_type,
            description=description or f"{dict(FeeType.CHOICES).get(fee_type, fee_type)} Fee",
            subtotal=amount,
            total=amount,
            balance=amount,
            due_date=due_date,
            status=InvoiceStatus.PENDING,
            created_by_id=created_by_id
        )
        print(f"Invoice created with ID: {invoice.id}")
        
        # Log creation
        try:
            SystemLogService.log_action(
                user=created_by_id,
                action=SystemLog.ActionType.CREATE,
                app_label=SystemLog.AppLabel.FINANCE,
                model_name='Invoice',
                object_id=str(invoice.id),
                object_repr=invoice.invoice_number,
                changes={
                    'student_id': student_id if student_id else 'PENDING_APPLICATION',
                    'student_name': student_name,
                    'amount': float(amount),
                    'fee_type': fee_type,
                }
            )
            print("Logging succeeded")
        except Exception as e:
            print(f"Logging failed: {e}")
            # Don't fail the whole operation for logging error
        
        return invoice


    @staticmethod
    @transaction.atomic
    def update_invoice_student_id(
        invoice_id: int,
        student_id: int,
        student_name: str = None
    ) -> Invoice:
        """
        Update an invoice with the actual student ID after enrollment
        Used for application fees that were created before the student existed
        """
        try:
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")
        
        # Verify the invoice is for an application fee (student_id was None)
        if invoice.student_id is not None:
            logger.warning(f"Invoice {invoice.invoice_number} already has student_id {invoice.student_id}")
            return invoice
        
        # Update the invoice
        invoice.student_id = student_id
        if student_name:
            invoice.student_name = student_name
        invoice.save(update_fields=['student_id', 'student_name', 'updated_at'])
        
        logger.info(f"Updated invoice {invoice.invoice_number} with student_id {student_id}")
        return invoice
    
    @staticmethod
    @transaction.atomic
    def bulk_create_invoices(
        student_ids: List[int],
        fee_type: str,
        amount: Decimal,
        description: str = "",
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        due_date: Optional[str] = None,
        created_by_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Bulk create invoices for multiple students
        Used for mass invoicing (e.g., tuition fees for entire class)
        """
        results = {
            'successful': [],
            'failed': [],
            'skipped': [],
        }
        
        # Get academic context
        if not session_id:
            current_session = AcademicSessionSelector.get_current_session()
            if not current_session:
                raise ValidationError("No active academic session configured")
            session_id = current_session.id
        
        # Get student details
        from apps.students.selectors import StudentSelector
        students = {}
        for student_id in student_ids:
            student = StudentSelector.get_by_id(student_id)
            if student:
                students[student_id] = student
        
        for student_id in student_ids:
            try:
                # Skip if student not found
                if student_id not in students:
                    results['failed'].append({
                        'student_id': student_id,
                        'reason': 'Student not found'
                    })
                    continue
                
                student = students[student_id]
                
                # Check for duplicate
                existing = Invoice.objects.filter(
                    student_id=student_id,
                    academic_session_id=session_id,
                    academic_term_id=term_id,
                    fee_type=fee_type
                ).exists()
                
                if existing:
                    results['skipped'].append({
                        'student_id': student_id,
                        'student_name': student['full_name'],
                        'reason': 'Invoice already exists'
                    })
                    continue
                
                # Create invoice
                invoice = InvoiceService.create_invoice(
                    student_id=student_id,
                    student_name=student['full_name'],
                    class_id=student['current_class']['id'],
                    fee_type=fee_type,
                    amount=amount,
                    description=description,
                    session_id=session_id,
                    term_id=term_id,
                    due_date=due_date,
                    created_by_id=created_by_id
                )
                
                results['successful'].append({
                    'student_id': student_id,
                    'student_name': student['full_name'],
                    'invoice_id': invoice.id,
                    'invoice_number': invoice.invoice_number,
                })
                
            except Exception as e:
                results['failed'].append({
                    'student_id': student_id,
                    'reason': str(e)
                })
        
        # Log bulk operation
        SystemLogService.log_action(
            user=created_by_id,
            action=SystemLog.ActionType.CREATE,
            app_label=SystemLog.AppLabel.FINANCE,
            model_name='Invoice',
            object_id='bulk',
            object_repr=f'Bulk create {len(results["successful"])} invoices',
            changes={
                'successful': len(results['successful']),
                'failed': len(results['failed']),
                'skipped': len(results['skipped']),
                'fee_type': fee_type,
                'amount': float(amount),
            }
        )
        
        logger.info(
            f"Bulk invoice creation: {len(results['successful'])} successful, "
            f"{len(results['failed'])} failed, {len(results['skipped'])} skipped"
        )
        
        return results
    
    @staticmethod
    @transaction.atomic
    def generate_invoices_from_fee_structure(
        class_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        created_by_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate invoices for an entire class based on fee structure
        This is the AUTOMATED invoicing method
        """
        # Get fee structure for this class
        fee_structures = FeeStructureSelector.get_for_class(
            class_id=class_id,
            session_id=session_id,
            active_only=True
        )
        
        if not fee_structures:
            raise FeeStructureError(f"No fee structure defined for class {class_id}")
        
        # Get all active students in this class
        from apps.students.selectors import StudentSelector
        students = StudentSelector.get_class_students(
            class_id=class_id,
            academic_session_id=session_id,
            include_inactive=False
        )
        
        if not students:
            return {
                'successful': [],
                'failed': [],
                'skipped': [],
                'message': 'No active students found in this class'
            }
        
        results = {
            'successful': [],
            'failed': [],
            'skipped': [],
            'fee_structures': len(fee_structures),
            'student_count': len(students),
        }
        
        # For each student, generate invoices for each fee type
        for student in students:
            student_id = student['id']
            student_name = student['name']
            
            for fee_struct in fee_structures:
                try:
                    # Check for existing invoice
                    existing = Invoice.objects.filter(
                        student_id=student_id,
                        academic_session_id=session_id,
                        academic_term_id=term_id,
                        fee_type=fee_struct['fee_type']
                    ).exists()
                    
                    if existing:
                        results['skipped'].append({
                            'student_id': student_id,
                            'student_name': student_name,
                            'fee_type': fee_struct['fee_type_display'],
                            'reason': 'Invoice already exists'
                        })
                        continue
                    
                    # Determine if this fee applies to this term
                    if fee_struct['term'] == 'per_term' and not term_id:
                        # Skip - need term for per-term fees
                        continue
                    
                    if fee_struct['term'] == 'per_session' and term_id:
                        # For per-session fees, only generate once per session
                        # We'll generate only if no term specified or first term
                        if term_id and AcademicTermSelector.get_by_id(term_id).term != 1:
                            continue
                    
                    # Create invoice
                    invoice = InvoiceService.create_invoice(
                        student_id=student_id,
                        student_name=student_name,
                        class_id=class_id,
                        fee_type=fee_struct['fee_type'],
                        amount=Decimal(str(fee_struct['amount'])),
                        description=fee_struct.get('description', ''),
                        session_id=session_id,
                        term_id=term_id if fee_struct['term'] == 'per_term' else None,
                        created_by_id=created_by_id
                    )
                    
                    results['successful'].append({
                        'student_id': student_id,
                        'student_name': student_name,
                        'fee_type': fee_struct['fee_type_display'],
                        'invoice_id': invoice.id,
                        'invoice_number': invoice.invoice_number,
                        'amount': float(invoice.total),
                    })
                    
                except Exception as e:
                    results['failed'].append({
                        'student_id': student_id,
                        'student_name': student_name,
                        'fee_type': fee_struct['fee_type_display'],
                        'reason': str(e)
                    })
        
        return results
    
    @staticmethod
    @transaction.atomic
    def update_invoice_status(
        invoice_id: int,
        new_status: str,
        updated_by_id: Optional[int] = None
    ) -> Invoice:
        """
        Update invoice status with validation
        """
        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")
        
        # Validate transition
        if not invoice.can_transition_to(new_status):
            raise InvalidInvoiceStatusError(
                f"Cannot transition from {invoice.status} to {new_status}"
            )
        
        old_status = invoice.status
        invoice.status = new_status
        invoice.save(update_fields=['status', 'updated_at'])
        
        # Log status change
        SystemLogService.log_action(
            user=updated_by_id,
            action=SystemLog.ActionType.UPDATE,
            app_label=SystemLog.AppLabel.FINANCE,
            model_name='Invoice',
            object_id=str(invoice.id),
            object_repr=invoice.invoice_number,
            changes={
                'status': f'{old_status} → {new_status}'
            }
        )
        
        logger.info(f"Invoice {invoice.invoice_number} status updated: {old_status} → {new_status}")
        return invoice
    
    @staticmethod
    def _generate_invoice_number() -> str:
        """Generate unique invoice number"""
        year = timezone.now().year
        prefix = f"INV-{year}"
        
        last_invoice = Invoice.objects.filter(
            invoice_number__startswith=prefix
        ).order_by('-invoice_number').first()
        
        if last_invoice:
            last_num = int(last_invoice.invoice_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}-{new_num:04d}"
    
    @staticmethod
    def mark_overdue_invoices() -> int:
        """
        Mark overdue invoices as OVERDUE
        Run daily via celery beat
        """
        today = timezone.now().date()
        
        overdue_invoices = Invoice.objects.filter(
            status__in=[InvoiceStatus.PENDING, InvoiceStatus.PARTIAL],
            due_date__lt=today,
            balance__gt=0
        )
        
        count = overdue_invoices.update(
            status=InvoiceStatus.OVERDUE,
            updated_at=timezone.now()
        )
        
        logger.info(f"Marked {count} invoices as overdue")
        return count
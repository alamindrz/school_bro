"""
Finance App Test Factories
"""

import factory
from factory.django import DjangoModelFactory
from factory.faker import Faker
from decimal import Decimal
from django.utils import timezone
from datetime import date, timedelta
import random

from apps.finance.models import FeeStructure, Invoice, Payment, FeeWaiver
from apps.finance.constants import (
    InvoiceStatus, PaymentStatus, PaymentMethod,
    FeeType, FeeTerm, DiscountType
)
from apps.corecode.tests.factories import (
    StudentClassFactory, AcademicSessionFactory,
    AcademicTermFactory, UserFactory
)
from apps.students.tests.factories import StudentFactory


class FeeStructureFactory(DjangoModelFactory):
    """Factory for FeeStructure model"""
    class Meta:
        model = FeeStructure
    
    student_class = factory.SubFactory(StudentClassFactory)
    fee_type = factory.Iterator([ft[0] for ft in FeeType.CHOICES])
    amount = factory.Iterator([5000, 10000, 15000, 20000, 25000, 30000])
    term = factory.Iterator([ft[0] for ft in FeeTerm.CHOICES])
    academic_session = factory.SubFactory(AcademicSessionFactory)
    description = Faker('sentence')
    is_active = True
    created_by = factory.SubFactory(UserFactory)


class InvoiceFactory(DjangoModelFactory):
    """Factory for Invoice model"""
    class Meta:
        model = Invoice
    
    invoice_number = factory.Sequence(lambda n: f"INV-2024-{n:04d}")
    student_id = factory.Sequence(lambda n: n + 1)
    student_name = factory.LazyFunction(lambda: StudentFactory().full_name)
    student_class = factory.SubFactory(StudentClassFactory)
    academic_session = factory.SubFactory(AcademicSessionFactory)
    academic_term = factory.SubFactory(AcademicTermFactory)
    fee_type = factory.Iterator([ft[0] for ft in FeeType.CHOICES])
    description = Faker('sentence')
    subtotal = factory.LazyAttribute(lambda obj: Decimal(str(random.randint(5000, 50000))))
    discount_type = None
    discount_value = 0
    discount_amount = 0
    total = factory.LazyAttribute(lambda obj: obj.subtotal)
    amount_paid = 0
    balance = factory.LazyAttribute(lambda obj: obj.total)
    status = InvoiceStatus.PENDING
    issue_date = factory.LazyFunction(date.today)
    due_date = factory.LazyAttribute(lambda obj: obj.issue_date + timedelta(days=30))
    has_waiver = False
    waiver_amount = 0
    waiver_reason = ""
    created_by = factory.SubFactory(UserFactory)


class PaymentFactory(DjangoModelFactory):
    """Factory for Payment model"""
    class Meta:
        model = Payment
    
    transaction_id = factory.Sequence(lambda n: f"TXN-2024-{n:06d}")
    invoice = factory.SubFactory(InvoiceFactory)
    amount = factory.LazyAttribute(lambda obj: obj.invoice.balance)
    payment_method = factory.Iterator([pm[0] for pm in PaymentMethod.CHOICES])
    status = PaymentStatus.COMPLETED
    gateway_reference = factory.Sequence(lambda n: f"PS-{n:010d}")
    gateway_response = {}
    payment_date = factory.LazyFunction(timezone.now)
    notes = Faker('sentence')
    receipt_number = factory.Sequence(lambda n: f"RCP-2024-{n:04d}")
    received_by = factory.SubFactory(UserFactory)


class FeeWaiverFactory(DjangoModelFactory):
    """Factory for FeeWaiver model"""
    class Meta:
        model = FeeWaiver
    
    invoice = factory.SubFactory(InvoiceFactory)
    amount = factory.LazyAttribute(lambda obj: obj.invoice.balance * Decimal('0.5'))
    reason = Faker('paragraph')
    status = 'pending'
    requested_by = factory.SubFactory(UserFactory)
    approval_notes = ""


# Helper functions
def create_paid_invoice(**kwargs):
    """Create a fully paid invoice"""
    invoice = InvoiceFactory(**kwargs)
    payment = PaymentFactory(
        invoice=invoice,
        amount=invoice.total,
        status=PaymentStatus.COMPLETED
    )
    invoice.amount_paid = invoice.total
    invoice.balance = 0
    invoice.status = InvoiceStatus.PAID
    invoice.save()
    return invoice, payment


def create_partial_invoice(paid_amount=None, **kwargs):
    """Create a partially paid invoice"""
    invoice = InvoiceFactory(**kwargs)
    if not paid_amount:
        paid_amount = invoice.total * Decimal('0.5')
    
    payment = PaymentFactory(
        invoice=invoice,
        amount=paid_amount,
        status=PaymentStatus.COMPLETED
    )
    invoice.amount_paid = paid_amount
    invoice.balance = invoice.total - paid_amount
    invoice.status = InvoiceStatus.PARTIAL
    invoice.save()
    return invoice, payment


def create_overdue_invoice(**kwargs):
    """Create an overdue invoice"""
    invoice = InvoiceFactory(
        due_date=date.today() - timedelta(days=10),
        status=InvoiceStatus.PENDING,
        **kwargs
    )
    return invoice
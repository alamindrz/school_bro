"""
Admissions Test Factories
"""

import factory
from factory.django import DjangoModelFactory
from factory.faker import Faker
from django.utils import timezone
from datetime import date, timedelta
import random

from apps.admissions.models import Application, ApplicationPayment, ApplicationDocument, ApplicationNote
from apps.admissions.constants import ApplicationStatus, ApplicationType, PaymentStatus, PaymentMethod, DocumentType
from apps.corecode.tests.factories import AcademicSessionFactory, StudentClassFactory, UserFactory
from apps.students.tests.factories import StudentFactory


class ApplicationFactory(DjangoModelFactory):
    """Factory for Application model"""
    class Meta:
        model = Application
    
    # Application number will be auto-generated on save
    application_number = factory.Sequence(lambda n: f"APP-2024-{n:04d}")
    
    # Personal info
    first_name = Faker('first_name')
    last_name = Faker('last_name')
    middle_name = Faker('first_name')
    gender = factory.Iterator(['M', 'F'])
    date_of_birth = factory.LazyFunction(
        lambda: date.today() - timedelta(days=random.randint(10*365, 17*365))
    )
    
    # Contact
    email = factory.LazyAttribute(lambda obj: f"{obj.first_name.lower()}.{obj.last_name.lower()}@example.com")
    phone = factory.Iterator(['08012345678', '08123456789', '09012345678'])
    alternate_phone = factory.Iterator(['', '07012345678'])
    address = Faker('address')
    city = Faker('city')
    state_of_origin = factory.Iterator(['Lagos', 'Abuja', 'Kano', 'Rivers', 'Oyo'])
    nationality = 'Nigerian'
    
    # Academic
    applying_for_class = factory.SubFactory(StudentClassFactory)
    application_type = factory.Iterator([t[0] for t in ApplicationType.CHOICES])
    previous_school = factory.Faker('company')
    previous_class = factory.Iterator(['SS1', 'SS2', 'JSS1', 'JSS2', 'JSS3', 'Primary 6'])
    
    # Guardian
    guardian_first_name = Faker('first_name')
    guardian_last_name = Faker('last_name')
    guardian_relationship = factory.Iterator(['father', 'mother', 'guardian'])
    guardian_phone = factory.Iterator(['08012345678', '08123456789'])
    guardian_email = factory.LazyAttribute(
        lambda obj: f"{obj.guardian_first_name.lower()}.{obj.guardian_last_name.lower()}@parent.com"
    )
    guardian_address = Faker('address')
    guardian_occupation = Faker('job')
    
    # Context
    applying_for_session = factory.SubFactory(AcademicSessionFactory)
    
    # Status
    status = ApplicationStatus.DRAFT
    submitted_at = None
    reviewed_by = None
    reviewed_at = None
    review_notes = ''
    
    # Enrollment tracking
    enrolled_student_id = None
    enrolled_at = None
    
    # Metadata
    created_by = factory.SubFactory(UserFactory)
    
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override to ensure application_number is set"""
        if 'application_number' not in kwargs:
            # Generate unique application number
            year = timezone.now().year
            last_app = Application.objects.filter(
                application_number__startswith=f"APP-{year}"
            ).order_by('-application_number').first()
            
            if last_app:
                last_num = int(last_app.application_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            kwargs['application_number'] = f"APP-{year}-{new_num:04d}"
        
        return super()._create(model_class, *args, **kwargs)


class ApplicationPaymentFactory(DjangoModelFactory):
    """Factory for ApplicationPayment model"""
    class Meta:
        model = ApplicationPayment
    
    application = factory.SubFactory(ApplicationFactory)
    amount = factory.Iterator([5000, 10000, 15000])
    payment_method = PaymentMethod.PAYSTACK
    status = PaymentStatus.PENDING
    paystack_reference = factory.Sequence(lambda n: f"PAYSTACK-{n:010d}")
    paystack_access_code = factory.Sequence(lambda n: f"ACCESS-{n:010d}")
    paystack_response = {}
    transaction_date = None
    verified_at = None
    created_by = factory.SubFactory(UserFactory)


class ApplicationDocumentFactory(DjangoModelFactory):
    """Factory for ApplicationDocument model"""
    class Meta:
        model = ApplicationDocument
    
    application = factory.SubFactory(ApplicationFactory)
    document_type = factory.Iterator([d[0] for d in DocumentType.CHOICES])
    file = factory.django.FileField(filename='test_document.pdf')
    filename = 'test_document.pdf'
    file_size = 1024 * 50  # 50KB
    uploaded_by = factory.SubFactory(UserFactory)


class ApplicationNoteFactory(DjangoModelFactory):
    """Factory for ApplicationNote model"""
    class Meta:
        model = ApplicationNote
    
    application = factory.SubFactory(ApplicationFactory)
    note = Faker('paragraph')
    created_by = factory.SubFactory(UserFactory)


# Helper functions for creating test data
def create_submitted_application(**kwargs):
    """Create a submitted application with payment"""
    app = ApplicationFactory(
        status=ApplicationStatus.SUBMITTED,
        submitted_at=timezone.now(),
        **kwargs
    )
    
    # Create payment record
    ApplicationPaymentFactory(
        application=app,
        status=PaymentStatus.COMPLETED,
        transaction_date=timezone.now(),
        verified_at=timezone.now()
    )
    
    return app


def create_approved_application(**kwargs):
    """Create an approved application ready for enrollment"""
    app = ApplicationFactory(
        status=ApplicationStatus.APPROVED,
        submitted_at=timezone.now() - timedelta(days=2),
        reviewed_at=timezone.now() - timedelta(days=1),
        reviewed_by=UserFactory(),
        review_notes='Approved after review',
        **kwargs
    )
    
    # Create payment record
    ApplicationPaymentFactory(
        application=app,
        status=PaymentStatus.COMPLETED,
        transaction_date=timezone.now() - timedelta(days=2),
        verified_at=timezone.now() - timedelta(days=2)
    )
    
    return app


def create_enrolled_application(**kwargs):
    """Create an enrolled application (already converted to student)"""
    student = StudentFactory()
    
    app = ApplicationFactory(
        status=ApplicationStatus.ENROLLED,
        submitted_at=timezone.now() - timedelta(days=10),
        reviewed_at=timezone.now() - timedelta(days=8),
        reviewed_by=UserFactory(),
        enrolled_student_id=student.id,
        enrolled_at=timezone.now() - timedelta(days=5),
        **kwargs
    )
    
    # Create payment record
    ApplicationPaymentFactory(
        application=app,
        status=PaymentStatus.COMPLETED,
        transaction_date=timezone.now() - timedelta(days=9),
        verified_at=timezone.now() - timedelta(days=9)
    )
    
    return app
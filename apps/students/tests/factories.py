"""
Test Data Factories
DEPENDS ON: students/models.py, corecode/factories.py (to be created)
"""

import factory
from factory.django import DjangoModelFactory
from factory.faker import Faker
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import date, timedelta
import random

from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass
from apps.corecode.constants import NigerianClassLevel, EducationLevel, TermType
from apps.students.models import Student, Guardian, StudentHistory
from apps.students.constants import StudentStatus, StudentCreationMethod, GuardianRelationship

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for Django User model"""
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = Faker('first_name')
    last_name = Faker('last_name')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_active = True


class AcademicSessionFactory(DjangoModelFactory):
    """Factory for AcademicSession"""
    class Meta:
        model = AcademicSession
        django_get_or_create = ['name', 'code']
    
    name = factory.Sequence(lambda n: f'{2020 + n}/{2021 + n}')
    code = factory.LazyAttribute(lambda obj: obj.name.replace('/', ''))
    start_date = factory.LazyFunction(lambda: date(date.today().year, 9, 1))
    end_date = factory.LazyAttribute(lambda obj: date(obj.start_date.year + 1, 8, 31))
    is_current = False


class StudentClassFactory(DjangoModelFactory):
    """Factory for StudentClass"""
    class Meta:
        model = StudentClass
        django_get_or_create = ['name']
    
    name = NigerianClassLevel.SS_1
    display_name = factory.LazyAttribute(lambda obj: dict(NigerianClassLevel.CHOICES).get(obj.name, obj.name))
    education_level = EducationLevel.SSS
    max_students = 45
    sort_order = factory.Sequence(lambda n: n)
    is_active = True


class StudentFactory(DjangoModelFactory):
    """Factory for Student model"""
    class Meta:
        model = Student
    
    # Core identity
    admission_number = factory.Sequence(lambda n: f'2024/SS1/{n:03d}')
    user = factory.SubFactory(UserFactory)
    
    # Personal info
    first_name = Faker('first_name')
    last_name = Faker('last_name')
    middle_name = Faker('first_name')
    gender = factory.Iterator(['M', 'F'])
    date_of_birth = factory.LazyFunction(
        lambda: date.today() - timedelta(days=random.randint(15*365, 17*365))
    )
    
    # Contact
    email = factory.LazyAttribute(lambda obj: f'{obj.first_name.lower()}.{obj.last_name.lower()}@student.edu')
    phone = factory.Iterator(['08012345678', '08123456789', '09012345678'])
    address = Faker('address')
    city = Faker('city')
    state_of_origin = factory.Iterator(['Lagos', 'Abuja', 'Kano', 'Rivers', 'Oyo'])
    
    # Academic
    current_class = factory.SubFactory(StudentClassFactory)
    enrollment_date = factory.LazyFunction(date.today)
    enrollment_session = factory.SubFactory(AcademicSessionFactory)
    
    # Status
    status = StudentStatus.ACTIVE
    created_via = StudentCreationMethod.MANUAL
    created_by = factory.SubFactory(UserFactory)
    
    # Medical
    blood_group = factory.Iterator(['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'])
    medical_notes = Faker('text', max_nb_chars=200)
    has_special_needs = False
    
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override to handle admission number generation"""
        if 'admission_number' not in kwargs:
            # Generate admission number
            from apps.students.services.admission_number import AdmissionNumberService
            session = kwargs.get('enrollment_session')
            student_class = kwargs.get('current_class')
            if session and student_class:
                kwargs['admission_number'] = AdmissionNumberService.generate_admission_number(
                    class_name=student_class.name,
                    session_code=session.code
                )
        return super()._create(model_class, *args, **kwargs)


class GuardianFactory(DjangoModelFactory):
    """Factory for Guardian model"""
    class Meta:
        model = Guardian
    
    student = factory.SubFactory(StudentFactory)
    first_name = Faker('first_name')
    last_name = Faker('last_name')
    relationship = factory.Iterator([
        GuardianRelationship.FATHER,
        GuardianRelationship.MOTHER,
        GuardianRelationship.GUARDIAN
    ])
    email = factory.LazyAttribute(
        lambda obj: f'{obj.first_name.lower()}.{obj.last_name.lower()}@parent.com'
    )
    phone = factory.Iterator(['08012345678', '08123456789'])
    alternate_phone = factory.Iterator(['', '09012345678'])
    address = Faker('address')
    occupation = Faker('job')
    employer = Faker('company')
    is_primary = True
    is_emergency_contact = True


class StudentHistoryFactory(DjangoModelFactory):
    """Factory for StudentHistory model"""
    class Meta:
        model = StudentHistory
    
    student = factory.SubFactory(StudentFactory)
    academic_session = factory.SubFactory(AcademicSessionFactory)
    term = factory.Iterator([1, 2, 3])
    class_at_time = factory.SubFactory(StudentClassFactory)
    status_at_time = StudentStatus.ACTIVE
    action = factory.Iterator(['ENROLLED', 'PROMOTED', 'STATUS_CHANGE'])
    previous_class = None
    notes = Faker('sentence')
    performed_by = factory.SubFactory(UserFactory)
    performed_at = factory.LazyFunction(timezone.now)


class AcademicTermFactory(DjangoModelFactory):
    """Factory for AcademicTerm"""
    class Meta:
        model = AcademicTerm
    
    session = factory.SubFactory(AcademicSessionFactory)
    term = factory.Iterator([1, 2, 3])
    name = factory.LazyAttribute(
        lambda obj: f"{dict(TermType.CHOICES)[obj.term]} {obj.session.name}"
    )
    is_current = False
    start_date = factory.LazyAttribute(
        lambda obj: obj.session.start_date + timedelta(days=120 * (obj.term - 1))
    )
    end_date = factory.LazyAttribute(
        lambda obj: obj.start_date + timedelta(days=110)
    )


# Bulk creation helpers
def create_nigerian_class_structure():
    """Create all Nigerian 6-3-3-4 classes"""
    from apps.corecode.services import StudentClassService
    return StudentClassService.bulk_create_nigerian_classes()


def create_current_academic_session():
    """Create a current academic session with terms"""
    session = AcademicSessionFactory(
        name=f"{date.today().year}/{date.today().year + 1}",
        code=f"{date.today().year}{date.today().year + 1}",
        is_current=True
    )
    
    # Create terms
    for term_num in [1, 2, 3]:
        AcademicTermFactory(
            session=session,
            term=term_num,
            is_current=(term_num == 1)
        )
    
    return session
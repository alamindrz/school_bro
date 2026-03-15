"""
Results App Test Factories
"""

import factory
from factory.django import DjangoModelFactory
from factory.faker import Faker
from django.utils import timezone
import random

from apps.results.models import (
    Subject, ResultSheet, ResultSheetSubject,
    Result, ResultComment, CumulativeRecord
)
from apps.results.constants import (
    SubjectType, ResultStatus, GradeSystem,
    RemarkType
)
from apps.corecode.tests.factories import (
    StudentClassFactory, AcademicSessionFactory,
    AcademicTermFactory, UserFactory
)
from apps.students.tests.factories import StudentFactory


class SubjectFactory(DjangoModelFactory):
    """Factory for Subject model"""
    class Meta:
        model = Subject

    name = factory.Sequence(lambda n: f"Subject {n}")
    code = factory.Sequence(lambda n: f"SUB{n:03d}")
    subject_type = factory.Iterator([st[0] for st in SubjectType.CHOICES])
    description = Faker('sentence')
    is_active = True
    is_nigerian_core = factory.Faker('boolean')

    @factory.post_generation
    def offered_in_classes(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for class_obj in extracted:
                self.offered_in_classes.add(class_obj)


class ResultSheetFactory(DjangoModelFactory):
    """Factory for ResultSheet model"""
    class Meta:
        model = ResultSheet

    sheet_number = factory.Sequence(lambda n: f"RS-{n:06d}")
    student_class = factory.SubFactory(StudentClassFactory)
    academic_session = factory.SubFactory(AcademicSessionFactory)
    academic_term = factory.SubFactory(AcademicTermFactory)
    status = ResultStatus.DRAFT
    created_by = factory.SubFactory(UserFactory)


class ResultSheetSubjectFactory(DjangoModelFactory):
    """Factory for ResultSheetSubject model"""
    class Meta:
        model = ResultSheetSubject

    result_sheet = factory.SubFactory(ResultSheetFactory)
    subject = factory.SubFactory(SubjectFactory)
    teacher_name = Faker('name')
    pass_mark = 40


class ResultFactory(DjangoModelFactory):
    """Factory for Result model"""
    class Meta:
        model = Result

    result_sheet = factory.SubFactory(ResultSheetFactory)
    subject = factory.SubFactory(SubjectFactory)
    student_id = factory.Sequence(lambda n: n + 1)
    student_name = factory.LazyFunction(lambda: StudentFactory().full_name)

    # Random scores
    ca1_score = factory.LazyFunction(lambda: random.randint(60, 100))
    ca2_score = factory.LazyFunction(lambda: random.randint(60, 100))
    ca3_score = factory.LazyFunction(lambda: random.randint(60, 100))
    exam_score = factory.LazyFunction(lambda: random.randint(50, 100))
    practical_score = factory.LazyFunction(lambda: random.randint(60, 100) if random.choice([True, False]) else None)
    project_score = factory.LazyFunction(lambda: random.randint(60, 100) if random.choice([True, False]) else None)

    entered_by = factory.SubFactory(UserFactory)


class ResultCommentFactory(DjangoModelFactory):
    """Factory for ResultComment model"""
    class Meta:
        model = ResultComment

    result_sheet = factory.SubFactory(ResultSheetFactory)
    student_id = factory.Sequence(lambda n: n + 1)
    student_name = Faker('name')
    teacher_comment = Faker('paragraph')
    class_teacher_comment = Faker('paragraph')
    principal_comment = Faker('paragraph')
    next_term_recommendation = Faker('sentence')
    created_by = factory.SubFactory(UserFactory)


class CumulativeRecordFactory(DjangoModelFactory):
    """Factory for CumulativeRecord model"""
    class Meta:
        model = CumulativeRecord

    student_id = factory.Sequence(lambda n: n + 1)
    student_name = Faker('name')
    academic_session = factory.SubFactory(AcademicSessionFactory)

    term1_average = factory.LazyFunction(lambda: random.uniform(60, 90))
    term2_average = factory.LazyFunction(lambda: random.uniform(60, 90))
    term3_average = factory.LazyFunction(lambda: random.uniform(60, 90))
    session_average = factory.LazyAttribute(lambda obj: (
        (obj.term1_average + obj.term2_average + obj.term3_average) / 3
        if all([obj.term1_average, obj.term2_average, obj.term3_average])
        else None
    ))
    promoted_to_next_class = factory.Faker('boolean')


# Helper functions
def create_complete_result_sheet(**kwargs):
    """Create a result sheet with subjects and sample results"""
    sheet = ResultSheetFactory(**kwargs)

    # Add subjects
    subjects = SubjectFactory.create_batch(5)
    for subject in subjects:
        ResultSheetSubjectFactory(
            result_sheet=sheet,
            subject=subject,
            teacher_name=Faker('name').generate()
        )

    # Add students
    students = StudentFactory.create_batch(10)
    for student in students:
        for subject in subjects:
            ResultFactory(
                result_sheet=sheet,
                subject=subject,
                student_id=student.id,
                student_name=student.full_name
            )

    return sheet


def create_published_sheet(**kwargs):
    """Create a published result sheet"""
    sheet = create_complete_result_sheet(**kwargs)
    sheet.status = ResultStatus.PUBLISHED
    sheet.save()
    return sheet
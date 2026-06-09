"""
Unit tests for the corecode app models.
"""

import pytest
from datetime import date
from django.contrib.auth import get_user_model

from apps.corecode.models import (
    AcademicSession, AcademicTerm, StudentClass, Subject, SiteConfig, SystemLog,
)
from apps.corecode.constants import (
    NigerianClassLevel, EducationLevel, TermType, SubjectType, SiteConfigKey,
)

User = get_user_model()


@pytest.mark.django_db
class TestAcademicSessionModel:

    def test_create_session(self, db):
        session = AcademicSession.objects.create(
            name='2024/2025', code='202425',
            start_date=date(2024, 9, 1), end_date=date(2025, 8, 31),
        )
        assert session.pk is not None
        assert str(session) == '2024/2025'

    def test_only_one_current_session(self, db):
        s1 = AcademicSession.objects.create(
            name='2023/2024', code='202324', is_current=True,
            start_date=date(2023, 9, 1), end_date=date(2024, 8, 31),
        )
        s2 = AcademicSession.objects.create(
            name='2024/2025', code='202425', is_current=True,
            start_date=date(2024, 9, 1), end_date=date(2025, 8, 31),
        )
        s1.refresh_from_db()
        assert s1.is_current is False
        assert s2.is_current is True

    def test_ordering_newest_first(self, db):
        AcademicSession.objects.create(
            name='2022/2023', code='202223',
            start_date=date(2022, 9, 1), end_date=date(2023, 8, 31),
        )
        AcademicSession.objects.create(
            name='2024/2025', code='202425',
            start_date=date(2024, 9, 1), end_date=date(2025, 8, 31),
        )
        sessions = list(AcademicSession.objects.all())
        assert sessions[0].name == '2024/2025'

    def test_unique_name_and_code(self, db):
        AcademicSession.objects.create(
            name='2024/2025', code='202425',
            start_date=date(2024, 9, 1), end_date=date(2025, 8, 31),
        )
        with pytest.raises(Exception):
            AcademicSession.objects.create(
                name='2024/2025', code='202425',
                start_date=date(2024, 9, 1), end_date=date(2025, 8, 31),
            )


@pytest.mark.django_db
class TestAcademicTermModel:

    def test_create_term(self, academic_session):
        term = AcademicTerm.objects.create(
            session=academic_session,
            term=TermType.SECOND,
            name='Second Term 2025/2026',
            start_date=date(2026, 1, 10),
            end_date=date(2026, 4, 15),
        )
        assert term.pk is not None

    def test_only_one_current_term(self, academic_session):
        t1 = AcademicTerm.objects.create(
            session=academic_session, term=TermType.FIRST,
            name='First', is_current=True,
            start_date=date(2025, 9, 1), end_date=date(2025, 12, 15),
        )
        t2 = AcademicTerm.objects.create(
            session=academic_session, term=TermType.SECOND,
            name='Second', is_current=True,
            start_date=date(2026, 1, 10), end_date=date(2026, 4, 15),
        )
        t1.refresh_from_db()
        assert t1.is_current is False
        assert t2.is_current is True

    def test_unique_together(self, academic_session):
        AcademicTerm.objects.create(
            session=academic_session, term=TermType.FIRST,
            name='First', start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
        )
        with pytest.raises(Exception):
            AcademicTerm.objects.create(
                session=academic_session, term=TermType.FIRST,
                name='First Again', start_date=date(2025, 9, 1),
                end_date=date(2025, 12, 15),
            )


@pytest.mark.django_db
class TestStudentClassModel:

    def test_create_class(self, db):
        sc = StudentClass.objects.create(
            name=NigerianClassLevel.JSS_1,
            display_name='JSS 1',
            education_level=EducationLevel.JSS,
            max_students=40,
            sort_order=10,
        )
        assert sc.pk is not None
        assert str(sc) == 'JSS 1'

    def test_str_with_stream(self, db):
        sc = StudentClass.objects.create(
            name=NigerianClassLevel.SS_1,
            stream='A',
            display_name='SS 1',
            education_level=EducationLevel.SSS,
        )
        assert str(sc) == 'SS 1 A'

    def test_full_name_property(self, db):
        sc = StudentClass.objects.create(
            name=NigerianClassLevel.SS_2,
            stream='B',
            display_name='SS 2',
            education_level=EducationLevel.SSS,
        )
        assert sc.full_name == 'SS 2 B'

    def test_full_name_no_stream(self, db):
        sc = StudentClass.objects.create(
            name=NigerianClassLevel.PRIMARY_1,
            display_name='Primary 1',
            education_level=EducationLevel.PRIMARY,
        )
        assert sc.full_name == 'Primary 1'

    def test_is_graduating_class(self, db):
        ss3 = StudentClass.objects.create(
            name=NigerianClassLevel.SS_3,
            display_name='SS 3',
            education_level=EducationLevel.SSS,
        )
        jss1 = StudentClass.objects.create(
            name=NigerianClassLevel.JSS_1,
            display_name='JSS 1',
            education_level=EducationLevel.JSS,
        )
        assert ss3.is_graduating_class is True
        assert jss1.is_graduating_class is False

    def test_next_class_progression(self, db):
        jss1 = StudentClass.objects.create(
            name=NigerianClassLevel.JSS_1,
            display_name='JSS 1',
            education_level=EducationLevel.JSS,
            sort_order=10,
        )
        jss2 = StudentClass.objects.create(
            name=NigerianClassLevel.JSS_2,
            display_name='JSS 2',
            education_level=EducationLevel.JSS,
            sort_order=11,
        )
        assert jss1.next_class == jss2

    def test_next_class_none_for_ss3(self, db):
        ss3 = StudentClass.objects.create(
            name=NigerianClassLevel.SS_3,
            display_name='SS 3',
            education_level=EducationLevel.SSS,
        )
        assert ss3.next_class is None


@pytest.mark.django_db
class TestSubjectModel:

    def test_create_subject(self, db):
        subject = Subject.objects.create(
            name='Mathematics',
            code='MATH',
            subject_type=SubjectType.CORE,
        )
        assert subject.pk is not None
        assert 'Mathematics' in str(subject)
        assert 'MATH' in str(subject)

    def test_unique_name_and_code(self, db):
        Subject.objects.create(name='English', code='ENG')
        with pytest.raises(Exception):
            Subject.objects.create(name='English', code='ENG2')

    def test_nigerian_core_flag(self, db):
        subject = Subject.objects.create(
            name='Civic Education',
            code='CIVIC',
            is_nigerian_core=True,
        )
        assert subject.is_nigerian_core is True


@pytest.mark.django_db
class TestSiteConfigModel:

    def test_get_string_value(self, db):
        SiteConfig.objects.create(
            key=SiteConfigKey.COMPANY_NAME,
            value='Test School',
        )
        assert SiteConfig.get(SiteConfigKey.COMPANY_NAME) == 'Test School'

    def test_get_boolean_value(self, db):
        SiteConfig.objects.create(
            key=SiteConfigKey.MAINTENANCE_MODE,
            value='true',
        )
        assert SiteConfig.get(SiteConfigKey.MAINTENANCE_MODE) is True

    def test_get_integer_value(self, db):
        SiteConfig.objects.create(
            key=SiteConfigKey.PASS_MARK,
            value='40',
        )
        assert SiteConfig.get(SiteConfigKey.PASS_MARK) == 40

    def test_get_default_when_missing(self, db):
        assert SiteConfig.get('NONEXISTENT_KEY', default='fallback') == 'fallback'

    def test_get_default_when_empty(self, db):
        SiteConfig.objects.create(
            key=SiteConfigKey.COMPANY_EMAIL,
            value='',
        )
        assert SiteConfig.get(SiteConfigKey.COMPANY_EMAIL, default='noreply') == 'noreply'

    def test_str_representation(self, db):
        config = SiteConfig.objects.create(
            key=SiteConfigKey.COMPANY_NAME,
            value='Ace Academy',
        )
        assert 'COMPANY_NAME' in str(config)
        assert 'Ace Academy' in str(config)


@pytest.mark.django_db
class TestSystemLogModel:

    def test_create_system_log(self, user):
        log = SystemLog.objects.create(
            user=user,
            username=user.username,
            action=SystemLog.ActionType.CREATE,
            app_label=SystemLog.AppLabel.STUDENTS,
            model_name='Student',
            object_id='1',
            object_repr='Student #1',
        )
        assert log.pk is not None
        assert log.action == SystemLog.ActionType.CREATE

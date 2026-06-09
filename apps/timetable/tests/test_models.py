"""
Unit tests for the timetable app models.
"""

import pytest
from datetime import time
from django.contrib.auth import get_user_model

from apps.timetable.models import SchoolDay, PeriodType, TimetablePeriod, Timetable

User = get_user_model()


@pytest.mark.django_db
class TestSchoolDayModel:

    def test_create_school_day(self, db):
        day = SchoolDay.objects.create(
            day_number=1, name='Monday', is_active=True, order=1,
        )
        assert day.pk is not None
        assert str(day) == 'Monday'

    def test_unique_day_number(self, db):
        SchoolDay.objects.create(day_number=1, name='Monday', order=1)
        with pytest.raises(Exception):
            SchoolDay.objects.create(day_number=1, name='Mon', order=2)

    def test_ordering_by_order(self, db):
        SchoolDay.objects.create(day_number=3, name='Wednesday', order=3)
        SchoolDay.objects.create(day_number=1, name='Monday', order=1)
        SchoolDay.objects.create(day_number=2, name='Tuesday', order=2)
        days = list(SchoolDay.objects.all())
        assert days[0].name == 'Monday'
        assert days[1].name == 'Tuesday'

    def test_friday_special_fields(self, db):
        day = SchoolDay.objects.create(
            day_number=5, name='Friday', is_active=True, order=5,
            is_friday=True,
            friday_start_time=time(8, 0),
            friday_end_time=time(12, 30),
        )
        assert day.is_friday is True
        assert day.friday_start_time == time(8, 0)


@pytest.mark.django_db
class TestPeriodTypeModel:

    def test_create_period_type(self, db):
        pt = PeriodType.objects.create(
            name='Teaching Period',
            code='TEACH',
            is_teaching=True,
            duration_minutes=40,
        )
        assert pt.pk is not None
        assert str(pt) == 'Teaching Period'

    def test_break_period(self, db):
        pt = PeriodType.objects.create(
            name='Breakfast Break',
            code='BREAK',
            is_teaching=False,
            is_break=True,
            break_duration_minutes=60,
        )
        assert pt.is_break is True
        assert pt.break_duration_minutes == 60

    def test_unique_code(self, db):
        PeriodType.objects.create(name='P1', code='P1', is_teaching=True)
        with pytest.raises(Exception):
            PeriodType.objects.create(name='P2', code='P1', is_teaching=True)


@pytest.mark.django_db
class TestTimetablePeriodModel:

    def test_create_timetable_period(self, db):
        pt = PeriodType.objects.create(
            name='Period 1', code='P1', is_teaching=True,
        )
        period = TimetablePeriod.objects.create(
            period_type=pt,
            order=1,
            start_time=time(8, 0),
            end_time=time(8, 40),
            display_name='Period 1',
        )
        assert period.pk is not None
        assert '8:00' in str(period) or '08:00' in str(period)

    def test_ordering(self, db):
        pt = PeriodType.objects.create(name='Teaching', code='T', is_teaching=True)
        TimetablePeriod.objects.create(
            period_type=pt, order=2,
            start_time=time(8, 40), end_time=time(9, 20),
            display_name='Period 2',
        )
        TimetablePeriod.objects.create(
            period_type=pt, order=1,
            start_time=time(8, 0), end_time=time(8, 40),
            display_name='Period 1',
        )
        periods = list(TimetablePeriod.objects.all())
        assert periods[0].display_name == 'Period 1'


@pytest.mark.django_db
class TestTimetableModel:

    def test_create_timetable(self, academic_session, academic_term, student_class, user):
        timetable = Timetable.objects.create(
            academic_session=academic_session,
            academic_term=academic_term,
            student_class=student_class,
            name='SS1 First Term Timetable',
            created_by=user,
        )
        assert timetable.pk is not None
        assert timetable.version == 1
        assert timetable.is_active is True

    def test_auto_name_generation(self, academic_session, student_class, user):
        timetable = Timetable.objects.create(
            academic_session=academic_session,
            student_class=student_class,
            created_by=user,
        )
        assert timetable.name != ''

    def test_str_representation(self, academic_session, student_class, user):
        timetable = Timetable.objects.create(
            academic_session=academic_session,
            student_class=student_class,
            name='Test Timetable',
            created_by=user,
        )
        result = str(timetable)
        assert student_class.display_name in result
        assert 'v1' in result

    def test_unique_together(self, academic_session, academic_term, student_class, user):
        Timetable.objects.create(
            academic_session=academic_session,
            academic_term=academic_term,
            student_class=student_class,
            name='TT1',
            version=1,
            created_by=user,
        )
        with pytest.raises(Exception):
            Timetable.objects.create(
                academic_session=academic_session,
                academic_term=academic_term,
                student_class=student_class,
                name='TT2',
                version=1,
                created_by=user,
            )

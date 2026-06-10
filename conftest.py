"""
Root conftest for DETs Toolkit test suite.
Provides shared fixtures for all app tests.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save, post_save
from datetime import date

User = get_user_model()


def _disconnect_signals():
    """Disconnect signal handlers that cause side-effects during tests."""
    from apps.audit.signals.handlers import audit_pre_save, audit_post_save
    from apps.attendance.signals.handlers import (
        attendance_record_post_save, attendance_record_pre_save,
    )
    from apps.attendance.models import AttendanceRecord
    pre_save.disconnect(audit_pre_save)
    post_save.disconnect(audit_post_save)
    post_save.disconnect(attendance_record_post_save, sender=AttendanceRecord)
    pre_save.disconnect(attendance_record_pre_save, sender=AttendanceRecord)


# Disconnect during test DB creation (migrations)
_disconnect_signals()


@pytest.fixture(autouse=True)
def _signals_off():
    """Keep signals disconnected during every test."""
    _disconnect_signals()
    yield
    _disconnect_signals()


@pytest.fixture
def user(db):
    """Create a basic user."""
    return User.objects.create_user(
        username='testuser',
        email='testuser@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User',
    )


@pytest.fixture
def admin_user(db):
    """Create a superuser."""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123',
        first_name='Admin',
        last_name='User',
    )


@pytest.fixture
def academic_session(db):
    """Create a current academic session."""
    from apps.corecode.models import AcademicSession
    return AcademicSession.objects.create(
        name='2025/2026',
        code='202526',
        is_current=True,
        start_date=date(2025, 9, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def academic_term(db, academic_session):
    """Create a current academic term."""
    from apps.corecode.models import AcademicTerm
    from apps.corecode.constants import TermType
    return AcademicTerm.objects.create(
        session=academic_session,
        term=TermType.FIRST,
        name='First Term 2025/2026',
        is_current=True,
        start_date=date(2025, 9, 1),
        end_date=date(2025, 12, 15),
    )


@pytest.fixture
def student_class(db):
    """Create a student class."""
    from apps.corecode.models import StudentClass
    from apps.corecode.constants import NigerianClassLevel, EducationLevel
    return StudentClass.objects.create(
        name=NigerianClassLevel.SS_1,
        display_name='SS 1',
        education_level=EducationLevel.SSS,
        max_students=45,
        sort_order=13,
        is_active=True,
    )

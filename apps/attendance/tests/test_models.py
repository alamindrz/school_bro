"""
Unit tests for the attendance app models.
"""

import pytest
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.attendance.models import (
    AttendanceRegister, AttendanceRecord, QRCode, AttendanceSummary,
)
from apps.attendance.constants import AttendanceStatus, SessionType

User = get_user_model()


@pytest.mark.django_db
class TestAttendanceRegisterModel:

    def test_create_register(self, academic_session, academic_term, student_class):
        register = AttendanceRegister.objects.create(
            student_class=student_class,
            academic_session=academic_session,
            academic_term=academic_term,
            date=date.today(),
            session_type=SessionType.MORNING,
        )
        assert register.pk is not None
        assert register.register_number.startswith('ATT-')

    def test_auto_generate_register_number(self, academic_session, student_class):
        register = AttendanceRegister(
            student_class=student_class,
            academic_session=academic_session,
            date=date.today(),
            session_type=SessionType.MORNING,
        )
        register.save()
        assert register.register_number != ''
        assert 'ATT-' in register.register_number

    def test_register_number_format(self, academic_session, student_class):
        register = AttendanceRegister.objects.create(
            student_class=student_class,
            academic_session=academic_session,
            date=date(2025, 10, 15),
            session_type=SessionType.MORNING,
        )
        assert '20251015' in register.register_number
        assert 'MOR' in register.register_number

    def test_str_representation(self, academic_session, student_class):
        register = AttendanceRegister.objects.create(
            student_class=student_class,
            academic_session=academic_session,
            date=date(2025, 10, 15),
        )
        result = str(register)
        assert student_class.display_name in result

    def test_present_percentage_zero_students(self, academic_session, student_class):
        register = AttendanceRegister.objects.create(
            student_class=student_class,
            academic_session=academic_session,
            date=date.today(),
            total_students=0,
        )
        assert register.present_percentage == 0

    def test_present_percentage_calculation(self, academic_session, student_class):
        register = AttendanceRegister.objects.create(
            student_class=student_class,
            academic_session=academic_session,
            date=date.today(),
            total_students=20,
            present_count=15,
        )
        assert register.present_percentage == 75.0

    def test_unique_together_constraint(self, academic_session, student_class):
        AttendanceRegister.objects.create(
            student_class=student_class,
            academic_session=academic_session,
            date=date.today(),
            session_type=SessionType.MORNING,
        )
        with pytest.raises(Exception):
            AttendanceRegister.objects.create(
                student_class=student_class,
                academic_session=academic_session,
                date=date.today(),
                session_type=SessionType.MORNING,
            )

    def test_update_counts(self, academic_session, student_class, user):
        register = AttendanceRegister.objects.create(
            student_class=student_class,
            academic_session=academic_session,
            date=date.today(),
        )
        AttendanceRecord.objects.create(
            register=register, student_id=1,
            student_name='Student A', status=AttendanceStatus.PRESENT,
        )
        AttendanceRecord.objects.create(
            register=register, student_id=2,
            student_name='Student B', status=AttendanceStatus.ABSENT,
        )
        AttendanceRecord.objects.create(
            register=register, student_id=3,
            student_name='Student C', status=AttendanceStatus.LATE,
        )
        register.update_counts()
        assert register.total_students == 3
        assert register.present_count == 1
        assert register.absent_count == 1
        assert register.late_count == 1


@pytest.mark.django_db
class TestAttendanceRecordModel:

    @pytest.fixture
    def register(self, academic_session, student_class):
        return AttendanceRegister.objects.create(
            student_class=student_class,
            academic_session=academic_session,
            date=date.today(),
        )

    def test_create_record(self, register):
        record = AttendanceRecord.objects.create(
            register=register,
            student_id=1,
            student_name='John Doe',
            status=AttendanceStatus.PRESENT,
        )
        assert record.pk is not None

    def test_is_present_property(self, register):
        record = AttendanceRecord.objects.create(
            register=register, student_id=1,
            student_name='Test', status=AttendanceStatus.PRESENT,
        )
        assert record.is_present is True
        assert record.is_absent is False

    def test_is_absent_property(self, register):
        record = AttendanceRecord.objects.create(
            register=register, student_id=1,
            student_name='Test', status=AttendanceStatus.ABSENT,
        )
        assert record.is_absent is True
        assert record.is_present is False

    def test_is_late_property(self, register):
        record = AttendanceRecord.objects.create(
            register=register, student_id=1,
            student_name='Test', status=AttendanceStatus.LATE,
        )
        assert record.is_late is True

    def test_is_excused_property_with_excused(self, register):
        record = AttendanceRecord.objects.create(
            register=register, student_id=1,
            student_name='Test', status=AttendanceStatus.EXCUSED,
        )
        assert record.is_excused is True

    def test_is_excused_property_with_sick(self, register):
        record = AttendanceRecord.objects.create(
            register=register, student_id=1,
            student_name='Test', status=AttendanceStatus.SICK,
        )
        assert record.is_excused is True

    def test_unique_together_register_student(self, register):
        AttendanceRecord.objects.create(
            register=register, student_id=1,
            student_name='Test', status=AttendanceStatus.PRESENT,
        )
        with pytest.raises(Exception):
            AttendanceRecord.objects.create(
                register=register, student_id=1,
                student_name='Test', status=AttendanceStatus.ABSENT,
            )


@pytest.mark.django_db
class TestQRCodeModel:

    def test_create_qr_code(self, db):
        qr = QRCode.objects.create(
            student_id=1,
            student_name='John Doe',
            code='ATT-QR-ABC12345',
        )
        assert qr.pk is not None
        assert qr.is_active is True

    def test_is_valid_active_no_expiry(self, db):
        qr = QRCode.objects.create(
            student_id=1, student_name='John',
            code='ATT-QR-VALID001',
        )
        assert qr.is_valid() is True

    def test_is_valid_inactive(self, db):
        qr = QRCode.objects.create(
            student_id=2, student_name='Jane',
            code='ATT-QR-INACT001', is_active=False,
        )
        assert qr.is_valid() is False

    def test_is_valid_expired(self, db):
        qr = QRCode.objects.create(
            student_id=3, student_name='Bob',
            code='ATT-QR-EXPIR001',
            expires_at=timezone.now() - timedelta(hours=1),
        )
        assert qr.is_valid() is False

    def test_record_use(self, db):
        qr = QRCode.objects.create(
            student_id=4, student_name='Alice',
            code='ATT-QR-USE00001',
        )
        assert qr.use_count == 0
        qr.record_use()
        qr.refresh_from_db()
        assert qr.use_count == 1
        assert qr.last_used is not None

    def test_str_representation(self, db):
        qr = QRCode.objects.create(
            student_id=5, student_name='Charlie',
            code='ATT-QR-STR00001',
        )
        assert 'Charlie' in str(qr)


@pytest.mark.django_db
class TestAttendanceSummaryModel:

    def test_calculate_percentages(self, academic_session):
        summary = AttendanceSummary.objects.create(
            student_id=1,
            student_name='Test Student',
            academic_session=academic_session,
            total_days=100,
            present_days=80,
            absent_days=10,
            late_days=5,
            excused_days=5,
        )
        summary.calculate_percentages()
        assert summary.present_percentage == 80.0

    def test_calculate_percentages_zero_days(self, academic_session):
        summary = AttendanceSummary.objects.create(
            student_id=2,
            student_name='New Student',
            academic_session=academic_session,
            total_days=0,
        )
        summary.calculate_percentages()
        assert summary.present_percentage == 0
        assert summary.attendance_score == 0

    def test_critical_attendance_alert(self, academic_session):
        summary = AttendanceSummary.objects.create(
            student_id=3,
            student_name='At Risk',
            academic_session=academic_session,
            total_days=100,
            present_days=40,
            absent_days=60,
        )
        summary.calculate_percentages()
        assert summary.attendance_alert is True
        assert 'Critical' in summary.alert_reason

    def test_low_attendance_alert(self, academic_session):
        summary = AttendanceSummary.objects.create(
            student_id=4,
            student_name='Low Att',
            academic_session=academic_session,
            total_days=100,
            present_days=70,
            absent_days=30,
        )
        summary.calculate_percentages()
        assert summary.attendance_alert is True
        assert 'Low' in summary.alert_reason

    def test_no_alert_good_attendance(self, academic_session):
        summary = AttendanceSummary.objects.create(
            student_id=5,
            student_name='Good Student',
            academic_session=academic_session,
            total_days=100,
            present_days=90,
            absent_days=10,
        )
        summary.calculate_percentages()
        assert summary.attendance_alert is False
        assert summary.alert_reason == ''

    def test_weighted_score(self, academic_session):
        summary = AttendanceSummary.objects.create(
            student_id=6,
            student_name='Weighted',
            academic_session=academic_session,
            total_days=100,
            present_days=60,
            absent_days=10,
            late_days=20,
            excused_days=10,
        )
        summary.calculate_percentages()
        # weighted = 60*1.0 + 20*0.5 + 10*0.75 = 60 + 10 + 7.5 = 77.5
        assert summary.attendance_score == pytest.approx(77.5, abs=0.1)

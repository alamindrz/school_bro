"""
Unit tests for the attendance app validators.
"""

import pytest
from datetime import date, time
from django.core.exceptions import ValidationError

from apps.attendance.validators import AttendanceValidator, QRCodeValidator
from apps.attendance.constants import AttendanceStatus, SessionType


class TestAttendanceValidator:

    def test_validate_valid_status(self):
        assert AttendanceValidator.validate_status(AttendanceStatus.PRESENT) is True
        assert AttendanceValidator.validate_status(AttendanceStatus.ABSENT) is True
        assert AttendanceValidator.validate_status(AttendanceStatus.LATE) is True

    def test_validate_invalid_status(self):
        with pytest.raises(ValidationError, match="Invalid attendance status"):
            AttendanceValidator.validate_status('invalid')

    def test_validate_valid_session_type(self):
        assert AttendanceValidator.validate_session_type(SessionType.MORNING) is True
        assert AttendanceValidator.validate_session_type(SessionType.AFTERNOON) is True

    def test_validate_invalid_session_type(self):
        with pytest.raises(ValidationError, match="Invalid session type"):
            AttendanceValidator.validate_session_type('invalid')

    def test_validate_check_in_time(self):
        result = AttendanceValidator.validate_check_in_time(
            time(8, 0), SessionType.MORNING,
        )
        assert result is True

    def test_validate_date_range_valid(self):
        start = date(2025, 1, 1)
        end = date(2025, 6, 30)
        assert AttendanceValidator.validate_date_range(start, end) is True

    def test_validate_date_range_start_after_end(self):
        with pytest.raises(ValidationError, match="Start date cannot be after end date"):
            AttendanceValidator.validate_date_range(
                date(2025, 12, 31), date(2025, 1, 1),
            )

    def test_validate_date_range_exceeds_one_year(self):
        with pytest.raises(ValidationError, match="cannot exceed one year"):
            AttendanceValidator.validate_date_range(
                date(2023, 1, 1), date(2025, 1, 2),
            )


class TestQRCodeValidator:

    def test_validate_valid_code(self):
        assert QRCodeValidator.validate_code('ATT-QR-ABC12345') is True

    def test_validate_code_too_short(self):
        with pytest.raises(ValidationError, match="between 10 and 100"):
            QRCodeValidator.validate_code('SHORT')

    def test_validate_code_too_long(self):
        with pytest.raises(ValidationError, match="between 10 and 100"):
            QRCodeValidator.validate_code('A' * 101)

    def test_validate_code_invalid_characters(self):
        with pytest.raises(ValidationError, match="only contain"):
            QRCodeValidator.validate_code('ATT QR ABC!@#$')

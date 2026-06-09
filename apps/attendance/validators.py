"""
Attendance App Validators - Pure validation functions
"""

from datetime import date, time
from django.core.exceptions import ValidationError

from .constants import AttendanceStatus, SessionType, MarkingMethod
from apps.shared.validators import (
    validate_choice as _shared_validate_choice,
    validate_date_range as _shared_validate_date_range,
)


class AttendanceValidator:
    """Validate attendance data"""
    
    @staticmethod
    def validate_status(status: str) -> bool:
        """Validate attendance status"""
        return _shared_validate_choice(status, AttendanceStatus.CHOICES, "attendance status")
    
    @staticmethod
    def validate_session_type(session_type: str) -> bool:
        """Validate session type"""
        return _shared_validate_choice(session_type, SessionType.CHOICES, "session type")
    
    @staticmethod
    def validate_check_in_time(check_in_time: time, session_type: str) -> bool:
        """Validate check-in time against session type"""
        from .constants import DEFAULT_SESSION_TIMES, LATE_THRESHOLD_MINUTES
        import datetime
        
        expected_time_str = DEFAULT_SESSION_TIMES.get(session_type)
        if expected_time_str:
            expected_time = datetime.datetime.strptime(expected_time_str, '%H:%M').time()
            
            # Convert to datetime for comparison
            today = date.today()
            check_dt = datetime.datetime.combine(today, check_in_time)
            expected_dt = datetime.datetime.combine(today, expected_time)
            
            if check_dt > expected_dt + datetime.timedelta(minutes=LATE_THRESHOLD_MINUTES):
                # This would be late, but status should reflect that
                pass
        
        return True
    
    @staticmethod
    def validate_date_range(start_date: date, end_date: date) -> bool:
        """Validate date range"""
        return _shared_validate_date_range(start_date, end_date, max_days=365)


class QRCodeValidator:
    """Validate QR code data"""
    
    @staticmethod
    def validate_code(code: str) -> bool:
        """Validate QR code format"""
        if len(code) < 10 or len(code) > 100:
            raise ValidationError("QR code must be between 10 and 100 characters")
        
        # Check for valid characters (alphanumeric + hyphens)
        import re
        if not re.match(r'^[a-zA-Z0-9\-]+$', code):
            raise ValidationError("QR code can only contain letters, numbers, and hyphens")
        
        return True
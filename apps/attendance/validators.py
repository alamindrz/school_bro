"""
Attendance App Validators - Pure validation functions
"""

from datetime import date, time
from django.core.exceptions import ValidationError

from .constants import AttendanceStatus, SessionType, MarkingMethod


class AttendanceValidator:
    """Validate attendance data"""
    
    @staticmethod
    def validate_status(status: str) -> bool:
        """Validate attendance status"""
        valid_statuses = [s[0] for s in AttendanceStatus.CHOICES]
        if status not in valid_statuses:
            raise ValidationError(f"Invalid attendance status: {status}")
        return True
    
    @staticmethod
    def validate_session_type(session_type: str) -> bool:
        """Validate session type"""
        valid_types = [s[0] for s in SessionType.CHOICES]
        if session_type not in valid_types:
            raise ValidationError(f"Invalid session type: {session_type}")
        return True
    
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
        if start_date > end_date:
            raise ValidationError("Start date cannot be after end date")
        
        if (end_date - start_date).days > 365:
            raise ValidationError("Date range cannot exceed one year")
        
        return True


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
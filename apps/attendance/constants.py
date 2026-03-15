"""
Attendance App Constants
Pure constants - no dependencies
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class AttendanceStatus:
    """Attendance status for a student"""
    
    PRESENT = 'present'
    ABSENT = 'absent'
    LATE = 'late'
    EXCUSED = 'excused'
    HOLIDAY = 'holiday'
    SICK = 'sick'
    
    CHOICES = [
        (PRESENT, _('Present')),
        (ABSENT, _('Absent')),
        (LATE, _('Late')),
        (EXCUSED, _('Excused')),
        (HOLIDAY, _('Holiday')),
        (SICK, _('Sick')),
    ]
    
    # Colors for UI
    COLORS = {
        PRESENT: 'green',
        ABSENT: 'red',
        LATE: 'yellow',
        EXCUSED: 'blue',
        HOLIDAY: 'purple',
        SICK: 'orange',
    }
    
    # Icons for UI
    ICONS = {
        PRESENT: 'fa-check-circle',
        ABSENT: 'fa-times-circle',
        LATE: 'fa-clock',
        EXCUSED: 'fa-check',
        HOLIDAY: 'fa-umbrella-beach',
        SICK: 'fa-thermometer-half',
    }


class SessionType:
    """Type of attendance session"""
    
    MORNING = 'morning'
    AFTERNOON = 'afternoon'
    FULL_DAY = 'full_day'
    EVENING = 'evening'
    
    CHOICES = [
        (MORNING, _('Morning Session')),
        (AFTERNOON, _('Afternoon Session')),
        (FULL_DAY, _('Full Day')),
        (EVENING, _('Evening Session')),
    ]


class MarkingMethod:
    """How attendance is marked"""
    
    MANUAL = 'manual'
    QR_CODE = 'qr_code'
    BIOMETRIC = 'biometric'
    BULK_CSV = 'bulk_csv'
    API = 'api'
    
    CHOICES = [
        (MANUAL, _('Manual Entry')),
        (QR_CODE, _('QR Code Scan')),
        (BIOMETRIC, _('Biometric')),
        (BULK_CSV, _('Bulk CSV Upload')),
        (API, _('API Integration')),
    ]


class ReportType:
    """Types of attendance reports"""
    
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    TERMLY = 'termly'
    SESSION = 'session'
    CUSTOM = 'custom'
    
    CHOICES = [
        (DAILY, _('Daily Report')),
        (WEEKLY, _('Weekly Report')),
        (MONTHLY, _('Monthly Report')),
        (TERMLY, _('Termly Report')),
        (SESSION, _('Session Report')),
        (CUSTOM, _('Custom Date Range')),
    ]


# Thresholds for alerts
LOW_ATTENDANCE_THRESHOLD = 75  # Percentage
CRITICAL_ATTENDANCE_THRESHOLD = 50  # Percentage

# Default settings
DEFAULT_SESSION_TIMES = {
    SessionType.MORNING: '08:00',
    SessionType.AFTERNOON: '13:00',
    SessionType.FULL_DAY: '08:00',
    SessionType.EVENING: '16:00',
}

LATE_THRESHOLD_MINUTES = 15  # Minutes after start time to be considered late
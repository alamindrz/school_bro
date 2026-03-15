"""
Attendance App Exceptions
Inherit from corecode exceptions
"""

from apps.corecode.exceptions import CorecodeError


class AttendanceError(CorecodeError):
    """Base exception for all attendance errors"""
    default_message = "An attendance error occurred"
    code = 'attendance_error'


class AttendanceRecordNotFoundError(AttendanceError):
    """Attendance record not found"""
    default_message = "Attendance record not found"
    code = 'attendance_record_not_found'


class DuplicateAttendanceError(AttendanceError):
    """Duplicate attendance record for same student/date/session"""
    default_message = "Attendance already marked for this student on this date"
    code = 'duplicate_attendance'


class InvalidAttendanceStatusError(AttendanceError):
    """Invalid attendance status"""
    default_message = "Invalid attendance status"
    code = 'invalid_attendance_status'


class StudentNotFoundError(AttendanceError):
    """Student not found"""
    default_message = "Student not found"
    code = 'student_not_found'


class ClassNotFoundError(AttendanceError):
    """Class not found"""
    default_message = "Class not found"
    code = 'class_not_found'


class BulkOperationError(AttendanceError):
    """Bulk attendance operation failed"""
    default_message = "Bulk operation failed"
    code = 'bulk_operation_error'


class QRCodeError(AttendanceError):
    """QR code related errors"""
    default_message = "QR code error"
    code = 'qr_code_error'


class InvalidQRCodeError(QRCodeError):
    """Invalid QR code format"""
    default_message = "Invalid QR code"
    code = 'invalid_qr_code'


class ExpiredQRCodeError(QRCodeError):
    """QR code has expired"""
    default_message = "QR code has expired"
    code = 'expired_qr_code'


class ReportGenerationError(AttendanceError):
    """Report generation failed"""
    default_message = "Failed to generate report"
    code = 'report_generation_error'


class DateRangeError(AttendanceError):
    """Invalid date range"""
    default_message = "Invalid date range"
    code = 'date_range_error'
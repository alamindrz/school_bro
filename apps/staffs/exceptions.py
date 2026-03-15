"""
Staffs App Exceptions
Inherit from corecode exceptions
"""

from apps.corecode.exceptions import CorecodeError


class StaffError(CorecodeError):
    """Base exception for all staff errors"""
    default_message = "A staff management error occurred"
    code = 'staff_error'


class StaffNotFoundError(StaffError):
    """Staff member not found"""
    default_message = "Staff member not found"
    code = 'staff_not_found'


class DuplicateStaffError(StaffError):
    """Duplicate staff record (email, staff_id)"""
    default_message = "A staff member with this ID or email already exists"
    code = 'duplicate_staff'


class InvalidStatusTransitionError(StaffError):
    """Invalid employment status transition"""
    default_message = "Cannot transition to this status"
    code = 'invalid_status_transition'


class LeaveRequestError(StaffError):
    """Leave request errors"""
    default_message = "Leave request error"
    code = 'leave_request_error'


class LeaveRequestNotFoundError(LeaveRequestError):
    """Leave request not found"""
    default_message = "Leave request not found"
    code = 'leave_request_not_found'


class InsufficientLeaveBalanceError(LeaveRequestError):
    """Insufficient leave balance"""
    default_message = "Insufficient leave balance"
    code = 'insufficient_leave_balance'


class OverlappingLeaveError(LeaveRequestError):
    """Overlapping leave dates"""
    default_message = "Leave dates overlap with existing leave"
    code = 'overlapping_leave'


class SubjectAssignmentError(StaffError):
    """Subject assignment errors"""
    default_message = "Subject assignment error"
    code = 'subject_assignment_error'


class StaffAttendanceError(StaffError):
    """Staff attendance errors"""
    default_message = "Staff attendance error"
    code = 'staff_attendance_error'


class DuplicateAttendanceError(StaffAttendanceError):
    """Duplicate staff attendance"""
    default_message = "Attendance already marked for this date"
    code = 'duplicate_attendance'
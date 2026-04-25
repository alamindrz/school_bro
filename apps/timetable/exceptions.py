"""
Timetable App Exceptions
"""

from apps.corecode.exceptions import CorecodeError


class TimetableError(CorecodeError):
    """Base exception for all timetable errors"""
    default_message = "A timetable error occurred"
    code = 'timetable_error'


class TimetableNotFoundError(TimetableError):
    """Timetable not found"""
    default_message = "Timetable not found"
    code = 'timetable_not_found'


class TeacherClashError(TimetableError):
    """Teacher assigned to multiple classes at same time"""
    default_message = "Teacher has a clash in schedule"
    code = 'teacher_clash'


class RoomClashError(TimetableError):
    """Room already occupied at this time"""
    default_message = "Room is already occupied at this time"
    code = 'room_clash'


class InvalidTimetableStateError(TimetableError):
    """Invalid timetable state transition"""
    default_message = "Invalid timetable state"
    code = 'invalid_timetable_state'
"""
Attendance App Interfaces - Contracts for other apps
NO model imports. Pure data contracts.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import date


@dataclass
class AttendanceRecordContract:
    """
    Contract for attendance records
    Used by other apps (parents, reports)
    """
    student_id: int
    date: date
    status: str
    session_type: str
    check_in_time: Optional[str] = None


@dataclass
class AttendanceSummaryContract:
    """
    Contract for attendance summaries
    """
    student_id: int
    session_id: int
    term_id: Optional[int] = None
    present_percentage: float = 0
    total_days: int = 0
    absent_days: int = 0


class AttendanceServiceInterface:
    """
    Interface that other apps must use to interact with attendance app
    """
    
    @staticmethod
    def get_student_summary(student_id: int, session_id: Optional[int] = None) -> Dict[str, Any]:
        """Get attendance summary for a student"""
        raise NotImplementedError("Use attendance.selectors.AttendanceSummarySelector.get_student_summary")
    
    @staticmethod
    def mark_attendance(contract: AttendanceRecordContract) -> Dict[str, Any]:
        """Mark attendance for a student"""
        raise NotImplementedError("Use attendance.services.AttendanceService.mark_attendance")
    
    @staticmethod
    def get_daily_summary(date: date, class_id: Optional[int] = None) -> Dict[str, Any]:
        """Get daily attendance summary"""
        raise NotImplementedError("Use attendance.selectors.AttendanceRecordSelector.get_daily_summary")
"""
Staff Attendance Service - Daily attendance tracking
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, Dict, Any
from datetime import date, time, datetime
import logging

from ..models import StaffAttendance, Staff
from ..exceptions import StaffNotFoundError, DuplicateAttendanceError
from ..selectors import StaffAttendanceSelector

from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class StaffAttendanceService:
    """
    Staff attendance business operations
    """

    @staticmethod
    @transaction.atomic
    def check_in(
        staff_id: int,
        check_in_time: Optional[time] = None,
        location: str = '',
        marked_by_id: Optional[int] = None
    ) -> StaffAttendance:
        """
        Record staff check-in
        """
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            raise StaffNotFoundError(f"Staff with id {staff_id} not found")

        today = date.today()

        # Check if already checked in today
        existing = StaffAttendance.objects.filter(
            staff=staff,
            date=today
        ).first()

        if existing:
            if existing.check_in_time:
                raise DuplicateAttendanceError(f"Staff already checked in at {existing.check_in_time}")
            # Update existing record
            existing.check_in_time = check_in_time or datetime.now().time()
            existing.check_in_location = location
            existing.marked_by_id = marked_by_id
            existing.save(update_fields=['check_in_time', 'check_in_location', 'marked_by', 'updated_at'])
            attendance = existing
        else:
            # Create new attendance record
            attendance = StaffAttendance.objects.create(
                staff=staff,
                date=today,
                check_in_time=check_in_time or datetime.now().time(),
                check_in_location=location,
                status='present',  # Default, may be updated later if late
                marked_by_id=marked_by_id
            )

        # Determine if late (based on staff shift)
        StaffAttendanceService._check_lateness(attendance, staff)

        logger.info(f"Staff {staff_id} checked in")
        return attendance

    @staticmethod
    @transaction.atomic
    def check_out(
        staff_id: int,
        check_out_time: Optional[time] = None,
        location: str = '',
        marked_by_id: Optional[int] = None
    ) -> StaffAttendance:
        """
        Record staff check-out
        """
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            raise StaffNotFoundError(f"Staff with id {staff_id} not found")

        today = date.today()

        # Find today's attendance record
        try:
            attendance = StaffAttendance.objects.get(
                staff=staff,
                date=today
            )
        except StaffAttendance.DoesNotExist:
            raise ValidationError("Staff has not checked in today")

        attendance.check_out_time = check_out_time or datetime.now().time()
        attendance.check_out_location = location
        attendance.marked_by_id = marked_by_id
        attendance.save(update_fields=['check_out_time', 'check_out_location', 'marked_by', 'updated_at'])

        logger.info(f"Staff {staff_id} checked out")
        return attendance

    @staticmethod
    @transaction.atomic
    def mark_absent(
        staff_id: int,
        attendance_date: date,
        notes: str = '',
        marked_by_id: Optional[int] = None
    ) -> StaffAttendance:
        """
        Mark staff as absent for a date
        """
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            raise StaffNotFoundError(f"Staff with id {staff_id} not found")

        # Check if already has record for this date
        existing = StaffAttendance.objects.filter(
            staff=staff,
            date=attendance_date
        ).first()

        if existing:
            existing.status = 'absent'
            existing.notes = notes
            existing.marked_by_id = marked_by_id
            existing.save(update_fields=['status', 'notes', 'marked_by', 'updated_at'])
            attendance = existing
        else:
            attendance = StaffAttendance.objects.create(
                staff=staff,
                date=attendance_date,
                status='absent',
                notes=notes,
                marked_by_id=marked_by_id
            )

        logger.info(f"Staff {staff_id} marked absent for {attendance_date}")
        return attendance

    @staticmethod
    def _check_lateness(attendance: StaffAttendance, staff: Staff):
        """
        Check if staff is late based on shift timing
        """
        from .constants import ShiftType

        # Define expected start times for different shifts
        shift_start_times = {
            'morning': time(8, 0),   # 8:00 AM
            'afternoon': time(14, 0),  # 2:00 PM
            'evening': time(16, 0),   # 4:00 PM
            'night': time(22, 0),     # 10:00 PM
            'fixed': time(8, 0),      # Default 8:00 AM
        }

        expected_time = shift_start_times.get(staff.shift, time(8, 0))

        # If check-in is more than 15 minutes after expected time, mark as late
        if attendance.check_in_time:
            check_in_datetime = datetime.combine(attendance.date, attendance.check_in_time)
            expected_datetime = datetime.combine(attendance.date, expected_time)

            if check_in_datetime > expected_datetime:
                # Calculate minutes late
                minutes_late = (check_in_datetime - expected_datetime).seconds // 60

                if minutes_late > 15:
                    attendance.status = 'late'
                    attendance.save(update_fields=['status'])
"""
Leave Service - Staff leave management
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, Dict, Any
from datetime import date, timedelta
import logging

from ..models import LeaveRequest, Staff
from ..constants import LeaveStatus, LeaveType
from ..exceptions import (
    LeaveRequestNotFoundError, InsufficientLeaveBalanceError,
    OverlappingLeaveError, StaffNotFoundError
)
from ..selectors import LeaveRequestSelector

from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class LeaveService:
    """
    Staff leave management business logic
    """

    # Default leave entitlements (in days per year)
    LEAVE_ENTITLEMENTS = {
        LeaveType.ANNUAL: 21,
        LeaveType.SICK: 10,
        LeaveType.MATERNITY: 90,
        LeaveType.PATERNITY: 10,
        LeaveType.STUDY: 30,
        LeaveType.UNPAID: 0,
        LeaveType.COMPASSIONATE: 5,
        LeaveType.SABBATICAL: 365,
        LeaveType.CASUAL: 3,
    }

    @classmethod
    @transaction.atomic
    def request_leave(
        cls,
        staff_id: int,
        leave_type: str,
        start_date: str,
        end_date: str,
        reason: str,
        handover_notes: str = '',
        alternative_phone: str = '',
        alternative_email: str = '',
        requested_by_id: Optional[int] = None
    ) -> LeaveRequest:
        """
        Submit a leave request
        """
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            raise StaffNotFoundError(f"Staff with id {staff_id} not found")

        from datetime import datetime
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Validate dates
        if start > end:
            raise ValidationError("Start date cannot be after end date")

        if start < date.today():
            raise ValidationError("Cannot request leave for past dates")

        # Check for overlapping leave
        overlapping = LeaveRequest.objects.filter(
            staff=staff,
            status__in=[LeaveStatus.PENDING, LeaveStatus.APPROVED],
            start_date__lte=end,
            end_date__gte=start
        ).exists()

        if overlapping:
            raise OverlappingLeaveError("Leave dates overlap with existing leave request")

        # Check leave balance (for paid leaves)
        if leave_type in cls.LEAVE_ENTITLEMENTS and leave_type != LeaveType.UNPAID:
            days_requested = (end - start).days + 1
            balance = cls.get_leave_balance(staff_id, leave_type)

            if days_requested > balance:
                raise InsufficientLeaveBalanceError(
                    f"Insufficient {leave_type} balance. Available: {balance} days, Requested: {days_requested} days"
                )

        # Create leave request
        leave = LeaveRequest.objects.create(
            staff=staff,
            leave_type=leave_type,
            start_date=start,
            end_date=end,
            return_date=end + timedelta(days=1),  # Return next day
            reason=reason,
            handover_notes=handover_notes,
            alternative_phone=alternative_phone,
            alternative_email=alternative_email,
            status=LeaveStatus.PENDING
        )

        logger.info(f"Leave request created for staff {staff_id}")
        return leave

    @classmethod
    @transaction.atomic
    def approve_leave(
        cls,
        leave_id: int,
        approver_id: int,
        approval_notes: str = ''
    ) -> LeaveRequest:
        """
        Approve a leave request
        """
        try:
            leave = LeaveRequest.objects.select_related('staff').get(id=leave_id)
            approver = Staff.objects.get(id=approver_id)
        except LeaveRequest.DoesNotExist:
            raise LeaveRequestNotFoundError(f"Leave request {leave_id} not found")
        except Staff.DoesNotExist:
            raise StaffNotFoundError(f"Approver with id {approver_id} not found")

        if leave.status != LeaveStatus.PENDING:
            raise ValidationError(f"Cannot approve leave with status {leave.status}")

        leave.status = LeaveStatus.APPROVED
        leave.approved_by = approver
        leave.approved_at = timezone.now()
        leave.approval_notes = approval_notes
        leave.save(update_fields=['status', 'approved_by', 'approved_at', 'approval_notes'])

        # Update staff status to ON_LEAVE
        staff = leave.staff
        staff.employment_status = 'on_leave'
        staff.save(update_fields=['employment_status'])

        logger.info(f"Leave request {leave_id} approved")
        return leave

    @classmethod
    @transaction.atomic
    def reject_leave(
        cls,
        leave_id: int,
        approver_id: int,
        rejection_reason: str
    ) -> LeaveRequest:
        """
        Reject a leave request
        """
        try:
            leave = LeaveRequest.objects.get(id=leave_id)
            approver = Staff.objects.get(id=approver_id)
        except LeaveRequest.DoesNotExist:
            raise LeaveRequestNotFoundError(f"Leave request {leave_id} not found")
        except Staff.DoesNotExist:
            raise StaffNotFoundError(f"Approver with id {approver_id} not found")

        if leave.status != LeaveStatus.PENDING:
            raise ValidationError(f"Cannot reject leave with status {leave.status}")

        leave.status = LeaveStatus.REJECTED
        leave.approved_by = approver
        leave.approved_at = timezone.now()
        leave.approval_notes = rejection_reason
        leave.save(update_fields=['status', 'approved_by', 'approved_at', 'approval_notes'])

        logger.info(f"Leave request {leave_id} rejected")
        return leave

    @classmethod
    @transaction.atomic
    def cancel_leave(cls, leave_id: int, cancelled_by_id: Optional[int] = None) -> LeaveRequest:
        """
        Cancel a leave request (by staff)
        """
        try:
            leave = LeaveRequest.objects.get(id=leave_id)
        except LeaveRequest.DoesNotExist:
            raise LeaveRequestNotFoundError(f"Leave request {leave_id} not found")

        if leave.status not in [LeaveStatus.PENDING, LeaveStatus.APPROVED]:
            raise ValidationError(f"Cannot cancel leave with status {leave.status}")

        leave.status = LeaveStatus.CANCELLED
        leave.save(update_fields=['status'])

        # If it was approved, revert staff status
        if leave.status == LeaveStatus.APPROVED:
            staff = leave.staff
            staff.employment_status = 'active'
            staff.save(update_fields=['employment_status'])

        logger.info(f"Leave request {leave_id} cancelled")
        return leave

    @classmethod
    def get_leave_balance(cls, staff_id: int, leave_type: str, year: Optional[int] = None) -> int:
        """
        Calculate leave balance for a staff member
        """
        if year is None:
            year = date.today().year

        # Get entitlement
        entitlement = cls.LEAVE_ENTITLEMENTS.get(leave_type, 0)

        if entitlement == 0:
            return 0  # Unlimited or not applicable

        # Get used days this year
        used = LeaveRequest.objects.filter(
            staff_id=staff_id,
            leave_type=leave_type,
            status=LeaveStatus.APPROVED,
            start_date__year=year
        ).aggregate(total=models.Sum(
            models.F('end_date') - models.F('start_date') + timedelta(days=1)
        ))['total'] or 0

        # Convert timedelta to days
        if used:
            used_days = used.days
        else:
            used_days = 0

        return entitlement - used_days

    @classmethod
    def get_staff_on_leave(cls, date: Optional[date] = None) -> list:
        """
        Get all staff on leave on a specific date
        """
        if date is None:
            date = date.today()

        on_leave = LeaveRequest.objects.filter(
            status=LeaveStatus.APPROVED,
            start_date__lte=date,
            end_date__gte=date
        ).select_related('staff')

        return [
            {
                'staff_id': l.staff.id,
                'staff_name': l.staff.get_full_name,
                'leave_type': l.get_leave_type_display(),
                'start_date': l.start_date.isoformat(),
                'end_date': l.end_date.isoformat(),
                'return_date': l.return_date.isoformat(),
                'handover_notes': l.handover_notes,
            }
            for l in on_leave
        ]
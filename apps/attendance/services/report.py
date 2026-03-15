"""
Report Service - Attendance reporting and analytics
"""

from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from typing import List, Dict, Any, Optional
from datetime import date, timedelta, datetime
import calendar
import logging

from ..models import AttendanceRecord, AttendanceRegister, AttendanceSummary
from ..constants import AttendanceStatus, ReportType
from ..exceptions import ReportGenerationError, DateRangeError

from apps.corecode.selectors import AcademicSessionSelector, AcademicTermSelector, StudentClassSelector
from apps.students.selectors import StudentSelector

logger = logging.getLogger(__name__)


class ReportService:
    """
    Attendance reporting and analytics
    """

    @staticmethod
    def generate_daily_report(
        report_date: date,
        class_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate daily attendance report
        """
        registers = AttendanceRegister.objects.filter(date=report_date)

        if class_id:
            registers = registers.filter(student_class_id=class_id)

        if not registers.exists():
            return {
                'date': report_date.isoformat(),
                'has_data': False,
                'message': 'No attendance data for this date'
            }

        total_students = sum(r.total_students for r in registers)
        total_present = sum(r.present_count for r in registers)
        total_absent = sum(r.absent_count for r in registers)
        total_late = sum(r.late_count for r in registers)
        total_excused = sum(r.excused_count for r in registers)

        return {
            'date': report_date.isoformat(),
            'has_data': True,
            'summary': {
                'total_registers': registers.count(),
                'total_students': total_students,
                'present': total_present,
                'absent': total_absent,
                'late': total_late,
                'excused': total_excused,
                'present_percentage': (total_present / total_students * 100) if total_students > 0 else 0,
            },
            'by_class': [
                {
                    'class_id': r.student_class_id,
                    'class_name': r.student_class.display_name,
                    'total': r.total_students,
                    'present': r.present_count,
                    'absent': r.absent_count,
                    'late': r.late_count,
                    'percentage': r.present_percentage,
                }
                for r in registers
            ],
        }

    @staticmethod
    def generate_weekly_report(
        start_date: date,
        class_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate weekly attendance report
        """
        end_date = start_date + timedelta(days=6)

        registers = AttendanceRegister.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )

        if class_id:
            registers = registers.filter(student_class_id=class_id)

        if not registers.exists():
            return {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'has_data': False,
                'message': 'No attendance data for this week'
            }

        # Daily breakdown
        daily_data = []
        current = start_date
        while current <= end_date:
            day_registers = registers.filter(date=current)
            if day_registers.exists():
                total = sum(r.total_students for r in day_registers)
                present = sum(r.present_count for r in day_registers)

                daily_data.append({
                    'date': current.isoformat(),
                    'day_name': current.strftime('%A'),
                    'total': total,
                    'present': present,
                    'percentage': (present / total * 100) if total > 0 else 0,
                })
            else:
                daily_data.append({
                    'date': current.isoformat(),
                    'day_name': current.strftime('%A'),
                    'total': 0,
                    'present': 0,
                    'percentage': 0,
                    'no_data': True,
                })
            current += timedelta(days=1)

        # Weekly totals
        total_students = sum(r.total_students for r in registers)
        total_present = sum(r.present_count for r in registers)
        total_absent = sum(r.absent_count for r in registers)
        total_late = sum(r.late_count for r in registers)

        return {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'has_data': True,
            'summary': {
                'total_days': registers.dates('date', 'day').count(),
                'total_registers': registers.count(),
                'total_students': total_students,
                'present': total_present,
                'absent': total_absent,
                'late': total_late,
                'average_daily': (total_present / total_students * 100) if total_students > 0 else 0,
            },
            'daily': daily_data,
            'by_class': [
                {
                    'class_name': r.student_class.display_name,
                    'total': r.total_students,
                    'present': r.present_count,
                    'absent': r.absent_count,
                }
                for r in registers.order_by('student_class__name').distinct('student_class')
            ],
        }

    @staticmethod
    def generate_monthly_report(
        year: int,
        month: int,
        class_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate monthly attendance report
        """
        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        registers = AttendanceRegister.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )

        if class_id:
            registers = registers.filter(student_class_id=class_id)

        if not registers.exists():
            return {
                'month': f"{year}-{month:02d}",
                'has_data': False,
                'message': 'No attendance data for this month'
            }

        # Weekly breakdown
        weekly_data = []
        week_start = start_date
        while week_start <= end_date:
            week_end = min(week_start + timedelta(days=6), end_date)
            week_registers = registers.filter(
                date__gte=week_start,
                date__lte=week_end
            )

            if week_registers.exists():
                total = sum(r.total_students for r in week_registers)
                present = sum(r.present_count for r in week_registers)

                weekly_data.append({
                    'week': f"Week {len(weekly_data) + 1}",
                    'start': week_start.isoformat(),
                    'end': week_end.isoformat(),
                    'total': total,
                    'present': present,
                    'percentage': (present / total * 100) if total > 0 else 0,
                })

            week_start = week_end + timedelta(days=1)

        # Monthly totals
        total_students = sum(r.total_students for r in registers)
        total_present = sum(r.present_count for r in registers)

        return {
            'month': f"{year}-{month:02d}",
            'month_name': start_date.strftime('%B %Y'),
            'has_data': True,
            'summary': {
                'total_days': registers.dates('date', 'day').count(),
                'total_registers': registers.count(),
                'total_students': total_students,
                'present': total_present,
                'average_daily': (total_present / total_students * 100) if total_students > 0 else 0,
            },
            'weekly': weekly_data,
            'by_class': [
                {
                    'class_name': r.student_class.display_name,
                    'total': r.total_students,
                    'present': r.present_count,
                }
                for r in registers.order_by('student_class__name').distinct('student_class')
            ],
        }

    @staticmethod
    def generate_termly_report(
        session_id: int,
        term_id: int
    ) -> Dict[str, Any]:
        """
        Generate termly attendance report with student-level details
        """
        # Get term dates
        from apps.corecode.models import AcademicTerm
        try:
            term = AcademicTerm.objects.select_related('session').get(id=term_id)
        except AcademicTerm.DoesNotExist:
            raise ReportGenerationError(f"Term {term_id} not found")

        # Get all registers for this term
        registers = AttendanceRegister.objects.filter(
            academic_session_id=session_id,
            academic_term_id=term_id
        ).select_related('student_class')

        if not registers.exists():
            return {
                'session': term.session.name,
                'term': term.get_term_display(),
                'has_data': False,
                'message': 'No attendance data for this term'
            }

        # Get all students in the term
        from apps.students.selectors import StudentSelector
        students = StudentSelector.list_students(
            session_id=session_id,
            limit=10000
        )

        student_data = []
        total_days = registers.dates('date', 'day').count()

        for student in students:
            # Get student's attendance records
            records = AttendanceRecord.objects.filter(
                register__in=registers,
                student_id=student['id']
            )

            present = records.filter(status=AttendanceStatus.PRESENT).count()
            absent = records.filter(status=AttendanceStatus.ABSENT).count()
            late = records.filter(status=AttendanceStatus.LATE).count()
            excused = records.filter(
                status__in=[AttendanceStatus.EXCUSED, AttendanceStatus.SICK]
            ).count()

            student_data.append({
                'student_id': student['id'],
                'student_name': student['full_name'],
                'class': student['current_class']['display_name'],
                'present': present,
                'absent': absent,
                'late': late,
                'excused': excused,
                'total': present + absent + late + excused,
                'percentage': (present / total_days * 100) if total_days > 0 else 0,
            })

        # Sort by percentage
        student_data.sort(key=lambda x: x['percentage'], reverse=True)

        return {
            'session': term.session.name,
            'term': term.get_term_display(),
            'has_data': True,
            'total_days': total_days,
            'total_registers': registers.count(),
            'total_students': len(student_data),
            'summary': {
                'total_present': sum(s['present'] for s in student_data),
                'total_absent': sum(s['absent'] for s in student_data),
                'average_attendance': sum(s['percentage'] for s in student_data) / len(student_data) if student_data else 0,
            },
            'by_class': [
                {
                    'class_name': reg.student_class.display_name,
                    'total': reg.total_students,
                    'present': reg.present_count,
                }
                for reg in registers.order_by('student_class__name').distinct('student_class')
            ],
            'students': student_data,
        }

    @staticmethod
    def generate_student_report(
        student_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate individual student attendance report
        """
        student = StudentSelector.get_by_id(student_id)
        if not student:
            raise ReportGenerationError(f"Student {student_id} not found")

        # Get attendance records
        records = AttendanceRecord.objects.filter(student_id=student_id)

        if session_id:
            records = records.filter(register__academic_session_id=session_id)

        if term_id:
            records = records.filter(register__academic_term_id=term_id)

        if not records.exists():
            return {
                'student': student,
                'has_data': False,
                'message': 'No attendance records found'
            }

        # Calculate totals
        present = records.filter(status=AttendanceStatus.PRESENT).count()
        absent = records.filter(status=AttendanceStatus.ABSENT).count()
        late = records.filter(status=AttendanceStatus.LATE).count()
        excused = records.filter(
            status__in=[AttendanceStatus.EXCUSED, AttendanceStatus.SICK]
        ).count()
        total = records.count()

        # Monthly breakdown
        monthly_data = []
        dates = records.dates('register__date', 'month')

        for month_date in dates:
            month_records = records.filter(register__date__year=month_date.year,
                                           register__date__month=month_date.month)
            month_present = month_records.filter(status=AttendanceStatus.PRESENT).count()
            month_total = month_records.count()

            monthly_data.append({
                'month': month_date.strftime('%B %Y'),
                'present': month_present,
                'total': month_total,
                'percentage': (month_present / month_total * 100) if month_total > 0 else 0,
            })

        # Daily records
        daily_records = []
        for rec in records.order_by('-register__date')[:30]:
            daily_records.append({
                'date': rec.register.date.isoformat(),
                'day_name': rec.register.date.strftime('%A'),
                'status': rec.get_status_display(),
                'check_in': rec.check_in_time.isoformat() if rec.check_in_time else None,
            })

        return {
            'student': student,
            'has_data': True,
            'summary': {
                'total_days': total,
                'present': present,
                'absent': absent,
                'late': late,
                'excused': excused,
                'present_percentage': (present / total * 100) if total > 0 else 0,
            },
            'monthly': monthly_data,
            'recent': daily_records,
        }
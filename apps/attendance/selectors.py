"""
Attendance Selectors - READ Layer
Returns dicts, never model instances
"""

from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from typing import Optional, List, Dict, Any
from datetime import date, timedelta, datetime

from .models import AttendanceRegister, AttendanceRecord, AttendanceSummary, QRCode
from .constants import AttendanceStatus, SessionType

from apps.corecode.selectors import AcademicSessionSelector, AcademicTermSelector, StudentClassSelector
from apps.students.selectors import StudentSelector



class AttendanceSelector:
    """
    Combined attendance selector that coordinates across different attendance models.
    Provides high-level attendance queries for use in views and APIs.
    """

    @staticmethod
    def get_student_overview(
        student_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get complete attendance overview for a student.
        Combines records, summary, and statistics.
        
        Args:
            student_id: Student ID
            session_id: Academic session ID
            term_id: Academic term ID
            
        Returns:
            Dictionary with complete student attendance overview
        """
        # Get student info
        from apps.students.selectors import StudentSelector
        student = StudentSelector.get_by_id(student_id)
        
        if not student:
            return {'error': 'Student not found'}
        
        # Get attendance records
        records = AttendanceRecordSelector.get_student_records(
            student_id=student_id,
            session_id=session_id,
            term_id=term_id,
            limit=100
        )
        
        # Get attendance summary
        summary = AttendanceSummarySelector.get_student_summary(
            student_id=student_id,
            session_id=session_id,
            term_id=term_id
        )
        
        # Calculate monthly breakdown
        monthly_breakdown = AttendanceSelector._get_monthly_breakdown(
            student_id=student_id,
            session_id=session_id,
            term_id=term_id
        )
        
        # Calculate statistics
        stats = AttendanceSelector._calculate_student_stats(records, summary)
        
        return {
            'student': student,
            'summary': summary,
            'recent_records': records[:30],  # Last 30 records
            'monthly_breakdown': monthly_breakdown,
            'statistics': stats,
            'alert_status': summary.get('attendance_alert', False) if summary else False,
            'alert_reason': summary.get('alert_reason') if summary else None,
        }

    @staticmethod
    def get_class_overview(
        class_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        date_obj: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get complete attendance overview for a class.
        
        Args:
            class_id: Class ID
            session_id: Academic session ID
            term_id: Academic term ID
            date_obj: Specific date (optional)
            
        Returns:
            Dictionary with complete class attendance overview
        """
        from apps.students.selectors import StudentSelector
        
        # Get class info
        from apps.corecode.selectors import StudentClassSelector
        class_info = StudentClassSelector.get_by_id(class_id)
        
        if not class_info:
            return {'error': 'Class not found'}
        
        # Get students in class
        students = StudentSelector.get_class_students(
            class_id=class_id,
            academic_session_id=session_id
        )
        student_ids = [s['id'] for s in students]
        
        # Get today's register if date specified
        today_register = None
        if date_obj:
            registers = AttendanceRegisterSelector.get_for_date(
                date_obj=date_obj,
                class_id=class_id
            )
            today_register = registers[0] if registers else None
        
        # Get class summary
        class_summary = AttendanceSummarySelector.get_class_summary(
            class_id=class_id,
            session_id=session_id,
            term_id=term_id
        )
        
        # Get student summaries
        student_summaries = []
        for student_id in student_ids[:50]:  # Limit to 50 for performance
            summary = AttendanceSummarySelector.get_student_summary(
                student_id=student_id,
                session_id=session_id,
                term_id=term_id
            )
            if summary:
                student_summaries.append(summary)
        
        # Sort by attendance percentage
        student_summaries.sort(
            key=lambda x: x.get('present_percentage', 0),
            reverse=True
        )
        
        # Get alerts
        alerts = AttendanceSummarySelector.get_alerts(
            session_id=session_id,
            term_id=term_id,
            limit=20
        )
        # Filter to this class
        class_alerts = [a for a in alerts if a['student_id'] in student_ids]
        
        return {
            'class_info': class_info,
            'total_students': len(students),
            'today_register': today_register,
            'class_summary': class_summary,
            'student_summaries': student_summaries,
            'alerts': class_alerts,
            'top_performers': student_summaries[:10],
            'bottom_performers': student_summaries[-10:] if len(student_summaries) >= 10 else student_summaries,
        }

    @staticmethod
    def get_school_overview(
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        date_obj: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get school-wide attendance overview.
        
        Args:
            session_id: Academic session ID
            term_id: Academic term ID
            date_obj: Specific date (optional)
            
        Returns:
            Dictionary with school-wide attendance overview
        """
        from apps.corecode.selectors import StudentClassSelector
        
        # Get all active classes
        classes = StudentClassSelector.get_all_classes(active_only=True)
        
        # Get today's overall attendance if date specified
        today_overall = None
        if date_obj:
            today_overall = AttendanceRecordSelector.get_daily_summary(date_obj)
        
        # Get per-class summaries
        class_summaries = []
        for class_info in classes:
            class_summary = AttendanceSummarySelector.get_class_summary(
                class_id=class_info['id'],
                session_id=session_id,
                term_id=term_id
            )
            if class_summary:
                class_summaries.append({
                    'class_id': class_info['id'],
                    'class_name': class_info['display_name'],
                    'summary': class_summary
                })
        
        # Get all alerts
        alerts = AttendanceSummarySelector.get_alerts(
            session_id=session_id,
            term_id=term_id,
            limit=100
        )
        
        # Calculate overall statistics
        total_students = sum(c['summary']['total_students'] for c in class_summaries)
        total_alerts = sum(c['summary']['alert_count'] for c in class_summaries)
        
        avg_attendance = 0
        if class_summaries:
            total_percentage = sum(
                c['summary']['average_present_percentage'] 
                for c in class_summaries
            )
            avg_attendance = total_percentage / len(class_summaries)
        
        return {
            'date': date_obj.isoformat() if date_obj else None,
            'total_classes': len(classes),
            'classes_with_data': len(class_summaries),
            'total_students': total_students,
            'total_alerts': total_alerts,
            'average_attendance': round(avg_attendance, 1),
            'today_overall': today_overall,
            'class_summaries': class_summaries,
            'recent_alerts': alerts[:20],
            'attendance_trend': AttendanceSelector._get_attendance_trend(
                days=30,
                session_id=session_id,
                term_id=term_id
            ),
        }

    @staticmethod
    def get_attendance_trends(
        class_id: Optional[int] = None,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get attendance trends over time.
        
        Args:
            class_id: Filter by class (optional)
            session_id: Academic session ID
            term_id: Academic term ID
            days: Number of days to look back
            
        Returns:
            Dictionary with trend data
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        daily_data = []
        current = start_date
        
        while current <= end_date:
            if class_id:
                day_summary = AttendanceRecordSelector.get_daily_summary(current, class_id)
            else:
                day_summary = AttendanceRecordSelector.get_daily_summary(current)
            
            daily_data.append({
                'date': current.isoformat(),
                'day_name': current.strftime('%A'),
                'present': day_summary['present'],
                'absent': day_summary['absent'],
                'late': day_summary['late'],
                'total': day_summary['total_students'],
                'percentage': day_summary['present_percentage'],
            })
            current += timedelta(days=1)
        
        # Calculate moving averages
        moving_avg_7day = AttendanceSelector._calculate_moving_average(daily_data, 7)
        moving_avg_30day = AttendanceSelector._calculate_moving_average(daily_data, 30)
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days,
            },
            'daily': daily_data,
            'moving_averages': {
                '7day': moving_avg_7day,
                '30day': moving_avg_30day,
            },
            'summary': {
                'average_present': sum(d['present'] for d in daily_data) / len(daily_data) if daily_data else 0,
                'average_percentage': sum(d['percentage'] for d in daily_data) / len(daily_data) if daily_data else 0,
                'best_day': max(daily_data, key=lambda x: x['percentage']) if daily_data else None,
                'worst_day': min(daily_data, key=lambda x: x['percentage']) if daily_data else None,
            }
        }

    @staticmethod
    def get_risk_assessment(
        class_id: Optional[int] = None,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Identify students at risk based on attendance.
        
        Args:
            class_id: Filter by class (optional)
            session_id: Academic session ID
            term_id: Academic term ID
            
        Returns:
            Dictionary with risk assessment data
        """
        from apps.students.selectors import StudentSelector
        
        # Get alerts
        critical = AttendanceSummarySelector.get_alerts(
            session_id=session_id,
            term_id=term_id,
            threshold='critical'
        )
        
        low = AttendanceSummarySelector.get_alerts(
            session_id=session_id,
            term_id=term_id,
            threshold='low'
        )
        
        # If class specified, filter to that class
        if class_id:
            students = StudentSelector.get_class_students(class_id, session_id)
            student_ids = [s['id'] for s in students]
            
            critical = [a for a in critical if a['student_id'] in student_ids]
            low = [a for a in low if a['student_id'] in student_ids]
        
        # Enhance with additional risk factors
        for student in critical:
            student['risk_level'] = 'HIGH'
            student['intervention_needed'] = 'IMMEDIATE'
            student['recommended_action'] = 'Parent-teacher conference required'
        
        for student in low:
            student['risk_level'] = 'MEDIUM'
            student['intervention_needed'] = 'SOON'
            student['recommended_action'] = 'Attendance monitoring and counseling'
        
        return {
            'high_risk_count': len(critical),
            'medium_risk_count': len(low),
            'total_at_risk': len(critical) + len(low),
            'high_risk_students': critical,
            'medium_risk_students': low,
            'recommendations': {
                'immediate_intervention': len(critical) > 0,
                'counseling_needed': len(low) > 5,
                'parent_notification': len(critical) > 3,
            }
        }

    @staticmethod
    def get_comparison_report(
        class_id_1: int,
        class_id_2: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Compare attendance between two classes.
        
        Args:
            class_id_1: First class ID
            class_id_2: Second class ID
            session_id: Academic session ID
            term_id: Academic term ID
            
        Returns:
            Dictionary with comparison data
        """
        from apps.corecode.selectors import StudentClassSelector
        
        class1_info = StudentClassSelector.get_by_id(class_id_1)
        class2_info = StudentClassSelector.get_by_id(class_id_2)
        
        if not class1_info or not class2_info:
            return {'error': 'One or both classes not found'}
        
        # Get summaries
        class1_summary = AttendanceSummarySelector.get_class_summary(
            class_id=class_id_1,
            session_id=session_id,
            term_id=term_id
        )
        
        class2_summary = AttendanceSummarySelector.get_class_summary(
            class_id=class_id_2,
            session_id=session_id,
            term_id=term_id
        )
        
        # Calculate differences
        diff_percentage = (
            class1_summary['average_present_percentage'] - 
            class2_summary['average_present_percentage']
        )
        
        return {
            'class_1': {
                'id': class_id_1,
                'name': class1_info['display_name'],
                'summary': class1_summary,
            },
            'class_2': {
                'id': class_id_2,
                'name': class2_info['display_name'],
                'summary': class2_summary,
            },
            'comparison': {
                'attendance_difference': round(diff_percentage, 1),
                'better_class': class1_info['display_name'] if diff_percentage > 0 else class2_info['display_name'],
                'difference_percentage': abs(round(diff_percentage, 1)),
            }
        }

    @staticmethod
    def export_attendance_data(
        class_id: Optional[int] = None,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        format: str = 'csv'
    ) -> List[Dict[str, Any]]:
        """
        Export attendance data for reporting.
        
        Args:
            class_id: Filter by class (optional)
            session_id: Academic session ID
            term_id: Academic term ID
            start_date: Start date for range
            end_date: End date for range
            format: Export format ('csv', 'excel', 'json')
            
        Returns:
            List of attendance records formatted for export
        """
        from apps.students.selectors import StudentSelector
        
        # Build queryset filters
        filters = {}
        if session_id:
            filters['register__academic_session_id'] = session_id
        if term_id:
            filters['register__academic_term_id'] = term_id
        if start_date:
            filters['register__date__gte'] = start_date
        if end_date:
            filters['register__date__lte'] = end_date
        
        # If class specified, get students in that class
        if class_id:
            students = StudentSelector.get_class_students(class_id, session_id)
            student_ids = [s['id'] for s in students]
            filters['student_id__in'] = student_ids
        
        # Get records
        records = AttendanceRecord.objects.filter(**filters).select_related(
            'register__student_class',
            'register__academic_session',
            'register__academic_term'
        ).order_by('register__date', 'student_name')
        
        export_data = []
        for rec in records:
            export_data.append({
                'date': rec.register.date.isoformat(),
                'day_of_week': rec.register.date.strftime('%A'),
                'student_id': rec.student_id,
                'student_name': rec.student_name,
                'class': rec.register.student_class.display_name,
                'session': rec.register.academic_session.name,
                'term': rec.register.academic_term.get_term_display() if rec.register.academic_term else None,
                'session_type': rec.register.get_session_type_display(),
                'status': rec.get_status_display(),
                'check_in_time': rec.check_in_time.isoformat() if rec.check_in_time else '',
                'remarks': rec.remarks or '',
            })
        
        return export_data

    @staticmethod
    def _get_monthly_breakdown(
        student_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Helper method to get monthly attendance breakdown."""
        records = AttendanceRecord.objects.filter(student_id=student_id)
        
        if session_id:
            records = records.filter(register__academic_session_id=session_id)
        if term_id:
            records = records.filter(register__academic_term_id=term_id)
        
        # Group by month
        monthly = {}
        for rec in records:
            month_key = rec.register.date.strftime('%Y-%m')
            if month_key not in monthly:
                monthly[month_key] = {
                    'month': rec.register.date.strftime('%B %Y'),
                    'total': 0,
                    'present': 0,
                    'absent': 0,
                    'late': 0,
                }
            
            monthly[month_key]['total'] += 1
            if rec.status == 'present':
                monthly[month_key]['present'] += 1
            elif rec.status == 'absent':
                monthly[month_key]['absent'] += 1
            elif rec.status == 'late':
                monthly[month_key]['late'] += 1
        
        # Calculate percentages
        result = []
        for month, data in monthly.items():
            data['percentage'] = round(
                (data['present'] / data['total'] * 100) if data['total'] > 0 else 0,
                1
            )
            result.append(data)
        
        return sorted(result, key=lambda x: x['month'])

    @staticmethod
    def _calculate_student_stats(
        records: List[Dict[str, Any]],
        summary: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Helper method to calculate student statistics."""
        if not records:
            return {
                'total_days': 0,
                'present_count': 0,
                'absent_count': 0,
                'late_count': 0,
                'attendance_rate': 0,
                'punctuality_rate': 0,
                'current_streak': 0,
                'best_streak': 0,
            }
        
        # Calculate streaks
        current_streak = 0
        best_streak = 0
        streak = 0
        
        for rec in sorted(records, key=lambda x: x['date']):
            if rec['status'] == 'present' or rec['status'] == 'late':
                streak += 1
                current_streak = streak
                if streak > best_streak:
                    best_streak = streak
            else:
                streak = 0
        
        present_count = len([r for r in records if r['status'] == 'present'])
        absent_count = len([r for r in records if r['status'] == 'absent'])
        late_count = len([r for r in records if r['status'] == 'late'])
        total = len(records)
        
        return {
            'total_days': total,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'attendance_rate': round((present_count / total * 100) if total > 0 else 0, 1),
            'punctuality_rate': round(
                ((present_count) / (present_count + late_count) * 100) 
                if (present_count + late_count) > 0 else 0, 
                1
            ),
            'current_streak': current_streak,
            'best_streak': best_streak,
        }

    @staticmethod
    def _calculate_moving_average(
        daily_data: List[Dict[str, Any]],
        window: int
    ) -> List[Dict[str, Any]]:
        """Helper method to calculate moving average."""
        if len(daily_data) < window:
            return []
        
        moving_avg = []
        for i in range(len(daily_data) - window + 1):
            window_data = daily_data[i:i + window]
            avg = sum(d['percentage'] for d in window_data) / window
            moving_avg.append({
                'date': daily_data[i + window - 1]['date'],
                'average': round(avg, 1),
            })
        
        return moving_avg

    @staticmethod
    def _get_attendance_trend(
        days: int = 30,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Helper method to get overall attendance trend."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        trend = []
        current = start_date
        
        while current <= end_date:
            day_summary = AttendanceRecordSelector.get_daily_summary(current)
            trend.append({
                'date': current.isoformat(),
                'percentage': day_summary['present_percentage'],
                'total': day_summary['total_students'],
            })
            current += timedelta(days=1)
        
        return trend


class AttendanceRegisterSelector:
    """Attendance register read operations"""
    
    @staticmethod
    def get_by_id(register_id: int) -> Optional[Dict[str, Any]]:
        """Get register by ID"""
        try:
            reg = AttendanceRegister.objects.select_related(
                'student_class', 'academic_session', 'academic_term',
                'marked_by', 'closed_by'
            ).prefetch_related('records').get(id=register_id)
            
            return {
                'id': reg.id,
                'register_number': reg.register_number,
                'student_class': {
                    'id': reg.student_class.id,
                    'name': reg.student_class.name,
                    'display_name': reg.student_class.display_name,
                },
                'academic_session': {
                    'id': reg.academic_session.id,
                    'name': reg.academic_session.name,
                },
                'academic_term': {
                    'id': reg.academic_term.id,
                    'name': reg.academic_term.name,
                } if reg.academic_term else None,
                'date': reg.date.isoformat(),
                'session_type': reg.session_type,
                'session_type_display': reg.get_session_type_display(),
                'total_students': reg.total_students,
                'present_count': reg.present_count,
                'absent_count': reg.absent_count,
                'late_count': reg.late_count,
                'excused_count': reg.excused_count,
                'present_percentage': reg.present_percentage,
                'is_closed': reg.is_closed,
                'closed_at': reg.closed_at.isoformat() if reg.closed_at else None,
                'closed_by': reg.closed_by.get_full_name() if reg.closed_by else None,
                'marked_by': reg.marked_by.get_full_name() if reg.marked_by else None,
                'marking_method': reg.get_marking_method_display(),
                'created_at': reg.created_at.isoformat(),
                
                'records': [
                    {
                        'id': r.id,
                        'student_id': r.student_id,
                        'student_name': r.student_name,
                        'status': r.status,
                        'status_display': r.get_status_display(),
                        'check_in_time': r.check_in_time.isoformat() if r.check_in_time else None,
                        'check_out_time': r.check_out_time.isoformat() if r.check_out_time else None,
                        'remarks': r.remarks,
                    }
                    for r in reg.records.all().order_by('student_name')
                ],
            }
        except AttendanceRegister.DoesNotExist:
            return None
    
    @staticmethod
    def get_for_date(
        date: date,
        class_id: Optional[int] = None,
        session_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get registers for a specific date"""
        queryset = AttendanceRegister.objects.filter(date=date).select_related(
            'student_class', 'academic_session'
        )
        
        if class_id:
            queryset = queryset.filter(student_class_id=class_id)
        
        if session_type:
            queryset = queryset.filter(session_type=session_type)
        
        registers = []
        for reg in queryset.order_by('student_class__name'):
            registers.append({
                'id': reg.id,
                'register_number': reg.register_number,
                'class_name': reg.student_class.display_name,
                'session_type': reg.get_session_type_display(),
                'total_students': reg.total_students,
                'present_count': reg.present_count,
                'absent_count': reg.absent_count,
                'present_percentage': reg.present_percentage,
                'is_closed': reg.is_closed,
            })
        
        return registers
    
    @staticmethod
    def list_registers(
        class_id: Optional[int] = None,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List attendance registers with filters"""
        queryset = AttendanceRegister.objects.select_related(
            'student_class', 'academic_session', 'academic_term'
        )
        
        if class_id:
            queryset = queryset.filter(student_class_id=class_id)
        
        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        
        if term_id:
            queryset = queryset.filter(academic_term_id=term_id)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        registers = []
        for reg in queryset.order_by('-date', 'student_class__name')[:limit]:
            registers.append({
                'id': reg.id,
                'register_number': reg.register_number,
                'class': reg.student_class.display_name,
                'date': reg.date.isoformat(),
                'session_type': reg.get_session_type_display(),
                'total_students': reg.total_students,
                'present_count': reg.present_count,
                'present_percentage': reg.present_percentage,
                'is_closed': reg.is_closed,
            })
        
        return registers


class AttendanceRecordSelector:
    """Attendance record read operations"""
    
    @staticmethod
    def get_student_records(
        student_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get attendance records for a student"""
        queryset = AttendanceRecord.objects.filter(
            student_id=student_id
        ).select_related('register__student_class')
        
        if session_id:
            queryset = queryset.filter(register__academic_session_id=session_id)
        
        if term_id:
            queryset = queryset.filter(register__academic_term_id=term_id)
        
        records = []
        for rec in queryset.order_by('-register__date')[:limit]:
            records.append({
                'id': rec.id,
                'date': rec.register.date.isoformat(),
                'session_type': rec.register.get_session_type_display(),
                'status': rec.status,
                'status_display': rec.get_status_display(),
                'check_in_time': rec.check_in_time.isoformat() if rec.check_in_time else None,
                'remarks': rec.remarks,
                'class_name': rec.register.student_class.display_name,
            })
        
        return records
    
    @staticmethod
    def get_daily_summary(
        date: date,
        class_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get daily attendance summary"""
        registers = AttendanceRegister.objects.filter(date=date)
        
        if class_id:
            registers = registers.filter(student_class_id=class_id)
        
        total_students = sum(r.total_students for r in registers)
        total_present = sum(r.present_count for r in registers)
        total_absent = sum(r.absent_count for r in registers)
        total_late = sum(r.late_count for r in registers)
        
        return {
            'date': date.isoformat(),
            'total_registers': registers.count(),
            'total_students': total_students,
            'present': total_present,
            'absent': total_absent,
            'late': total_late,
            'present_percentage': (total_present / total_students * 100) if total_students > 0 else 0,
            'by_class': [
                {
                    'class': r.student_class.display_name,
                    'present': r.present_count,
                    'absent': r.absent_count,
                    'percentage': r.present_percentage,
                }
                for r in registers
            ],
        }


class AttendanceSummarySelector:
    """Attendance summary read operations"""
    
    @staticmethod
    def get_student_summary(
        student_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get attendance summary for a student"""
        queryset = AttendanceSummary.objects.filter(student_id=student_id)
        
        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        
        if term_id:
            queryset = queryset.filter(academic_term_id=term_id)
        
        summary = queryset.first()
        
        if not summary:
            return None
        
        return {
            'student_id': summary.student_id,
            'student_name': summary.student_name,
            'session': summary.academic_session.name,
            'term': summary.academic_term.get_term_display() if summary.academic_term else None,
            'total_days': summary.total_days,
            'present': summary.present_days,
            'absent': summary.absent_days,
            'late': summary.late_days,
            'excused': summary.excused_days,
            'present_percentage': summary.present_percentage,
            'attendance_score': summary.attendance_score,
            'attendance_alert': summary.attendance_alert,
            'alert_reason': summary.alert_reason,
        }
    
    @staticmethod
    def get_class_summary(
        class_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get attendance summary for an entire class"""
        from apps.students.selectors import StudentSelector
        
        students = StudentSelector.get_class_students(
            class_id=class_id,
            academic_session_id=session_id
        )
        
        summaries = AttendanceSummary.objects.filter(
            student_id__in=[s['id'] for s in students],
            academic_session_id=session_id,
            academic_term_id=term_id
        )
        
        total_students = len(students)
        avg_attendance = summaries.aggregate(
            avg=Avg('present_percentage')
        )['avg'] or 0
        
        alert_count = summaries.filter(attendance_alert=True).count()
        
        return {
            'class_id': class_id,
            'total_students': total_students,
            'students_with_summary': summaries.count(),
            'average_attendance': avg_attendance,
            'alert_count': alert_count,
            'attendance_distribution': {
                'excellent': summaries.filter(present_percentage__gte=90).count(),
                'good': summaries.filter(present_percentage__gte=75, present_percentage__lt=90).count(),
                'fair': summaries.filter(present_percentage__gte=50, present_percentage__lt=75).count(),
                'poor': summaries.filter(present_percentage__lt=50).count(),
            }
        }
    
    @staticmethod
    def get_alerts(
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        threshold: str = 'all'
    ) -> List[Dict[str, Any]]:
        """Get students with attendance alerts"""
        queryset = AttendanceSummary.objects.filter(attendance_alert=True)
        
        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        
        if term_id:
            queryset = queryset.filter(academic_term_id=term_id)
        
        if threshold == 'critical':
            queryset = queryset.filter(present_percentage__lt=50)
        elif threshold == 'low':
            queryset = queryset.filter(
                present_percentage__gte=50,
                present_percentage__lt=75
            )
        
        alerts = []
        for summary in queryset.order_by('-present_percentage')[:50]:
            alerts.append({
                'student_id': summary.student_id,
                'student_name': summary.student_name,
                'present_percentage': summary.present_percentage,
                'alert_reason': summary.alert_reason,
                'total_days': summary.total_days,
                'absent_days': summary.absent_days,
            })
        
        return alerts


class QRCodeSelector:
    """QR code read operations"""
    
    @staticmethod
    def get_for_student(student_id: int) -> Optional[Dict[str, Any]]:
        """Get QR code for a student"""
        try:
            qr = QRCode.objects.get(student_id=student_id)
            return {
                'id': qr.id,
                'student_id': qr.student_id,
                'student_name': qr.student_name,
                'code': qr.code,
                'qr_image_url': qr.qr_image.url if qr.qr_image else None,
                'is_active': qr.is_active,
                'expires_at': qr.expires_at.isoformat() if qr.expires_at else None,
                'last_used': qr.last_used.isoformat() if qr.last_used else None,
                'use_count': qr.use_count,
            }
        except QRCode.DoesNotExist:
            return None
    
    @staticmethod
    def validate_code(code: str) -> Optional[Dict[str, Any]]:
        """Validate QR code and return student info"""
        try:
            qr = QRCode.objects.get(code=code, is_active=True)
            
            if not qr.is_valid():
                return None
            
            return {
                'student_id': qr.student_id,
                'student_name': qr.student_name,
                'code': qr.code,
            }
        except QRCode.DoesNotExist:
            return None
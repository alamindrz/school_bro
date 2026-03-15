"""
Report Service - Result reporting and analytics
"""

from django.db.models import Avg, Count, Sum, Max, Min
from typing import List, Dict, Any, Optional
from datetime import date
import logging

from ..models import ResultSheet, Result, CumulativeRecord
from ..constants import GradeSystem, ResultStatus
from ..selectors import ResultSelector, CumulativeSelector

from apps.corecode.selectors import AcademicSessionSelector
from apps.students.selectors import StudentSelector

logger = logging.getLogger(__name__)


class ReportService:
    """
    Result reporting and analytics
    """

    @staticmethod
    def generate_term_report(
        sheet_id: int
    ) -> Dict[str, Any]:
        """
        Generate comprehensive term report for a result sheet
        """
        from ..selectors import ResultSheetSelector

        sheet = ResultSheetSelector.get_by_id(sheet_id)
        if not sheet:
            return {'error': 'Result sheet not found'}

        # Get all students with results
        students = sheet['students']

        # Calculate class statistics
        totals = []
        averages = []
        grade_distribution = {grade: 0 for grade, _ in GradeSystem.CHOICES}

        for student in students:
            student_total = sum(r['total'] or 0 for r in student['results'])
            student_avg = student_total / len(student['results']) if student['results'] else 0

            totals.append(student_total)
            averages.append(student_avg)

            # Count grades
            for result in student['results']:
                if result['grade']:
                    grade_distribution[result['grade']] += 1

        # Subject performance
        subject_performance = []
        for subject in sheet['subjects']:
            subject_results = [
                r for student in students
                for r in student['results']
                if r['subject_id'] == subject['id']
            ]

            if subject_results:
                scores = [r['total'] or 0 for r in subject_results]
                subject_performance.append({
                    'subject_id': subject['id'],
                    'subject_name': subject['name'],
                    'average': sum(scores) / len(scores),
                    'highest': max(scores),
                    'lowest': min(scores),
                    'student_count': len(subject_results),
                    'pass_count': len([s for s in scores if s >= subject['pass_mark']]),
                    'pass_percentage': (len([s for s in scores if s >= subject['pass_mark']]) / len(scores)) * 100,
                })

        return {
            'sheet': sheet,
            'summary': {
                'total_students': len(students),
                'class_average': sum(averages) / len(averages) if averages else 0,
                'highest_average': max(averages) if averages else 0,
                'lowest_average': min(averages) if averages else 0,
                'total_subjects': len(sheet['subjects']),
            },
            'grade_distribution': grade_distribution,
            'subject_performance': subject_performance,
            'top_students': sorted(
                [{'name': s['name'], 'average': sum(r['total'] or 0 for r in s['results']) / len(s['results'])}
                 for s in students],
                key=lambda x: x['average'],
                reverse=True
            )[:10],
        }

    @staticmethod
    def generate_student_report_card(
        student_id: int,
        session_id: int,
        term_id: int
    ) -> Dict[str, Any]:
        """
        Generate individual student report card
        """
        # Get student info
        student = StudentSelector.get_by_id(student_id)
        if not student:
            return {'error': 'Student not found'}

        # Get result sheet
        try:
            sheet = ResultSheet.objects.get(
                academic_session_id=session_id,
                academic_term_id=term_id,
                status=ResultStatus.PUBLISHED
            )
        except ResultSheet.DoesNotExist:
            return {'error': 'Results not published'}

        # Get student's results
        results = Result.objects.filter(
            result_sheet=sheet,
            student_id=student_id
        ).select_related('subject').order_by('subject__name')

        if not results.exists():
            return {'error': 'No results found for this student'}

        # Get comments
        try:
            comments = ResultComment.objects.get(
                result_sheet=sheet,
                student_id=student_id
            )
        except ResultComment.DoesNotExist:
            comments = None

        # Calculate totals
        total_subjects = results.count()
        total_score = sum(r.total_score or 0 for r in results)
        average = total_score / total_subjects if total_subjects > 0 else 0

        # Get position
        position = results.first().position if results.exists() else None

        # Get cumulative record
        cumulative = CumulativeRecord.objects.filter(
            student_id=student_id,
            academic_session_id=session_id
        ).first()

        return {
            'student': student,
            'session': sheet.academic_session.name,
            'term': sheet.academic_term.get_term_display(),
            'sheet_number': sheet.sheet_number,
            'results': [
                {
                    'subject': r.subject.name,
                    'ca1': r.ca1_score,
                    'ca2': r.ca2_score,
                    'ca3': r.ca3_score,
                    'exam': r.exam_score,
                    'practical': r.practical_score,
                    'project': r.project_score,
                    'total': r.total_score,
                    'grade': r.grade,
                    'remark': r.get_remark_display() if r.remark else r.custom_remark,
                }
                for r in results
            ],
            'summary': {
                'total_subjects': total_subjects,
                'total_score': total_score,
                'average': round(average, 2),
                'position': position,
            },
            'comments': {
                'teacher': comments.teacher_comment if comments else '',
                'class_teacher': comments.class_teacher_comment if comments else '',
                'principal': comments.principal_comment if comments else '',
                'next_term': comments.next_term_recommendation if comments else '',
            } if comments else None,
            'cumulative': {
                'term1_average': cumulative.term1_average if cumulative else None,
                'term2_average': cumulative.term2_average if cumulative else None,
                'term3_average': cumulative.term3_average if cumulative else None,
                'session_average': cumulative.session_average if cumulative else None,
            } if cumulative else None,
        }

    @staticmethod
    def generate_session_summary(
        session_id: int
    ) -> Dict[str, Any]:
        """
        Generate summary report for an entire session
        """
        # Get all result sheets for this session
        sheets = ResultSheet.objects.filter(
            academic_session_id=session_id,
            status=ResultStatus.PUBLISHED
        ).select_related('student_class', 'academic_term')

        if not sheets.exists():
            return {'error': 'No published results for this session'}

        # Group by class
        class_summaries = {}
        for sheet in sheets:
            class_name = sheet.student_class.display_name
            if class_name not in class_summaries:
                class_summaries[class_name] = {
                    'class_id': sheet.student_class_id,
                    'term1': None,
                    'term2': None,
                    'term3': None,
                }

            term = sheet.academic_term.term
            report = ReportService.generate_term_report(sheet.id)

            if term == 1:
                class_summaries[class_name]['term1'] = report.get('summary', {})
            elif term == 2:
                class_summaries[class_name]['term2'] = report.get('summary', {})
            elif term == 3:
                class_summaries[class_name]['term3'] = report.get('summary', {})

        # Overall session statistics
        all_results = Result.objects.filter(
            result_sheet__academic_session_id=session_id,
            result_sheet__status=ResultStatus.PUBLISHED
        )

        total_students = all_results.values('student_id').distinct().count()
        total_subjects = all_results.values('subject_id').distinct().count()
        avg_score = all_results.aggregate(avg=Avg('total_score'))['avg'] or 0

        return {
            'session': AcademicSessionSelector.get_by_id(session_id)['name'],
            'class_summaries': class_summaries,
            'overall': {
                'total_students': total_students,
                'total_subjects': total_subjects,
                'average_score': round(avg_score, 2),
                'total_sheets': sheets.count(),
            }
        }

    @staticmethod
    def generate_performance_trends(
        student_id: int
    ) -> Dict[str, Any]:
        """
        Generate performance trends across sessions
        """
        # Get all cumulative records for this student
        records = CumulativeRecord.objects.filter(
            student_id=student_id
        ).order_by('academic_session')

        if not records.exists():
            return {'error': 'No cumulative records found'}

        trends = []
        for record in records:
            trends.append({
                'session': record.academic_session.name,
                'term1_average': record.term1_average,
                'term2_average': record.term2_average,
                'term3_average': record.term3_average,
                'session_average': record.session_average,
                'promoted': record.promoted_to_next_class,
            })

        # Calculate improvement rate
        if len(trends) >= 2:
            first_avg = trends[0]['session_average'] or 0
            last_avg = trends[-1]['session_average'] or 0
            improvement = last_avg - first_avg
            improvement_rate = (improvement / first_avg * 100) if first_avg > 0 else 0
        else:
            improvement = 0
            improvement_rate = 0

        return {
            'student_id': student_id,
            'trends': trends,
            'summary': {
                'sessions_attended': len(trends),
                'overall_improvement': round(improvement, 2),
                'improvement_rate': round(improvement_rate, 2),
                'best_session': max(trends, key=lambda x: x['session_average'] or 0)['session'] if trends else None,
                'best_average': max(t['session_average'] or 0 for t in trends) if trends else 0,
            }
        }
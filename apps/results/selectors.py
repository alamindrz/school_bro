"""
Results Selectors - READ Layer
Returns dicts, never model instances
"""

from django.db.models import Q, Avg, Sum, Count, Max, Min
from django.db.models.functions import Coalesce
from typing import Optional, List, Dict, Any
from decimal import Decimal

from .models import (
  ResultSheet, Result, ResultComment,
    CumulativeRecord
)
from apps.corecode.models import Subject
from .constants import ResultStatus, GradeSystem

from apps.corecode.selectors import (
    AcademicSessionSelector, AcademicTermSelector,
    StudentClassSelector
)
from apps.students.selectors import StudentSelector
from apps.finance.selectors import FinancialStatusSelector




class ResultSheetSelector:
    """Result sheet read operations"""
    
    @staticmethod
    def get_by_id(sheet_id: int) -> Optional[Dict[str, Any]]:
        """Get result sheet by ID"""
        try:
            sheet = ResultSheet.objects.select_related(
                'student_class', 'academic_session', 'academic_term',
                'created_by', 'submitted_by', 'approved_by', 'published_by'
            ).prefetch_related(
                'subjects', 'sheet_subjects', 'results'
            ).get(id=sheet_id)
            
            # Get subjects with teachers
            subjects = []
            for ss in sheet.sheet_subjects.select_related('subject').all():
                subjects.append({
                    'id': ss.subject.id,
                    'name': ss.subject.name,
                    'code': ss.subject.code,
                    'teacher_id': ss.teacher_id,
                    'teacher_name': ss.teacher_name,
                    'pass_mark': ss.pass_mark,
                    'has_practical': ss.has_practical,
                    'has_project': ss.has_project,
                })
            
            # Get student list with results
            students = {}
            for result in sheet.results.select_related('subject').all():
                if result.student_id not in students:
                    students[result.student_id] = {
                        'id': result.student_id,
                        'name': result.student_name,
                        'results': []
                    }
                students[result.student_id]['results'].append({
                    'subject_id': result.subject.id,
                    'subject_name': result.subject.name,
                    'ca1': result.ca1_score,
                    'ca2': result.ca2_score,
                    'ca3': result.ca3_score,
                    'exam': result.exam_score,
                    'practical': result.practical_score,
                    'project': result.project_score,
                    'total': result.total_score,
                    'grade': result.grade,
                    'grade_point': result.grade_point,
                    'remark': result.get_remark_display() if result.remark else None,
                })
            
            return {
                'id': sheet.id,
                'sheet_number': sheet.sheet_number,
                'student_class': {
                    'id': sheet.student_class.id,
                    'name': sheet.student_class.display_name,
                },
                'academic_session': {
                    'id': sheet.academic_session.id,
                    'name': sheet.academic_session.name,
                },
                'academic_term': {
                    'id': sheet.academic_term.id,
                    'name': sheet.academic_term.name,
                },
                'status': sheet.status,
                'status_display': sheet.get_status_display(),
                'subjects': subjects,
                'students': list(students.values()),
                'can_edit': sheet.can_edit(),
                'can_approve': sheet.can_approve(),
                'can_publish': sheet.can_publish(),
                'submitted_by': sheet.submitted_by.get_full_name() if sheet.submitted_by else None,
                'submitted_at': sheet.submitted_at.isoformat() if sheet.submitted_at else None,
                'approved_by': sheet.approved_by.get_full_name() if sheet.approved_by else None,
                'approved_at': sheet.approved_at.isoformat() if sheet.approved_at else None,
                'published_by': sheet.published_by.get_full_name() if sheet.published_by else None,
                'published_at': sheet.published_at.isoformat() if sheet.published_at else None,
                'created_by': sheet.created_by.get_full_name() if sheet.created_by else None,
                'created_at': sheet.created_at.isoformat(),
            }
        except ResultSheet.DoesNotExist:
            return None
    
    @staticmethod
    def list_sheets(
        class_id: Optional[int] = None,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List result sheets with filters"""
        queryset = ResultSheet.objects.select_related(
            'student_class', 'academic_session', 'academic_term'
        )
        
        if class_id:
            queryset = queryset.filter(student_class_id=class_id)
        
        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        
        if term_id:
            queryset = queryset.filter(academic_term_id=term_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        sheets = []
        for sheet in queryset.order_by('-academic_session', '-academic_term', 'student_class')[:limit]:
            sheets.append({
                'id': sheet.id,
                'sheet_number': sheet.sheet_number,
                'class': sheet.student_class.display_name,
                'session': sheet.academic_session.name,
                'term': sheet.academic_term.get_term_display(),
                'status': sheet.status,
                'status_display': sheet.get_status_display(),
                'subject_count': sheet.subjects.count(),
                'student_count': sheet.results.values('student_id').distinct().count(),
                'created_at': sheet.created_at.isoformat(),
            })
        
        return sheets


class ResultSelector:
    """Individual result read operations"""
    
    @staticmethod
    def get_student_results(
        student_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all results for a student"""
        queryset = Result.objects.filter(
            student_id=student_id
        ).select_related(
            'result_sheet', 'subject'
        ).order_by('result_sheet__academic_session', 'result_sheet__academic_term', 'subject__name')
        
        if session_id:
            queryset = queryset.filter(result_sheet__academic_session_id=session_id)
        
        if term_id:
            queryset = queryset.filter(result_sheet__academic_term_id=term_id)
        
        results = []
        for result in queryset:
            results.append({
                'id': result.id,
                'session': result.result_sheet.academic_session.name,
                'term': result.result_sheet.academic_term.get_term_display(),
                'subject': result.subject.name,
                'subject_code': result.subject.code,
                'ca1': result.ca1_score,
                'ca2': result.ca2_score,
                'ca3': result.ca3_score,
                'exam': result.exam_score,
                'practical': result.practical_score,
                'project': result.project_score,
                'total': result.total_score,
                'grade': result.grade,
                'grade_point': result.grade_point,
                'remark': result.get_remark_display() if result.remark else result.custom_remark,
                'position': result.position,
            })
        
        return results
    
    @staticmethod
    def get_term_summary(
        student_id: int,
        sheet_id: int
    ) -> Dict[str, Any]:
        """Get term summary for a student"""
        results = Result.objects.filter(
            student_id=student_id,
            result_sheet_id=sheet_id
        ).select_related('subject')
        
        if not results.exists():
            return {}
        
        total_subjects = results.count()
        total_score = sum(r.total_score or 0 for r in results)
        average = total_score / total_subjects if total_subjects > 0 else 0
        
        # Count grades
        grade_counts = {}
        for grade, _ in GradeSystem.CHOICES:
            count = results.filter(grade=grade).count()
            if count > 0:
                grade_counts[grade] = count
        
        return {
            'student_id': student_id,
            'total_subjects': total_subjects,
            'total_score': total_score,
            'average': round(average, 2),
            'grade_counts': grade_counts,
            'best_subject': results.order_by('-total_score').first().subject.name if results else None,
            'best_score': results.aggregate(Max('total_score'))['total_score__max'],
            'worst_subject': results.order_by('total_score').first().subject.name if results else None,
            'worst_score': results.aggregate(Min('total_score'))['total_score__min'],
        }
    
    @staticmethod
    def check_availability(
        student_id: int,
        session_id: int,
        term_id: int
    ) -> Dict[str, Any]:
        """Check if results are available for a student"""
        try:
            sheet = ResultSheet.objects.get(
                academic_session_id=session_id,
                academic_term_id=term_id,
                status=ResultStatus.PUBLISHED
            )
            
            has_results = Result.objects.filter(
                result_sheet=sheet,
                student_id=student_id
            ).exists()
            
            return {
                'available': has_results,
                'sheet_id': sheet.id if has_results else None,
                'sheet_number': sheet.sheet_number if has_results else None,
                'status': sheet.status,
            }
        except ResultSheet.DoesNotExist:
            return {
                'available': False,
                'sheet_id': None,
                'sheet_number': None,
                'status': None,
            }


class CumulativeSelector:
    """Cumulative record read operations"""
    
    @staticmethod
    def get_student_summary(
        student_id: int,
        session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get cumulative summary for a student"""
        queryset = CumulativeRecord.objects.filter(student_id=student_id)
        
        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        
        records = []
        for record in queryset.order_by('-academic_session'):
            records.append({
                'session': record.academic_session.name,
                'term1_average': record.term1_average,
                'term1_position': record.term1_position,
                'term2_average': record.term2_average,
                'term2_position': record.term2_position,
                'term3_average': record.term3_average,
                'term3_position': record.term3_position,
                'session_average': record.session_average,
                'session_position': record.session_position,
                'promoted': record.promoted_to_next_class,
            })
        
        # Calculate overall performance trend
        if records:
            averages = [r['session_average'] for r in records if r['session_average']]
            trend = 'improving' if len(averages) > 1 and averages[-1] > averages[0] else 'stable'
        else:
            trend = 'no_data'
        
        return {
            'student_id': student_id,
            'records': records,
            'trend': trend,
            'total_sessions': len(records),
        }
    
    @staticmethod
    def get_class_summary(
        class_id: int,
        session_id: int
    ) -> Dict[str, Any]:
        """Get cumulative summary for an entire class"""
        from apps.students.selectors import StudentSelector
        
        students = StudentSelector.get_class_students(class_id, session_id)
        student_ids = [s['id'] for s in students]
        
        records = CumulativeRecord.objects.filter(
            student_id__in=student_ids,
            academic_session_id=session_id
        )
        
        # Class statistics
        averages = [r.session_average for r in records if r.session_average]
        if averages:
            class_average = sum(averages) / len(averages)
            highest = max(averages)
            lowest = min(averages)
        else:
            class_average = highest = lowest = 0
        
        return {
            'class_id': class_id,
            'session_id': session_id,
            'total_students': len(students),
            'students_with_records': records.count(),
            'class_average': round(class_average, 2),
            'highest_average': round(highest, 2),
            'lowest_average': round(lowest, 2),
            'promotion_rate': records.filter(promoted_to_next_class=True).count() / records.count() * 100 if records.exists() else 0,
        }
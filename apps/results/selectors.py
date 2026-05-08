"""
Results Selectors - READ Layer
Returns dicts, never model instances
"""

from django.db.models import Q, Avg, Sum, Count, Max, Min
from typing import Optional, List, Dict, Any

from .models import ScoreSheet, ScoreEntry, CumulativeRecord
from apps.corecode.selectors import (
    AcademicSessionSelector, AcademicTermSelector, StudentClassSelector, SubjectSelector
)
from apps.students.selectors import StudentSelector


class ScoreSheetSelector:
    """Score sheet read operations"""

    @staticmethod
    def get_by_id(sheet_id: int) -> Optional[Dict[str, Any]]:
        """Get score sheet by ID with all entries."""
        try:
            sheet = ScoreSheet.objects.select_related(
                'subject', 'student_class', 'academic_session', 'academic_term',
                'created_by', 'submitted_by'
            ).prefetch_related('entries').get(id=sheet_id)

            entries = []
            for entry in sheet.entries.all().order_by('student_name'):
                entries.append({
                    'id': entry.id,
                    'student_id': entry.student_id,
                    'student_name': entry.student_name,
                    'ca1': entry.ca1,
                    'ca2': entry.ca2,
                    'ca3': entry.ca3,
                    'exam': entry.exam,
                    'total_score': entry.total_score,
                    'grade': entry.grade,
                    'position': entry.position,
                    'all_filled': all([
                        entry.ca1 is not None,
                        entry.ca2 is not None,
                        entry.ca3 is not None,
                        entry.exam is not None,
                    ]),
                })

            return {
                'id': sheet.id,
                'subject_id': sheet.subject_id,
                'class_id': sheet.student_class_id,
                'subject': {
                    'id': sheet.subject.id,
                    'name': sheet.subject.name,
                    'code': sheet.subject.code,
                },
                'student_class': {
                    'id': sheet.student_class.id,
                    'name': sheet.student_class.display_name,
                    'education_level': sheet.student_class.education_level,
                },
                'academic_session': {
                    'id': sheet.academic_session.id,
                    'name': sheet.academic_session.name,
                },
                'academic_term': {
                    'id': sheet.academic_term.id,
                    'name': sheet.academic_term.name,
                    'term': sheet.academic_term.term,
                },
                'status': sheet.status,
                'status_display': sheet.get_status_display(),
                'is_editable': sheet.is_editable,
                'entries': entries,
                'total_students': len(entries),
                'filled_count': len([e for e in entries if e['all_filled']]),
                'created_by': sheet.created_by.get_full_name() if sheet.created_by else None,
                'submitted_by': sheet.submitted_by.get_full_name() if sheet.submitted_by else None,
                'submitted_at': sheet.submitted_at.isoformat() if sheet.submitted_at else None,
                'created_at': sheet.created_at.isoformat(),
            }
        except ScoreSheet.DoesNotExist:
            return None

    @staticmethod
    def list_sheets(
        class_id: Optional[int] = None,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List score sheets with filters."""
        queryset = ScoreSheet.objects.select_related(
            'subject', 'student_class', 'academic_session', 'academic_term'
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
        for sheet in queryset.order_by('subject__name')[:limit]:
            filled = sheet.entries.filter(total_score__isnull=False).count()
            total = sheet.entries.count()
            sheets.append({
                'id': sheet.id,
                'subject_id': sheet.subject_id,
                'class_id': sheet.student_class_id,
                'subject_name': sheet.subject.name,
                'subject_code': sheet.subject.code,
                'class_name': sheet.student_class.display_name,
                'session': sheet.academic_session.name,
                'term': sheet.academic_term.get_term_display(),
                'status': sheet.status,
                'status_display': sheet.get_status_display(),
                'is_editable': sheet.is_editable,
                'filled': filled,
                'total': total,
                'completion': round(filled / total * 100, 1) if total > 0 else 0,
            })

        return sheets

    @staticmethod
    def get_or_create_sheet(
        subject_id: int,
        class_id: int,
        session_id: int,
        term_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get existing sheet or create a new one."""
        from .services.result import ScoreSheetService

        sheet = ScoreSheetService.create_sheet(
            subject_id=subject_id,
            class_id=class_id,
            session_id=session_id,
            term_id=term_id
        )

        return ScoreSheetSelector.get_by_id(sheet.id)

    @staticmethod
    def get_sheets_for_class(
        class_id: int,
        session_id: int,
        term_id: int
    ) -> List[Dict[str, Any]]:
        """Get all score sheets for a class in a term."""
        return ScoreSheetSelector.list_sheets(
            class_id=class_id,
            session_id=session_id,
            term_id=term_id
        )


class ScoreEntrySelector:
    """Score entry read operations"""

    @staticmethod
    def get_by_id(entry_id: int) -> Optional[Dict[str, Any]]:
        """Get a single score entry."""
        try:
            entry = ScoreEntry.objects.select_related(
                'score_sheet__subject'
            ).get(id=entry_id)

            return {
                'id': entry.id,
                'sheet_id': entry.score_sheet_id,
                'subject_name': entry.score_sheet.subject.name,
                'student_id': entry.student_id,
                'student_name': entry.student_name,
                'ca1': entry.ca1,
                'ca2': entry.ca2,
                'ca3': entry.ca3,
                'exam': entry.exam,
                'total_score': entry.total_score,
                'grade': entry.grade,
                'position': entry.position,
            }
        except ScoreEntry.DoesNotExist:
            return None

    @staticmethod
    def get_student_results(
        student_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all results for a student across subjects."""
        queryset = ScoreEntry.objects.filter(
            student_id=student_id
        ).select_related(
            'score_sheet__subject', 'score_sheet__academic_term'
        ).order_by('score_sheet__subject__name')

        if session_id:
            queryset = queryset.filter(score_sheet__academic_session_id=session_id)
        if term_id:
            queryset = queryset.filter(score_sheet__academic_term_id=term_id)

        results = []
        for entry in queryset:
            results.append({
                'id': entry.id,
                'subject': entry.score_sheet.subject.name,
                'subject_code': entry.score_sheet.subject.code,
                'term': entry.score_sheet.academic_term.get_term_display(),
                'ca1': entry.ca1,
                'ca2': entry.ca2,
                'ca3': entry.ca3,
                'exam': entry.exam,
                'total': entry.total_score,
                'grade': entry.grade,
                'position': entry.position,
            })

        return results

    @staticmethod
    def get_student_summary(
        student_id: int,
        session_id: int,
        term_id: int
    ) -> Dict[str, Any]:
        """Get term summary for a student."""
        entries = ScoreEntry.objects.filter(
            student_id=student_id,
            score_sheet__academic_session_id=session_id,
            score_sheet__academic_term_id=term_id,
            total_score__isnull=False
        ).select_related('score_sheet__subject')

        if not entries.exists():
            return {'total_subjects': 0, 'average': 0, 'total_score': 0}

        total = sum(e.total_score for e in entries)
        average = total / entries.count()

        grades = {}
        for entry in entries:
            if entry.grade:
                grades[entry.grade] = grades.get(entry.grade, 0) + 1

        best = entries.order_by('-total_score').first()
        worst = entries.order_by('total_score').first()

        return {
            'total_subjects': entries.count(),
            'total_score': total,
            'average': round(average, 2),
            'grades': grades,
            'best_subject': {
                'name': best.score_sheet.subject.name if best else None,
                'score': best.total_score if best else None,
            },
            'worst_subject': {
                'name': worst.score_sheet.subject.name if worst else None,
                'score': worst.total_score if worst else None,
            },
        }


class CumulativeSelector:
    """Cumulative record read operations"""

    @staticmethod
    def get_student_summary(
        student_id: int,
        session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get cumulative summary for a student."""
        queryset = CumulativeRecord.objects.filter(student_id=student_id)
        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)

        records = []
        for record in queryset.order_by('-academic_session'):
            records.append({
                'session': record.academic_session.name,
                'term1_average': record.term1_average,
                'term2_average': record.term2_average,
                'term3_average': record.term3_average,
                'session_average': record.session_average,
                'promoted': record.promoted_to_next_class,
            })

        return {
            'student_id': student_id,
            'records': records,
            'total_sessions': len(records),
        }
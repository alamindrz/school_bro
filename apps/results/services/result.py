"""
Result Service - Core score entry and promotion business logic
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, List, Dict, Any
import logging

from ..models import ScoreSheet, ScoreEntry, CumulativeRecord
from ..constants import GradeSystem

from apps.corecode.services import SystemLogService
from django.contrib.auth import get_user_model
User = get_user_model()
from apps.corecode.models import SystemLog
from apps.students.selectors import StudentSelector
from apps.corecode.selectors import AcademicSessionSelector, AcademicTermSelector

logger = logging.getLogger(__name__)


class ScoreSheetService:
    """Score sheet business operations"""

    @staticmethod
    @transaction.atomic
    def create_sheet(
        subject_id: int,
        class_id: int,
        session_id: int,
        term_id: int,
        created_by_id: Optional[int] = None
    ) -> ScoreSheet:
        """Create a score sheet for a subject + class + term."""
        sheet, created = ScoreSheet.objects.get_or_create(
            subject_id=subject_id,
            student_class_id=class_id,
            academic_session_id=session_id,
            academic_term_id=term_id,
            defaults={'created_by_id': created_by_id}
        )

        if created:
            logger.info(f"Score sheet created: {sheet}")
            # Auto-create empty entries for all students in the class
            ScoreSheetService._populate_students(sheet)

        return sheet

    @staticmethod
    def _populate_students(sheet: ScoreSheet):
        """Create empty ScoreEntry records for all students in the class."""
        students = StudentSelector.get_class_students(
            class_id=sheet.student_class_id,
            academic_session_id=sheet.academic_session_id
        )

        entries = []
        for student in students:
            entries.append(ScoreEntry(
                score_sheet=sheet,
                student_id=student['id'],
                student_name=student.get('full_name', student.get('name', 'Unknown'))
            ))

        ScoreEntry.objects.bulk_create(entries, ignore_conflicts=True)
        logger.info(f"Populated {len(entries)} students for sheet {sheet}")

    @staticmethod
    @transaction.atomic
    def update_score(
        entry_id: int,
        field: str,
        value: Optional[int],
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update a single score field on an entry.
        Auto-calculates total, grade, and position.
        Returns updated entry data for HTMX response.
        """
        try:
            entry = ScoreEntry.objects.select_related('score_sheet').get(id=entry_id)
        except ScoreEntry.DoesNotExist:
            raise ValidationError(f"Score entry {entry_id} not found")

        if not entry.score_sheet.is_editable:
            raise ValidationError("Score sheet is not editable")

        # Validate field name
        valid_fields = ['ca1', 'ca2', 'ca3', 'exam']
        if field not in valid_fields:
            raise ValidationError(f"Invalid field: {field}")

        # Validate value
        if value is not None and (value < 0 or value > 100):
            raise ValidationError(f"Score must be between 0 and 100")

        old_value = getattr(entry, field)
        setattr(entry, field, value)
        entry.entered_by_id = user_id

        # Check if all scores are filled
        all_filled = all(
            getattr(entry, f) is not None
            for f in valid_fields
        )

        if all_filled:
            entry.calculate_total()
            entry.determine_grade()
        else:
            entry.total_score = None
            entry.grade = None
            entry.position = None

        entry.save()

        # Recalculate positions if all scores filled
        if all_filled:
            ScoreSheetService._recalculate_positions(entry.score_sheet)

        # Log the change
        SystemLogService.log_action(
            user=User.objects.get(id=user_id) if user_id else None,
            action=SystemLog.ActionType.GRADE_CHANGE,
            app_label='results',
            model_name='ScoreEntry',
            object_id=str(entry.id),
            object_repr=f"{entry.student_name} - {entry.score_sheet.subject.name}",
            changes={
                'field': field,
                'old_value': old_value,
                'new_value': value,
            }
        )

        # Get updated position
        entry.refresh_from_db()

        return {
            'entry_id': entry.id,
            'field': field,
            'value': value,
            'total_score': entry.total_score,
            'grade': entry.grade,
            'position': entry.position,
            'all_filled': all_filled,
        }

    @staticmethod
    def _recalculate_positions(sheet: ScoreSheet):
        """Recalculate positions for all entries in a sheet."""
        # Only rank entries that have all scores filled
        entries = list(
            sheet.entries.filter(total_score__isnull=False).order_by('-total_score')
        )

        if not entries:
            return

        position = 1
        prev_total = None
        same_count = 0

        for i, entry in enumerate(entries):
            if prev_total is not None and entry.total_score == prev_total:
                same_count += 1
            else:
                position += same_count
                same_count = 0

            ScoreEntry.objects.filter(id=entry.id).update(position=position)
            prev_total = entry.total_score
            position += 0  # Will increment on next different score

        # Reset position for entries without all scores
        sheet.entries.filter(total_score__isnull=True).update(position=None)

    @staticmethod
    @transaction.atomic
    def submit_sheet(sheet_id: int, user_id: int) -> ScoreSheet:
        """Submit a score sheet for approval."""
        sheet = ScoreSheet.objects.get(id=sheet_id)
        if sheet.status != ScoreSheet.DRAFT:
            raise ValidationError("Only draft sheets can be submitted")

        sheet.status = ScoreSheet.SUBMITTED
        sheet.submitted_by_id = user_id
        sheet.submitted_at = timezone.now()
        sheet.save()

        logger.info(f"Score sheet submitted: {sheet}")
        return sheet

    @staticmethod
    @transaction.atomic
    def approve_sheet(sheet_id: int) -> ScoreSheet:
        """Approve a submitted score sheet."""
        sheet = ScoreSheet.objects.get(id=sheet_id)
        if sheet.status != ScoreSheet.SUBMITTED:
            raise ValidationError("Only submitted sheets can be approved")

        sheet.status = ScoreSheet.APPROVED
        sheet.save()
        return sheet

    @staticmethod
    @transaction.atomic
    def publish_sheet(sheet_id: int) -> ScoreSheet:
        """Publish an approved score sheet. Visible to parents."""
        sheet = ScoreSheet.objects.get(id=sheet_id)
        if sheet.status != ScoreSheet.APPROVED:
            raise ValidationError("Only approved sheets can be published")

        sheet.status = ScoreSheet.PUBLISHED
        sheet.save()
        return sheet


class PromotionService:
    """Student promotion calculations"""

    # Default promotion rules (configurable via SiteConfig later)
    MIN_PASS_SCORE = 40
    MIN_SUBJECTS_PASSED = 5
    MAX_FAILED_SUBJECTS = 3
    CORE_SUBJECTS = ['English Language', 'Mathematics']

    @classmethod
    def calculate_promotion(
        cls,
        student_id: int,
        session_id: int,
        term_id: int
    ) -> Dict[str, Any]:
        """
        Determine if a student qualifies for promotion.
        Checks: total subjects passed, core subjects, max failures.
        """
        # Get all score entries for this student in the current term
        entries = ScoreEntry.objects.filter(
            student_id=student_id,
            score_sheet__academic_session_id=session_id,
            score_sheet__academic_term_id=term_id,
            total_score__isnull=False  # Only entries with all scores filled
        ).select_related('score_sheet__subject')

        if not entries.exists():
            return {
                'eligible': False,
                'reason': 'No complete score entries found',
                'promoted': False,
            }

        total_subjects = entries.count()
        passed_subjects = entries.filter(total_score__gte=cls.MIN_PASS_SCORE).count()
        failed_subjects = total_subjects - passed_subjects

        # Check core subjects
        core_passed = True
        failed_core = []
        for core in cls.CORE_SUBJECTS:
            core_entry = entries.filter(
                score_sheet__subject__name__iexact=core
            ).first()
            if core_entry and core_entry.total_score < cls.MIN_PASS_SCORE:
                core_passed = False
                failed_core.append(core)

        # Apply rules
        if failed_subjects > cls.MAX_FAILED_SUBJECTS:
            return {
                'eligible': False,
                'reason': f'Failed {failed_subjects} subjects (max {cls.MAX_FAILED_SUBJECTS})',
                'total_subjects': total_subjects,
                'passed': passed_subjects,
                'failed': failed_subjects,
                'core_passed': core_passed,
                'failed_core': failed_core,
                'promoted': False,
            }

        if not core_passed:
            return {
                'eligible': False,
                'reason': f'Failed core subject(s): {", ".join(failed_core)}',
                'total_subjects': total_subjects,
                'passed': passed_subjects,
                'failed': failed_subjects,
                'core_passed': False,
                'failed_core': failed_core,
                'promoted': False,
            }

        if passed_subjects < cls.MIN_SUBJECTS_PASSED:
            return {
                'eligible': False,
                'reason': f'Passed only {passed_subjects} subjects (min {cls.MIN_SUBJECTS_PASSED})',
                'total_subjects': total_subjects,
                'passed': passed_subjects,
                'failed': failed_subjects,
                'core_passed': core_passed,
                'promoted': False,
            }

        # Promotion qualified
        return {
            'eligible': True,
            'reason': 'All promotion criteria met',
            'total_subjects': total_subjects,
            'passed': passed_subjects,
            'failed': failed_subjects,
            'core_passed': True,
            'failed_core': [],
            'promoted': True,
        }

    @classmethod
    @transaction.atomic
    def update_cumulative_record(
        cls,
        student_id: int,
        session_id: int,
        term_id: int
    ) -> CumulativeRecord:
        """Update or create cumulative record after term completion."""
        student = StudentSelector.get_by_id(student_id)
        if not student:
            raise ValidationError(f"Student {student_id} not found")

        # Get all entries for this term
        entries = ScoreEntry.objects.filter(
            student_id=student_id,
            score_sheet__academic_session_id=session_id,
            score_sheet__academic_term_id=term_id,
            total_score__isnull=False
        )

        if not entries.exists():
            logger.warning(f"No complete scores for student {student_id}")
            return None

        total = sum(e.total_score for e in entries)
        average = total / entries.count()

        # Get or create cumulative record
        record, _ = CumulativeRecord.objects.get_or_create(
            student_id=student_id,
            academic_session_id=session_id,
            defaults={'student_name': student.get('full_name', student.get('name', 'Unknown'))}
        )

        # Update term field based on term number
        if term_id == 1 or term_id == '1':
            record.term1_total = total
            record.term1_average = round(average, 2)
            # Get position from any entry (they share the same sheet positions are per-sheet)
            first_entry = entries.first()
            record.term1_position = first_entry.position if first_entry else None
        elif term_id == 2 or term_id == '2':
            record.term2_total = total
            record.term2_average = round(average, 2)
            first_entry = entries.first()
            record.term2_position = first_entry.position if first_entry else None
        elif term_id == 3 or term_id == '3':
            record.term3_total = total
            record.term3_average = round(average, 2)
            first_entry = entries.first()
            record.term3_position = first_entry.position if first_entry else None

        # Check promotion (only after Term 3)
        term_obj = AcademicTermSelector.get_by_id(int(term_id)) if term_id else None
        term_number = term_obj.get('term') if term_obj else int(term_id) if isinstance(term_id, int) else None
        
        if term_number == 3:
            promotion = PromotionService.calculate_promotion(
                student_id, session_id, term_id
            )
            record.promoted_to_next_class = promotion['promoted']

        record.calculate_session_average()
        record.save()

        logger.info(f"Cumulative record updated for student {student_id}")
        return record
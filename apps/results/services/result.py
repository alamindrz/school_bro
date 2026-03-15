"""
Result Service - Core result processing business logic
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, List, Dict, Any, Tuple
import logging

from ..models import (
    Subject, ResultSheet, ResultSheetSubject,
    Result, ResultComment, CumulativeRecord
)
from ..constants import ResultStatus, GradeSystem
from ..exceptions import (
    ResultSheetNotFoundError,
    ResultNotFoundError,
    DuplicateResultError,
    InvalidScoreError,
    ResultSheetClosedError,
    ResultSheetNotApprovedError,
    StudentNotEligibleError,
    SubjectNotFoundError,
    InvalidAssessmentWeightError,
)
from ..selectors import  ResultSheetSelector
from apps.corecode.selectors import SubjectSelector, AcademicSessionSelector

from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog
from apps.students.selectors import StudentSelector
from apps.finance.selectors import FinancialStatusSelector

logger = logging.getLogger(__name__)


class ResultService:
    """
    Result business operations
    Single source of truth for result management
    """

    @staticmethod
    @transaction.atomic
    def create_result_sheet(
        class_id: int,
        session_id: int,
        term_id: int,
        subject_ids: List[int],
        created_by_id: Optional[int] = None
    ) -> ResultSheet:
        """
        Create a result sheet for a class and term
        """
        # Check if sheet already exists
        existing = ResultSheet.objects.filter(
            student_class_id=class_id,
            academic_session_id=session_id,
            academic_term_id=term_id
        ).first()

        if existing:
            logger.info(f"Result sheet already exists for class {class_id}, term {term_id}")
            return existing

        # Create sheet
        sheet = ResultSheet.objects.create(
            student_class_id=class_id,
            academic_session_id=session_id,
            academic_term_id=term_id,
            status=ResultStatus.DRAFT,
            created_by_id=created_by_id
        )

        # Add subjects
        for subject_id in subject_ids:
            ResultSheetSubject.objects.create(
                result_sheet=sheet,
                subject_id=subject_id
            )

        logger.info(f"Result sheet created: {sheet.sheet_number}")
        return sheet

    @staticmethod
    @transaction.atomic
    def enter_result(
        sheet_id: int,
        student_id: int,
        subject_id: int,
        ca1_score: Optional[int] = None,
        ca2_score: Optional[int] = None,
        ca3_score: Optional[int] = None,
        exam_score: Optional[int] = None,
        practical_score: Optional[int] = None,
        project_score: Optional[int] = None,
        entered_by_id: Optional[int] = None
    ) -> Result:
        """
        Enter or update a result for a student
        """
        try:
            sheet = ResultSheet.objects.get(id=sheet_id)
        except ResultSheet.DoesNotExist:
            raise ResultSheetNotFoundError(f"Result sheet {sheet_id} not found")

        # Check if sheet can be edited
        if not sheet.can_edit():
            raise ResultSheetClosedError("Result sheet is closed for editing")

        # Validate student exists
        student = StudentSelector.get_by_id(student_id)
        if not student:
            raise StudentNotEligibleError(f"Student {student_id} not found")

        # Validate subject is in sheet
        if not sheet.subjects.filter(id=subject_id).exists():
            raise SubjectNotFoundError(f"Subject {subject_id} not in this result sheet")

        # Validate scores
        ResultService._validate_scores(
            ca1=ca1_score,
            ca2=ca2_score,
            ca3=ca3_score,
            exam=exam_score,
            practical=practical_score,
            project=project_score
        )

        # Check for existing result
        result, created = Result.objects.update_or_create(
            result_sheet=sheet,
            student_id=student_id,
            subject_id=subject_id,
            defaults={
                'student_name': student['full_name'],
                'ca1_score': ca1_score,
                'ca2_score': ca2_score,
                'ca3_score': ca3_score,
                'exam_score': exam_score,
                'practical_score': practical_score,
                'project_score': project_score,
                'entered_by_id': entered_by_id
            }
        )

        action = "CREATE" if created else "UPDATE"
        logger.info(f"Result {action}d for student {student_id}, subject {subject_id}")

        return result

    @staticmethod
    @transaction.atomic
    def submit_for_approval(
        sheet_id: int,
        submitted_by_id: int
    ) -> ResultSheet:
        """
        Submit result sheet for approval
        """
        try:
            sheet = ResultSheet.objects.get(id=sheet_id)
        except ResultSheet.DoesNotExist:
            raise ResultSheetNotFoundError(f"Result sheet {sheet_id} not found")

        if sheet.status != ResultStatus.DRAFT:
            raise ValidationError(f"Cannot submit sheet with status {sheet.status}")

        # Check if all results are entered
        total_students = sheet.results.values('student_id').distinct().count()
        expected_students = StudentSelector.get_class_students(
            class_id=sheet.student_class_id,
            academic_session_id=sheet.academic_session_id
        )

        if total_students < len(expected_students):
            raise ValidationError(
                f"Results entered for only {total_students} out of {len(expected_students)} students"
            )

        sheet.status = ResultStatus.PENDING_APPROVAL
        sheet.submitted_by_id = submitted_by_id
        sheet.submitted_at = timezone.now()
        sheet.save()

        logger.info(f"Result sheet {sheet.sheet_number} submitted for approval")
        return sheet

    @staticmethod
    @transaction.atomic
    def approve_sheet(
        sheet_id: int,
        approved_by_id: int
    ) -> ResultSheet:
        """
        Approve a result sheet
        """
        try:
            sheet = ResultSheet.objects.get(id=sheet_id)
        except ResultSheet.DoesNotExist:
            raise ResultSheetNotFoundError(f"Result sheet {sheet_id} not found")

        if not sheet.can_approve():
            raise ValidationError(f"Cannot approve sheet with status {sheet.status}")

        sheet.status = ResultStatus.APPROVED
        sheet.approved_by_id = approved_by_id
        sheet.approved_at = timezone.now()
        sheet.save()

        logger.info(f"Result sheet {sheet.sheet_number} approved")
        return sheet

    @staticmethod
    @transaction.atomic
    def publish_sheet(
        sheet_id: int,
        published_by_id: int
    ) -> ResultSheet:
        """
        Publish a result sheet (make available to parents)
        """
        try:
            sheet = ResultSheet.objects.get(id=sheet_id)
        except ResultSheet.DoesNotExist:
            raise ResultSheetNotFoundError(f"Result sheet {sheet_id} not found")

        if not sheet.can_publish():
            raise ResultSheetNotApprovedError("Sheet must be approved before publishing")

        # Check financial clearance if required
        from apps.corecode.services import SiteConfigService
        from apps.corecode.constants import SiteConfigKey

        require_clearance = SiteConfigService.get_config(
            SiteConfigKey.EXAM_CLEARANCE_REQUIRED,
            True
        )

        if require_clearance:
            # Get all students in this sheet
            student_ids = sheet.results.values_list('student_id', flat=True).distinct()

            not_cleared = []
            for student_id in student_ids:
                clearance = FinancialStatusSelector.is_student_cleared_for_exams(
                    student_id=student_id,
                    session_id=sheet.academic_session_id
                )
                if not clearance['is_cleared']:
                    student = StudentSelector.get_by_id(student_id)
                    not_cleared.append(student['full_name'] if student else f"Student {student_id}")

            if not_cleared:
                raise ValidationError(
                    f"Cannot publish: {len(not_cleared)} students not financially cleared: "
                    f"{', '.join(not_cleared[:5])}"
                )

        sheet.status = ResultStatus.PUBLISHED
        sheet.published_by_id = published_by_id
        sheet.published_at = timezone.now()
        sheet.save()

        # Calculate positions
        ResultService._calculate_positions(sheet)

        # Send notifications to parents
        ResultService._notify_parents(sheet)

        logger.info(f"Result sheet {sheet.sheet_number} published")
        return sheet

    @staticmethod
    def _validate_scores(**scores):
        """Validate all scores are within range"""
        from ..validators import ResultValidator
        ResultValidator.validate_scores(**scores)

    @staticmethod
    def _calculate_positions(sheet: ResultSheet):
        """
        Calculate student positions based on total scores
        """
        # Group results by student
        from django.db.models import Sum

        student_totals = sheet.results.values('student_id').annotate(
            total=Sum('total_score'),
            name=Max('student_name')
        ).order_by('-total')

        position = 1
        prev_total = None
        same_position_count = 0

        for student in student_totals:
            # Handle ties
            if prev_total is not None and student['total'] == prev_total:
                same_position_count += 1
            else:
                position += same_position_count
                same_position_count = 0

            # Update all results for this student with position
            Result.objects.filter(
                result_sheet=sheet,
                student_id=student['student_id']
            ).update(position=position)

            prev_total = student['total']

    @staticmethod
    def _notify_parents(sheet: ResultSheet):
        """
        Send notifications to parents about published results
        """
        from apps.parents.services import NotificationService
        from apps.parents.selectors import ChildLinkSelector

        student_ids = sheet.results.values_list('student_id', flat=True).distinct()

        for student_id in student_ids:
            parents = ChildLinkSelector.get_for_student(student_id)

            for parent in parents:
                try:
                    NotificationService.send_results_published(
                        parent_id=parent['parent_id'],
                        student_id=student_id,
                        term=sheet.academic_term.get_term_display(),
                        session=sheet.academic_session.name
                    )
                except Exception as e:
                    logger.error(f"Failed to notify parent {parent['parent_id']}: {e}")

    @staticmethod
    @transaction.atomic
    def add_comment(
        sheet_id: int,
        student_id: int,
        teacher_comment: str = "",
        class_teacher_comment: str = "",
        principal_comment: str = "",
        next_term_recommendation: str = "",
        created_by_id: Optional[int] = None
    ) -> ResultComment:
        """
        Add or update comments for a student
        """
        try:
            sheet = ResultSheet.objects.get(id=sheet_id)
        except ResultSheet.DoesNotExist:
            raise ResultSheetNotFoundError(f"Result sheet {sheet_id} not found")

        student = StudentSelector.get_by_id(student_id)
        if not student:
            raise StudentNotEligibleError(f"Student {student_id} not found")

        comment, created = ResultComment.objects.update_or_create(
            result_sheet=sheet,
            student_id=student_id,
            defaults={
                'student_name': student['full_name'],
                'teacher_comment': teacher_comment,
                'class_teacher_comment': class_teacher_comment,
                'principal_comment': principal_comment,
                'next_term_recommendation': next_term_recommendation,
                'created_by_id': created_by_id
            }
        )

        logger.info(f"Comment {'created' if created else 'updated'} for student {student_id}")
        return comment

    @staticmethod
    def update_cumulative_record(
        student_id: int,
        session_id: int
    ) -> CumulativeRecord:
        """
        Update cumulative record for a student after term completion
        """
        # Get all term results for this student in this session
        sheets = ResultSheet.objects.filter(
            academic_session_id=session_id,
            results__student_id=student_id,
            status=ResultStatus.PUBLISHED
        ).distinct().order_by('academic_term__term')

        if not sheets.exists():
            logger.warning(f"No published results for student {student_id} in session {session_id}")
            return None

        # Get or create cumulative record
        record, _ = CumulativeRecord.objects.get_or_create(
            student_id=student_id,
            academic_session_id=session_id,
            defaults={'student_name': StudentSelector.get_by_id(student_id)['full_name']}
        )

        # Update term data
        for sheet in sheets:
            term = sheet.academic_term.term
            summary = ResultSelector.get_term_summary(student_id, sheet.id)

            if term == 1:
                record.term1_average = summary.get('average')
                record.term1_position = Result.objects.filter(
                    result_sheet=sheet,
                    position=1
                ).exists() and Result.objects.filter(
                    result_sheet=sheet,
                    student_id=student_id
                ).first().position
            elif term == 2:
                record.term2_average = summary.get('average')
                record.term2_position = Result.objects.filter(
                    result_sheet=sheet,
                    position=1
                ).exists() and Result.objects.filter(
                    result_sheet=sheet,
                    student_id=student_id
                ).first().position
            elif term == 3:
                record.term3_average = summary.get('average')
                record.term3_position = Result.objects.filter(
                    result_sheet=sheet,
                    position=1
                ).exists() and Result.objects.filter(
                    result_sheet=sheet,
                    student_id=student_id
                ).first().position

        # Calculate session average
        record.calculate_session_average()
        record.save()

        logger.info(f"Cumulative record updated for student {student_id}")
        return record
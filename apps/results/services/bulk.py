"""
Bulk Result Service - CSV import and bulk operations
"""

import csv
import io
from typing import List, Dict, Any, Tuple, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
import logging

# from ..models import ScoreSheet, Result  # OLD MODEL
from ..services import ScoreSheetService
from ..exceptions import BulkOperationError
from ..validators import BulkResultValidator

from apps.students.selectors import StudentSelector

logger = logging.getLogger(__name__)


class BulkResultService:
    """
    Bulk result operations (CSV import, mass updates)
    """

    REQUIRED_CSV_FIELDS = ['student_id', 'subject_code']
    OPTIONAL_CSV_FIELDS = ['ca1', 'ca2', 'ca3', 'exam', 'practical', 'project']

    @classmethod
    @transaction.atomic
    def import_from_csv(
        cls,
        csv_file,
        sheet_id: int,
        entered_by_id: Optional[int] = None,
        batch_size: int = 100
    ) -> Tuple[List[Result], List[Dict[str, Any]]]:
        """
        Import results from CSV file
        """
        try:
            sheet = ScoreSheet.objects.get(id=sheet_id)
        except ScoreSheet.DoesNotExist:
            raise BulkOperationError(f"Result sheet {sheet_id} not found")

        if not sheet.can_edit():
            raise BulkOperationError("Cannot import to closed result sheet")

        # Validate batch size
        BulkResultValidator.validate_batch_size(batch_size)

        successful = []
        failed = []

        try:
            decoded_file = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            # Validate headers
            headers = reader.fieldnames or []
            BulkResultValidator.validate_csv_headers(headers, cls.REQUIRED_CSV_FIELDS)

            # Process in batches
            batch = []
            for row_num, row in enumerate(reader, start=2):
                batch.append((row_num, row))

                if len(batch) >= batch_size:
                    batch_success, batch_failed = cls._process_batch(
                        batch, sheet, entered_by_id
                    )
                    successful.extend(batch_success)
                    failed.extend(batch_failed)
                    batch = []

            # Process remaining records
            if batch:
                batch_success, batch_failed = cls._process_batch(
                    batch, sheet, entered_by_id
                )
                successful.extend(batch_success)
                failed.extend(batch_failed)

        except Exception as e:
            raise BulkOperationError(f"CSV import failed: {str(e)}")

        logger.info(
            f"CSV import completed: {len(successful)} successful, {len(failed)} failed"
        )

        return successful, failed

    @classmethod
    def _process_batch(
        cls,
        batch: List[Tuple[int, Dict]],
        sheet: ScoreSheet,
        entered_by_id: Optional[int]
    ) -> Tuple[List[Result], List[Dict[str, Any]]]:
        """Process a batch of CSV records"""
        successful = []
        failed = []

        for row_num, row in batch:
            try:
                student_id = int(row.get('student_id'))
                subject_code = row.get('subject_code')

                # Get subject by code
                from ..selectors import SubjectSelector
                subject = SubjectSelector.get_by_code(subject_code)
                if not subject:
                    raise ValidationError(f"Subject code '{subject_code}' not found")

                # Parse scores
                ca1 = cls._parse_score(row.get('ca1'))
                ca2 = cls._parse_score(row.get('ca2'))
                ca3 = cls._parse_score(row.get('ca3'))
                exam = cls._parse_score(row.get('exam'))
                practical = cls._parse_score(row.get('practical'))
                project = cls._parse_score(row.get('project'))

                # Enter result
                result = ScoreSheetService.enter_result(
                    sheet_id=sheet.id,
                    student_id=student_id,
                    subject_id=subject['id'],
                    ca1_score=ca1,
                    ca2_score=ca2,
                    ca3_score=ca3,
                    exam_score=exam,
                    practical_score=practical,
                    project_score=project,
                    entered_by_id=entered_by_id
                )
                successful.append(result)

            except Exception as e:
                failed.append({
                    'row': row_num,
                    'data': row,
                    'error': str(e)
                })

        return successful, failed

    @classmethod
    def _parse_score(cls, value: str) -> Optional[int]:
        """Parse score from string, return None if empty"""
        if not value or value.strip() == '':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid score value: {value}")

    @classmethod
    def generate_csv_template(cls, sheet_id: int) -> str:
        """
        Generate CSV template for a result sheet
        """
        from ..selectors import ScoreSheetSelector

        sheet = ScoreSheetSelector.get_by_id(sheet_id)
        if not sheet:
            raise BulkOperationError(f"Result sheet {sheet_id} not found")

        output = io.StringIO()
        writer = csv.writer(output)

        # Write headers
        headers = cls.REQUIRED_CSV_FIELDS + cls.OPTIONAL_CSV_FIELDS
        writer.writerow(headers)

        # Get students in this class
        from apps.students.selectors import StudentSelector
        students = StudentSelector.get_class_students(
            class_id=sheet['student_class']['id'],
            academic_session_id=sheet['academic_session']['id']
        )

        # Get subjects in this sheet
        subjects = sheet['subjects']

        # Write example rows (first 3 students with first subject)
        for student in students[:3]:
            if subjects:
                writer.writerow([
                    student['id'],
                    subjects[0]['code'],
                    '80', '75', '70', '65', '60', '55'
                ])

        return output.getvalue()

    @classmethod
    @transaction.atomic
    def copy_from_previous_term(
        cls,
        target_sheet_id: int,
        source_sheet_id: int,
        copied_by_id: Optional[int] = None
    ) -> Tuple[List[Result], List[Dict[str, Any]]]:
        """
        Copy results from previous term's result sheet
        """
        try:
            target_sheet = ScoreSheet.objects.get(id=target_sheet_id)
            source_sheet = ScoreSheet.objects.get(id=source_sheet_id)
        except ScoreSheet.DoesNotExist as e:
            raise BulkOperationError(str(e))

        if not target_sheet.can_edit():
            raise BulkOperationError("Cannot copy to closed result sheet")

        # Get source results
        source_results = Result.objects.filter(result_sheet=source_sheet)

        successful = []
        failed = []

        for source in source_results:
            try:
                # Check if subject exists in target sheet
                if not target_sheet.subjects.filter(id=source.subject_id).exists():
                    failed.append({
                        'student_id': source.student_id,
                        'subject': source.subject.name,
                        'error': 'Subject not in target sheet'
                    })
                    continue

                result = ScoreSheetService.enter_result(
                    sheet_id=target_sheet_id,
                    student_id=source.student_id,
                    subject_id=source.subject_id,
                    ca1_score=source.ca1_score,
                    ca2_score=source.ca2_score,
                    ca3_score=source.ca3_score,
                    exam_score=source.exam_score,
                    practical_score=source.practical_score,
                    project_score=source.project_score,
                    entered_by_id=copied_by_id
                )
                successful.append(result)

            except Exception as e:
                failed.append({
                    'student_id': source.student_id,
                    'subject': source.subject.name,
                    'error': str(e)
                })

        logger.info(
            f"Copied {len(successful)} results from sheet {source_sheet_id} "
            f"to {target_sheet_id}"
        )

        return successful, failed
"""
API endpoints for results app (AJAX/HTMX)
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
import json
import logging

from ..models import Subject, ResultSheet, Result
from ..selectors import (
  ResultSheetSelector, ResultSelector,
    CumulativeSelector
)
from apps.corecode.selectors import SubjectSelector
from ..services import ResultService, ReportService

logger = logging.getLogger(__name__)


@login_required
@permission_required('results.view_subject')
@require_http_methods(["GET"])
def search_subjects(request):
    """Search subjects via AJAX"""
    query = request.GET.get('q', '')
    subjects = SubjectSelector.list_subjects(search=query, limit=10)

    return JsonResponse({'subjects': subjects})


@login_required
@permission_required('results.view_resultsheet')
@require_http_methods(["GET"])
def get_sheet_status(request, sheet_id):
    """Get result sheet status"""
    sheet = get_object_or_404(ResultSheet, id=sheet_id)

    return JsonResponse({
        'id': sheet.id,
        'status': sheet.status,
        'status_display': sheet.get_status_display(),
        'can_edit': sheet.can_edit(),
        'can_approve': sheet.can_approve(),
        'can_publish': sheet.can_publish(),
        'result_count': sheet.results.count(),
        'student_count': sheet.results.values('student_id').distinct().count(),
    })


@login_required
@permission_required('results.view_result')
@require_http_methods(["GET"])
def get_student_results(request, student_id):
    """Get student results summary"""
    session_id = request.GET.get('session_id')
    term_id = request.GET.get('term_id')

    results = ResultSelector.get_student_results(
        student_id=student_id,
        session_id=session_id,
        term_id=term_id
    )

    return JsonResponse({'results': results})


@login_required
@permission_required('results.view_result')
@require_http_methods(["GET"])
def check_clearance(request, student_id):
    """Check if student is cleared for results"""
    from apps.finance.selectors import FinancialStatusSelector

    session_id = request.GET.get('session_id')
    clearance = FinancialStatusSelector.is_student_cleared_for_exams(
        student_id=student_id,
        session_id=session_id
    )

    return JsonResponse(clearance)


@login_required
@permission_required('results.change_result')
@require_http_methods(["POST"])
def update_result_ajax(request):
    """Update a result via AJAX"""
    try:
        data = json.loads(request.body)
        result_id = data.get('result_id')
        field = data.get('field')
        value = data.get('value')

        result = get_object_or_404(Result, id=result_id)

        if field == 'ca1':
            result.ca1_score = int(value) if value else None
        elif field == 'ca2':
            result.ca2_score = int(value) if value else None
        elif field == 'ca3':
            result.ca3_score = int(value) if value else None
        elif field == 'exam':
            result.exam_score = int(value) if value else None
        elif field == 'practical':
            result.practical_score = int(value) if value else None
        elif field == 'project':
            result.project_score = int(value) if value else None

        result.save()  # Triggers recalculation

        return JsonResponse({
            'success': True,
            'total': result.total_score,
            'grade': result.grade,
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permission_required('results.view_cumulative')
@require_http_methods(["GET"])
def get_cumulative_chart(request, student_id):
    """Get cumulative data for charts"""
    trends = ReportService.generate_performance_trends(student_id)

    chart_data = {
        'labels': [t['session'] for t in trends['trends']],
        'term1': [t['term1_average'] or 0 for t in trends['trends']],
        'term2': [t['term2_average'] or 0 for t in trends['trends']],
        'term3': [t['term3_average'] or 0 for t in trends['trends']],
        'average': [t['session_average'] or 0 for t in trends['trends']],
    }

    return JsonResponse(chart_data)


@login_required
@permission_required('results.view_resultsheet')
@require_http_methods(["GET"])
def get_grade_distribution(request, sheet_id):
    """Get grade distribution for charts"""
    report = ReportService.generate_term_report(sheet_id)

    if 'grade_distribution' in report:
        return JsonResponse(report['grade_distribution'])

    return JsonResponse({})


@login_required
@permission_required('results.view_resultsheet')
@require_http_methods(["GET"])
def download_template(request, sheet_id):
    """Download CSV template for bulk upload"""
    from django.http import HttpResponse

    csv_content = BulkResultService.generate_csv_template(sheet_id)

    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="result_template_{sheet_id}.csv"'

    return response
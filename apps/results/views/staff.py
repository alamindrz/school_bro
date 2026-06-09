"""
Staff views for results management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
import logging

from ..models import ScoreSheet
from ..selectors import ScoreSheetSelector, ScoreEntrySelector, CumulativeSelector
from ..services.result import ScoreSheetService, PromotionService

from apps.corecode.selectors import (
    StudentClassSelector, AcademicSessionSelector, AcademicTermSelector, SubjectSelector
)
from apps.students.selectors import StudentSelector

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Results dashboard"""
    template_name = 'results/pages/dashboard.html'
    permission_required = 'results.view_result'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_session = AcademicSessionSelector.get_current_session()
        current_term = AcademicTermSelector.get_current_term()

        context['classes'] = StudentClassSelector.get_all_classes(active_only=True)
        context['current_session'] = current_session
        context['current_term'] = current_term

        if current_session and current_term:
            context['recent_sheets'] = ScoreSheetSelector.list_sheets(
                session_id=current_session.id,
                term_id=current_term.id,
                limit=20
            )

        return context


class SheetEntryView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'results/pages/sheet_entry.html'
    permission_required = 'results.add_result'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        class_id = self.request.GET.get('class_id')
        try:
            class_id = int(class_id) if class_id else None
        except (ValueError, TypeError):
            class_id = None
        subject_id = self.request.GET.get('subject_id')
        try:
            subject_id = int(subject_id) if subject_id else None
        except (ValueError, TypeError):
            subject_id = None
        
        current_session = AcademicSessionSelector.get_current_session()
        current_term = AcademicTermSelector.get_current_term()
        session_id = current_session.id if current_session else None
        term_id = current_term.id if current_term else None

        # Get or create sheet
        if class_id and subject_id and session_id and term_id:
            sheet = ScoreSheetSelector.get_or_create_sheet(
                subject_id=int(subject_id),
                class_id=int(class_id),
                session_id=int(session_id),
                term_id=int(term_id)
            )
            context['sheet'] = sheet

        context['classes'] = StudentClassSelector.get_all_classes(active_only=True)
        
        # Filter subjects by teacher
        user = self.request.user
        if user.is_superuser or not hasattr(user, 'staff_profile'):
            context['subjects'] = SubjectSelector.list_subjects(active_only=True)
        else:
            from apps.staffs.selectors import TeacherQualificationSelector
            quals = TeacherQualificationSelector.get_for_teacher(user.staff_profile.id)
            qualified_ids = [q['subject_id'] for q in quals]
            all_subjects = SubjectSelector.list_subjects(active_only=True)
            context['subjects'] = [s for s in all_subjects if s['id'] in qualified_ids]

        context['current_session'] = current_session
        context['current_term'] = current_term
        context['selected_class'] = class_id or ''
        context['selected_subject'] = subject_id or ''

        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        # If HTMX request, return only the sheet partial
        if request.headers.get('HX-Request'):
            if context.get('sheet'):
                return render(request, 'results/partials/sheet_table.html', context)
            return HttpResponse('<div class="text-center text-gray-500 py-12">Select a class and subject.</div>')
        
        return self.render_to_response(context)


class SheetDetailView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """View-only score sheet."""
    template_name = 'results/pages/sheet_detail.html'
    permission_required = 'results.view_result'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sheet_id = self.kwargs.get('pk')
        context['sheet'] = ScoreSheetSelector.get_by_id(sheet_id)
        return context


class ScoreUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    HTMX endpoint: Update a single score field on blur.
    Returns updated row data as JSON.
    """
    permission_required = 'results.change_result'

    def post(self, request, *args, **kwargs):
        logger.debug(f"RAW POST: {request.POST}")
        logger.debug(f"BODY: {request.body}")
        try:
            entry_id = request.POST.get('entry_id')
            field = request.POST.get('field')
            value = request.POST.get('value')

            if not entry_id or not field:
                return JsonResponse({'success': False, 'error': 'Missing entry_id or field'}, status=400)

            try:
                value = int(value) if value and value.strip() else None
            except (ValueError, TypeError):
                return JsonResponse({'success': False, 'error': 'Invalid score value'}, status=400)

            if value is not None and (value < 0 or value > 100):
                return JsonResponse({'success': False, 'error': 'Score must be between 0 and 100'}, status=400)

            result = ScoreSheetService.update_score(
                entry_id=int(entry_id),
                field=field,
                value=value,
                user_id=request.user.id
            )

            return JsonResponse({
                'success': True,
                'total_score': result['total_score'],
                'grade': result['grade'],
                'position': result['position'],
                'all_filled': result['all_filled'],
            })

        except Exception as e:
            logger.error(f"Score update failed: {e}", exc_info=True)
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

class SubmitSheetView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Submit a score sheet for approval."""
    permission_required = 'results.change_resultsheet'

    def post(self, request, pk):
        try:
            ScoreSheetService.submit_sheet(sheet_id=pk, user_id=request.user.id)
            messages.success(request, 'Sheet submitted for approval.')
        except Exception as e:
            logger.error(f"Sheet submission failed for sheet {pk}: {e}", exc_info=True)
            messages.error(request, str(e))
        return redirect('results:sheet_detail', pk=pk)


class PublishSheetView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Publish a score sheet."""
    permission_required = 'results.publish_resultsheet'

    def post(self, request, pk):
        try:
            ScoreSheetService.publish_sheet(sheet_id=pk)
            messages.success(request, 'Sheet published.')
        except Exception as e:
            logger.error(f"Sheet publishing failed for sheet {pk}: {e}", exc_info=True)
            messages.error(request, str(e))
        return redirect('results:sheet_detail', pk=pk)


class ClassResultView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """View all subject results for a class in a term."""
    template_name = 'results/pages/class_result.html'
    permission_required = 'results.view_result'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_id = self.request.GET.get('class_id')
        try:
            class_id = int(class_id) if class_id else None
        except (ValueError, TypeError):
            class_id = None
        session_id = self.request.GET.get('session_id')
        term_id = self.request.GET.get('term_id')

        current_session = AcademicSessionSelector.get_current_session()
        current_term = AcademicTermSelector.get_current_term()

        if not session_id and current_session:
            session_id = current_session.id
        if not term_id and current_term:
            term_id = current_term.id

        if class_id and session_id and term_id:
            sheets = ScoreSheetSelector.list_sheets(
                class_id=int(class_id),
                session_id=int(session_id),
                term_id=int(term_id)
            )
            context['sheets'] = sheets

            # Build student result matrix
            all_entries = ScoreEntry.objects.filter(
                score_sheet__student_class_id=class_id,
                score_sheet__academic_session_id=session_id,
                score_sheet__academic_term_id=term_id,
                total_score__isnull=False
            ).select_related('score_sheet__subject')

            students_dict = {}
            for entry in all_entries:
                if entry.student_id not in students_dict:
                    students_dict[entry.student_id] = {
                        'id': entry.student_id,
                        'name': entry.student_name,
                        'subjects': {},
                        'total': 0,
                        'average': 0,
                    }
                students_dict[entry.student_id]['subjects'][entry.score_sheet.subject.name] = {
                    'total': entry.total_score,
                    'grade': entry.grade,
                    'position': entry.position,
                }

            # Calculate totals and averages
            for student in students_dict.values():
                scores = [s['total'] for s in student['subjects'].values() if s['total']]
                student['total'] = sum(scores)
                student['average'] = round(sum(scores) / len(scores), 2) if scores else 0

            # Sort by average descending
            student_list = sorted(students_dict.values(), key=lambda x: x['average'], reverse=True)

            # Assign positions
            for i, student in enumerate(student_list):
                student['position'] = i + 1

            context['students'] = student_list
            context['subjects'] = [s['subject_name'] for s in sheets]

        context['classes'] = StudentClassSelector.get_all_classes(active_only=True)
        context['selected_class'] = class_id or ''

        return context
"""
HTMX Fragment Views - Return HTML partials for HTMX requests
All views return HTML fragments with proper logging and user feedback.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views import View
from django.shortcuts import render
from django.http import HttpResponse
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import json
import logging

from ..models import TimetableSlot, SchoolDay, TimetablePeriod
from ..services import ClashDetectionService, TimetableService
from ..services.recommendation import TimetableRecommendationService
from ..selectors import (
    TimetableSelector,
    TimetableSlotSelector,
    TeacherQualificationSelector,
    SchoolDaySelector,
    TimetablePeriodSelector,
    TimetableStatsSelector,
)
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class SlotEditFormView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    GET: Return slot edit modal HTML fragment.
    
    Loads the edit form for a timetable slot, including:
    - All active academic staff
    - Current slot data (if editing)
    - Teacher's qualified subjects (if teacher already assigned)
    """
    permission_required = 'timetable.change_timetable'
    
    def get(self, request, slot_id):
        logger.info(f"Loading slot edit form for slot_id={slot_id}, user={request.user}")
        
        slot = None
        if slot_id and slot_id != 0:
            slot = TimetableSlotSelector.get_by_id_model(slot_id)
            logger.debug(f"Found existing slot: {slot}")
        
        day_id = request.GET.get('day')
        period_id = request.GET.get('period')
        timetable_id = request.GET.get('timetable_id')
        
        if slot:
            day_id = slot.day_id
            period_id = slot.period_id
            timetable_id = slot.timetable_id
        
        day = None
        if day_id:
            try:
                day = SchoolDay.objects.get(id=int(day_id))
            except SchoolDay.DoesNotExist:
                logger.warning(f"SchoolDay id={day_id} not found")
        
        period = None
        if period_id:
            try:
                period = TimetablePeriod.objects.get(id=int(period_id))
            except TimetablePeriod.DoesNotExist:
                logger.warning(f"TimetablePeriod id={period_id} not found")
        
        # Get all active academic staff
        from apps.staffs.models import Staff
        teachers = Staff.objects.filter(
            employment_status='active',
            staff_category='academic'
        ).order_by('first_name', 'last_name')
        logger.debug(f"Found {teachers.count()} active academic staff")
        
        # If editing an existing slot with a teacher, get their qualified subjects
        subjects = []
        qualifications = []
        
        if slot and slot.teacher:
            from apps.staffs.selectors import TeacherQualificationSelector
            qualifications = TeacherQualificationSelector.get_for_teacher(int(slot.teacher_id))
            subjects = [{'id': q['subject_id'], 'name': q['subject_name']} for q in qualifications]
            logger.debug(f"Pre-loaded {len(subjects)} subjects for teacher {slot.teacher.get_full_name}")
        
        context = {
            'slot': slot,
            'slot_id': slot_id if slot_id != 0 else 0,
            'day': day,
            'period': period,
            'timetable_id': timetable_id,
            'selected_teacher': slot.teacher_id if slot else None,
            'selected_subject': slot.subject_id if slot else None,
            'room': slot.room if slot else '',
            'is_free_period': slot.is_free_period if slot else False,
            'teachers': teachers,
            'subjects': subjects,
        }
        
        return render(request, 'timetable/htmx/slot_edit_modal.html', context)




class TeacherSubjectsSelectView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'timetable.change_timetableslot'

    def get(self, request):
        teacher_id = request.GET.get('teacher_id')
        slot_id = request.GET.get('slot_id')
        
        # Fallback to URL query parameter if slot attribute is empty
        timetable_id = request.GET.get('timetable_id')
        day_id = request.GET.get('day_id')
        period_id = request.GET.get('period_id')
        room = request.GET.get('room', '')

        # If slot_id is 0 or missing, we need to ensure timetable_id, day_id, period_id are still passed to context
        # These are crucial for the hx-target in subject_select.html when a new slot is being created
        if slot_id and slot_id != '0':
            try:
                slot = TimetableSlot.objects.get(id=slot_id)
                # If a slot exists, prefer its timetable_id, day_id, period_id
                timetable_id = slot.timetable.id if slot.timetable else timetable_id
                day_id = slot.day.id if slot.day else day_id
                period_id = slot.period.id if slot.period else period_id
            except TimetableSlot.DoesNotExist:
                logger.warning(f"Slot with ID {slot_id} not found when fetching subjects.")
        
        subjects = []
        if teacher_id and teacher_id != 'undefined':
            try:
                teacher_pk = int(teacher_id)
                subjects = TeacherQualificationSelector.get_for_teacher(teacher_pk)
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid teacher_id {teacher_id}: {e}")
                pass

        context = {
            'subjects': subjects,
            'slot_id': slot_id if slot_id != '0' else 0, # Ensure slot_id is 0 if it's a new slot
            'teacher_id': teacher_id,
            'timetable_id': timetable_id,
            'day_id': day_id,
            'period_id': period_id,
            'room': room,
        }
        return render(request, 'timetable/htmx/subject_select.html', context)



@method_decorator(require_http_methods(["POST"]), name='dispatch')
class SlotUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """POST: Update a timetable slot with teacher/subject assignment."""
    permission_required = 'timetable.change_timetable'
    
    def post(self, request, slot_id):
        print("\n" + "="*50)
        print(f"🔴 SlotUpdateView.post() CALLED")
        print(f"🔴 slot_id: {slot_id}")
        print(f"🔴 POST data: {dict(request.POST)}")
        print(f"🔴 HX-Request header: {request.headers.get('HX-Request')}")
        print("="*50 + "\n")
        
        logger.info(f"SlotUpdateView called: slot_id={slot_id}, user={request.user}")
        
        # Validate with form
        from ..forms import TimetableSlotUpdateForm
        form = TimetableSlotUpdateForm(request.POST)
        
        if not form.is_valid():
            logger.warning(f"Form validation failed: {form.errors}")
            response = HttpResponse(status=400)
            response['HX-Trigger'] = json.dumps({
                'showToast': {
                    'message': f"❌ {list(form.errors.values())[0][0]}",
                    'type': 'error'
                }
            })
            return response
        
        cleaned = form.cleaned_data
        
        # Handle slot_id = 0
        if slot_id == 0 or slot_id == '0':
            logger.error("slot_id is 0, cannot update")
            return HttpResponse('<div class="text-red-500 p-4">Invalid slot ID</div>', status=400)
        
        # Get the slot
        slot = TimetableSlotSelector.get_by_id_model(int(slot_id))
        if not slot:
            logger.error(f"Slot {slot_id} not found")
            return HttpResponse('<div class="text-red-500 p-4">Slot not found</div>', status=404)
        
        teacher_id = cleaned.get('teacher_id')
        subject_id = cleaned.get('subject_id')
        room = cleaned.get('room', '')
        is_free_period = cleaned.get('is_free_period', False)

        logger.debug(f"Parsed data - teacher_id: {teacher_id}, subject_id: {subject_id}, room: '{room}', is_free_period: {is_free_period}")
        
        # Handle free period
        if is_free_period:
            logger.info(f"Setting slot {slot_id} as free period")
            with transaction.atomic():
                old_teacher = slot.teacher.get_full_name if slot.teacher else None
                
                slot.teacher = None
                slot.subject = None
                slot.is_free_period = True
                slot.room = ''
                slot.updated_at = timezone.now()
                slot.save()
                
                # Audit log
                SystemLogService.log_action(
                    user=request.user,
                    action=SystemLog.ActionType.UPDATE,
                    app_label='timetable',
                    model_name='TimetableSlot',
                    object_id=str(slot.id),
                    object_repr=f"{slot.day.name} {slot.period.display_name}",
                    changes={
                        'action': 'set_free_period',
                        'previous_teacher': old_teacher,
                    },
                    request=request
                )
                logger.info(f"Free period set successfully, was: {old_teacher}")
        
        # Handle teacher assignment
        elif teacher_id:
            logger.info(f"Assigning teacher {teacher_id} to slot {slot_id}")
            
            # Validate teacher exists
            from apps.staffs.models import Staff
            try:
                teacher = Staff.objects.get(id=int(teacher_id))
                logger.debug(f"Teacher found: {teacher.get_full_name}")
            except Staff.DoesNotExist:
                logger.error(f"Teacher {teacher_id} not found")
                return HttpResponse(
                    '<div class="text-red-500 p-4 text-center">Teacher not found</div>',
                    status=400
                )
            
            # Validate subject if provided
            subject = None
            if subject_id:
                from apps.corecode.models import Subject
                try:
                    subject = Subject.objects.get(id=int(subject_id))
                    logger.debug(f"Subject found: {subject.name}")
                except Subject.DoesNotExist:
                    logger.error(f"Subject {subject_id} not found")
                    return HttpResponse(
                        '<div class="text-red-500 p-4 text-center">Subject not found</div>',
                        status=400
                    )
            
            # Check for teacher clash
            logger.debug("Checking for teacher clash...")
            has_clash, clash_details = ClashDetectionService.check_teacher_clash(
                timetable_id=slot.timetable_id,
                teacher_id=int(teacher_id),
                day_id=slot.day_id,
                period_id=slot.period_id,
                exclude_slot_id=slot.id
            )
            
            if has_clash:
                logger.warning(f"Clash detected: {clash_details}")
                response = HttpResponse(status=409)
                response['HX-Trigger'] = json.dumps({
                    'showToast': {
                        'message': f"⚠️ {teacher.get_full_name} is already assigned to {clash_details['class_name']} at this time.",
                        'type': 'warning'
                    }
                })
                return response
            
            logger.info("No clash detected, saving assignment")
            
            # Save the assignment
            with transaction.atomic():
                old_teacher = slot.teacher.get_full_name if slot.teacher else 'None'
                old_subject = slot.subject.name if slot.subject else 'None'
                
                slot.teacher = teacher
                slot.subject = subject
                slot.is_free_period = False
                slot.room = room
                slot.updated_at = timezone.now()
                slot.save()
                
                # Audit log
                SystemLogService.log_action(
                    user=request.user,
                    action=SystemLog.ActionType.UPDATE,
                    app_label='timetable',
                    model_name='TimetableSlot',
                    object_id=str(slot.id),
                    object_repr=f"{slot.day.name} {slot.period.display_name}",
                    changes={
                        'action': 'assigned',
                        'teacher': teacher.get_full_name,
                        'subject': subject.name if subject else 'None',
                        'room': room,
                        'previous_teacher': old_teacher,
                        'previous_subject': old_subject,
                    },
                    request=request
                )
                logger.info(f"Assignment saved: {teacher.get_full_name} -> {subject.name if subject else 'No subject'}")
        
        # Handle clear (no teacher, not free period)
        else:
            logger.info(f"Clearing slot {slot_id}")
            with transaction.atomic():
                old_teacher = slot.teacher.get_full_name if slot.teacher else None
                
                slot.teacher = None
                slot.subject = None
                slot.is_free_period = False
                slot.room = ''
                slot.updated_at = timezone.now()
                slot.save()
                
                # Audit log
                SystemLogService.log_action(
                    user=request.user,
                    action=SystemLog.ActionType.UPDATE,
                    app_label='timetable',
                    model_name='TimetableSlot',
                    object_id=str(slot.id),
                    object_repr=f"{slot.day.name} {slot.period.display_name}",
                    changes={
                        'action': 'cleared',
                        'previous_teacher': old_teacher,
                    },
                    request=request
                )
                logger.info(f"Slot cleared, was: {old_teacher}")
        
        # Prepare response with updated cell
        context = {
            'slot': slot,
            'day': slot.day,
            'period': slot.period,
        }
        
        response = render(request, 'timetable/htmx/slot_cell.html', context)
        response['HX-Trigger'] = json.dumps({
            'slotUpdated': {
                'slotId': slot.id,
                'timetableId': slot.timetable_id
            },
            'showToast': {
                'message': '✓ Slot updated successfully',
                'type': 'success'
            }
        })
        
        logger.info(f"Slot {slot_id} updated successfully, returning response")
        return response


@method_decorator(require_http_methods(["POST"]), name='dispatch')
class SlotClearView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    POST: Clear a slot (remove teacher and subject).
    Returns updated cell HTML.
    """
    permission_required = 'timetable.change_timetable'
    
    def post(self, request, slot_id):
        logger.info(f"Clearing slot {slot_id}, user={request.user}")
        
        slot = TimetableSlotSelector.get_by_id_model(slot_id)
        if not slot:
            logger.error(f"Slot {slot_id} not found")
            return HttpResponse(
                '<div class="text-red-500 p-2">Slot not found</div>',
                status=404
            )
        
        with transaction.atomic():
            old_teacher = slot.teacher.get_full_name if slot.teacher else None
            
            slot.teacher = None
            slot.subject = None
            slot.is_free_period = False
            slot.room = ''
            slot.updated_at = timezone.now()
            slot.save()
            
            SystemLogService.log_action(
                user=request.user,
                action=SystemLog.ActionType.UPDATE,
                app_label='timetable',
                model_name='TimetableSlot',
                object_id=str(slot.id),
                object_repr=f"{slot.day.name} {slot.period.display_name}",
                changes={'action': 'cleared', 'previous_teacher': old_teacher},
                request=request
            )
        
        logger.info(f"Slot {slot_id} cleared successfully")
        
        context = {'slot': slot, 'day': slot.day, 'period': slot.period}
        response = render(request, 'timetable/htmx/slot_cell.html', context)
        response['HX-Trigger'] = json.dumps({
            'slotUpdated': {'timetableId': slot.timetable_id},
            'showToast': {'message': '✓ Slot cleared', 'type': 'info'}
        })
        
        return response


class SlotCellView(LoginRequiredMixin, View):
    """GET: Return slot cell HTML fragment for refresh."""
    
    def get(self, request, slot_id):
        slot = TimetableSlotSelector.get_by_id_model(slot_id)
        if not slot:
            return HttpResponse('<div class="text-red-500 p-2">Slot not found</div>', status=404)
        
        context = {'slot': slot, 'day': slot.day, 'period': slot.period}
        return render(request, 'timetable/htmx/slot_cell.html', context)


class TimetableStatsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """GET: Return stats cards HTML fragment."""
    permission_required = 'timetable.view_timetable'
    
    def get(self, request, pk):
        timetable = TimetableSelector.get_by_id_model(pk)
        if not timetable:
            return HttpResponse('<div class="text-red-500 p-4">Timetable not found</div>', status=404)
        
        stats = TimetableStatsSelector.get_timetable_stats(pk)
        clash_summary = TimetableStatsSelector.get_clash_summary(pk)
        
        context = {
            'timetable': timetable,
            'stats': stats,
            'clash_summary': clash_summary,
        }
        
        return render(request, 'timetable/htmx/stats_cards.html', context)


class RecommendationsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """GET: Return recommendations panel HTML fragment."""
    permission_required = 'timetable.view_timetable'
    
    def get(self, request, pk):
        recommendations = TimetableRecommendationService.generate_recommendations(pk)
        balance = TimetableRecommendationService.balance_teacher_load(pk)
        
        context = {
            'recommendations': recommendations,
            'balance': balance,
            'timetable_id': pk,
        }
        
        return render(request, 'timetable/htmx/recommendations_panel.html', context)


@method_decorator(require_http_methods(["POST"]), name='dispatch')
class ApplyRecommendationView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """POST: Apply a single recommendation, return updated cell."""
    permission_required = 'timetable.change_timetable'
    
    def post(self, request, pk):
        slot_id = request.POST.get('slot_id')
        teacher_id = request.POST.get('teacher_id')
        subject_id = request.POST.get('subject_id')
        
        logger.info(f"Applying recommendation: slot={slot_id}, teacher={teacher_id}, subject={subject_id}")
        
        slot = TimetableSlotSelector.get_by_id_model(int(slot_id))
        if not slot:
            return HttpResponse(status=404)
        
        has_clash, clash_details = ClashDetectionService.check_teacher_clash(
            timetable_id=pk,
            teacher_id=int(teacher_id),
            day_id=slot.day_id,
            period_id=slot.period_id,
            exclude_slot_id=slot.id
        )
        
        if has_clash:
            response = HttpResponse(status=409)
            response['HX-Trigger'] = json.dumps({
                'showToast': {'message': '⚠️ Cannot assign - teacher clash', 'type': 'warning'}
            })
            return response
        
        with transaction.atomic():
            from apps.staffs.models import Staff
            from apps.corecode.models import Subject
            
            slot.teacher = Staff.objects.get(id=int(teacher_id))
            slot.subject = Subject.objects.get(id=int(subject_id))
            slot.is_free_period = False
            slot.save()
            
            SystemLogService.log_action(
                user=request.user,
                action=SystemLog.ActionType.UPDATE,
                app_label='timetable',
                model_name='TimetableSlot',
                object_id=str(slot.id),
                object_repr=f"{slot.day.name} {slot.period.display_name}",
                changes={'action': 'auto_assigned', 'teacher': slot.teacher.get_full_name, 'subject': slot.subject.name},
                request=request
            )
        
        context = {'slot': slot, 'day': slot.day, 'period': slot.period}
        response = render(request, 'timetable/htmx/slot_cell.html', context)
        response['HX-Trigger'] = json.dumps({
            'slotUpdated': {'timetableId': pk},
            'showToast': {'message': '✓ Recommendation applied', 'type': 'success'},
            'refreshRecommendations': True
        })
        
        return response


@method_decorator(require_http_methods(["POST"]), name='dispatch')
class ClearAllView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """POST: Clear all assignments, return updated grid."""
    permission_required = 'timetable.change_timetable'
    
    def post(self, request, pk):
        logger.info(f"Clearing all assignments for timetable {pk}, user={request.user}")
        
        cleared = TimetableService.clear_all_assignments(
            timetable_id=pk,
            cleared_by_id=request.user.id,
            request=request
        )
        
        timetable = TimetableSelector.get_by_id_model(pk)
        days = SchoolDaySelector.get_active_days_model()
        periods = TimetablePeriodSelector.get_all_periods_model()
        slots_by_day_period = TimetableSlotSelector.get_slots_grouped_by_day(pk)
        
        context = {
            'timetable': timetable,
            'days': days,
            'periods': periods,
            'slots_by_day_period': slots_by_day_period,
        }
        
        response = render(request, 'timetable/htmx/timetable_grid.html', context)
        response['HX-Trigger'] = json.dumps({
            'showToast': {'message': f'✓ Cleared {cleared} assignments', 'type': 'info'}
        })
        
        logger.info(f"Cleared {cleared} slots from timetable {pk}")
        return response


class ClashListView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """GET: Return clash list HTML fragment."""
    permission_required = 'timetable.view_timetable'
    
    def get(self, request, pk):
        clashes = ClashDetectionService.detect_all_clashes(pk)
        unresolved = ClashDetectionService.get_unresolved_clashes(pk)
        
        unresolved_list = []
        for clash_log in unresolved:
            unresolved_list.append({
                'id': clash_log.id,
                'teacher_name': clash_log.teacher.get_full_name(),
                'day': clash_log.day.name,
                'detected_at': clash_log.detected_at,
            })
        
        context = {
            'clashes': clashes,
            'unresolved': unresolved_list,
            'timetable_id': pk,
        }
        
        return render(request, 'timetable/htmx/clash_list.html', context)
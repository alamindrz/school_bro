"""
Timetable API Views - JSON endpoints for external/async calls
Returns JSON, never HTML.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import logging

from ..services import ClashDetectionService
from ..services.recommendation import TimetableRecommendationService

logger = logging.getLogger(__name__)


@method_decorator(require_http_methods(["GET"]), name='dispatch')
class ClashCheckView(LoginRequiredMixin, View):
    """GET: Check for teacher clash - returns JSON"""
    
    def get(self, request):
        timetable_id = request.GET.get('timetable_id')
        teacher_id = request.GET.get('teacher_id')
        day_id = request.GET.get('day_id')
        period_id = request.GET.get('period_id')
        slot_id = request.GET.get('slot_id')
        
        if not all([timetable_id, teacher_id, day_id, period_id]):
            return JsonResponse({'has_clash': False, 'error': 'Missing parameters'}, status=400)
        
        try:
            has_clash, clash_details = ClashDetectionService.check_teacher_clash(
                timetable_id=int(timetable_id),
                teacher_id=int(teacher_id),
                day_id=int(day_id),
                period_id=int(period_id),
                exclude_slot_id=int(slot_id) if slot_id else None
            )
            
            return JsonResponse({
                'has_clash': has_clash,
                'clash_details': clash_details if has_clash else None
            })
            
        except Exception as e:
            logger.exception(f"Clash check failed: {e}")
            return JsonResponse({'has_clash': False, 'error': str(e)}, status=500)


@method_decorator(require_http_methods(["GET"]), name='dispatch')
class TeacherAvailabilityView(LoginRequiredMixin, View):
    """GET: Get teacher availability - returns JSON"""
    
    def get(self, request):
        teacher_id = request.GET.get('teacher_id')
        timetable_id = request.GET.get('timetable_id')
        
        if not teacher_id or not timetable_id:
            return JsonResponse({'error': 'Missing parameters'}, status=400)
        
        try:
            available = TimetableRecommendationService.get_teacher_availability(
                int(teacher_id),
                int(timetable_id)
            )
            return JsonResponse({'available_slots': available})
            
        except Exception as e:
            logger.exception(f"Teacher availability failed: {e}")
            return JsonResponse({'error': str(e)}, status=500)
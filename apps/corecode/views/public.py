"""
Public views for corecode
No authentication required
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.utils import timezone

from ..selectors import AcademicTermSelector, SiteConfigSelector
from ..constants import SiteConfigKey


class HealthCheckView(TemplateView):
    """Simple health check endpoint"""
    
    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
        })


@method_decorator(cache_page(60 * 15), name='dispatch')  # Cache for 15 minutes
class CurrentAcademicInfoView(TemplateView):
    """Public endpoint for current academic information"""
    
    def get(self, request, *args, **kwargs):
        term_info = AcademicTermSelector.get_active_term_details()
        config = SiteConfigSelector.get_current_academic_config()
        
        data = {
            'current_session': term_info.get('session'),
            'current_term': term_info.get('term_name'),
            'term_start': term_info.get('start_date'),
            'term_end': term_info.get('end_date'),
            'admissions_open': SiteConfigSelector.get_config_value(SiteConfigKey.ADMISSIONS_OPEN, False),
        }
        
        return JsonResponse(data)
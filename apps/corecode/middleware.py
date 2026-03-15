"""
Corecode Middleware
"""

from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
import logging

from .selectors import SiteConfigSelector
from .constants import SiteConfigKey

logger = logging.getLogger(__name__)


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Block access when maintenance mode is enabled
    Allow superusers to bypass
    """
    
    def process_request(self, request):
        # Skip for admin, login, and static files
        if request.path.startswith('/admin') or \
           request.path.startswith('/login') or \
           request.path.startswith('/static') or \
           request.path.startswith('/media'):
            return None
        
        # Check maintenance mode
        maintenance_mode = SiteConfigSelector.get_config_value(
            SiteConfigKey.MAINTENANCE_MODE, 
            False
        )
        
        if maintenance_mode and not request.user.is_superuser:
            return redirect('maintenance_mode')
        
        return None


class SiteConfigMiddleware(MiddlewareMixin):
    """
    Inject site config into request for easy access
    """
    
    def process_request(self, request):
        request.site_config = {
            'COMPANY_NAME': SiteConfigSelector.get_config_value('COMPANY_NAME', 'DETs Toolkit'),
            'ADMISSIONS_OPEN': SiteConfigSelector.get_config_value('ADMISSIONS_OPEN', False),
            'PASS_MARK': SiteConfigSelector.get_config_value('PASS_MARK', 40),
        }
        return None
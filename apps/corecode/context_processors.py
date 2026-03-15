"""
Corecode Context Processors
Inject navigation and common data into ALL templates
"""

from django.conf import settings
from .navigation import MenuRegistry
from .selectors import SiteConfigSelector, AcademicTermSelector
from django.urls import reverse
from django.utils import timezone


def navigation(request):
    """
    Inject navigation menu items into ALL templates
    This runs on EVERY request, making navigation available globally
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {
            'main_menu': [],
            'user_menu': [],
            'footer_menu': MenuRegistry.get_footer_menu(request.user) if hasattr(request, 'user') else [],
        }
    
    return {
        'main_menu': MenuRegistry.get_main_menu(request.user, request.path),
        'user_menu': MenuRegistry.get_user_menu(request.user, request.path),
        'footer_menu': MenuRegistry.get_footer_menu(request.user),
        'current_year': timezone.now().year,
    }


def site_config(request):
    """Inject site configuration into ALL templates"""
    return {
        'COMPANY_NAME': SiteConfigSelector.get_config_value('COMPANY_NAME', 'DETs Toolkit'),
        'CURRENT_TERM': AcademicTermSelector.get_current_term(),
        'DEBUG': settings.DEBUG,
        'VERSION': getattr(settings, 'VERSION', '1.0.0'),
    }


def breadcrumbs(request):
    """
    Generate breadcrumbs based on current URL
    This helps with navigation context
    """
    if not hasattr(request, 'resolver_match') or not request.resolver_match:
        return {'breadcrumbs': []}
    
    breadcrumbs = []
    url_name = request.resolver_match.url_name
    app_name = request.resolver_match.app_name
    
    # Home breadcrumb
    breadcrumbs.append({
        'url': reverse('corecode:dashboard'),
        'title': 'Home',
        'active': False
    })
    
    # App breadcrumb
    if app_name:
        app_titles = {
            'students': 'Students',
            'staffs': 'Staff',
            'admissions': 'Admissions',
            'finance': 'Finance',
            'results': 'Results',
            'attendance': 'Attendance',
            'parents': 'Parents Portal',
            'corecode': 'System',
            'audit': 'Audit',
            'notifications': 'Notifications',
        }
        app_title = app_titles.get(app_name, app_name.title())
        breadcrumbs.append({
            'url': reverse(f'{app_name}:dashboard') if hasattr(reverse, f'{app_name}:dashboard') else '#',
            'title': app_title,
            'active': False
        })
    
    # Current page
    if url_name:
        page_title = url_name.replace('_', ' ').title()
        breadcrumbs.append({
            'url': request.path,
            'title': page_title,
            'active': True
        })
    
    return {'breadcrumbs': breadcrumbs}
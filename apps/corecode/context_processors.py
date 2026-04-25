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
    """Inject navigation menu items into ALL templates"""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {
            'main_menu': [],
            'user_menu': [],
            'footer_menu': MenuRegistry.get_footer_menu(request.user) if hasattr(request, 'user') else [],
            'current_path': request.path,
        }
    
    return {
        'main_menu': MenuRegistry.get_main_menu(request.user, request.path),
        'user_menu': MenuRegistry.get_user_menu(request.user, request.path),
        'footer_menu': MenuRegistry.get_footer_menu(request.user),
        'current_year': timezone.now().year,
        'current_path': request.path,
    }


def site_config(request):
    """Inject site configuration into ALL templates"""
    return {
        'COMPANY_NAME': SiteConfigSelector.get_config_value('COMPANY_NAME', 'DETs Toolkit'),
        'CURRENT_TERM': AcademicTermSelector.get_current_term(),
        'DEBUG': settings.DEBUG,
        'VERSION': getattr(settings, 'VERSION', '1.0.0'),
        'theme_preference': request.COOKIES.get('theme', 'light'),
    }


def breadcrumbs(request):
    """Generate breadcrumbs based on current URL"""
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
    app_titles = {
        'students': 'Students',
        'staffs': 'Staff',
        'admissions': 'Admissions',
        'finance': 'Finance',
        'results': 'Results',
        'attendance': 'Attendance',
        'parents': 'Parents Portal',
        'timetable': 'Timetable',
        'corecode': 'System',
    }
    
    if app_name and app_name in app_titles:
        breadcrumbs.append({
            'url': '#',
            'title': app_titles[app_name],
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
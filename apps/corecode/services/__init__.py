"""
Corecode Services - Foundation Business Logic
This is the SINGLE SOURCE OF TRUTH for core academic operations.
All other apps depend on these services.
"""

from .academic import AcademicSessionService, AcademicTermService
from .classes import StudentClassService
from .config import SiteConfigService
from .logging import SystemLogService

__all__ = [
    'AcademicSessionService',
    'AcademicTermService',
    'StudentClassService',
    'SiteConfigService',
    'SystemLogService',
]
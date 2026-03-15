"""
Corecode Exceptions - Foundation exception hierarchy
All other app exceptions inherit from these
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class CorecodeError(Exception):
    """Base exception for all corecode errors"""
    default_message = _("A core system error occurred")
    
    def __init__(self, message=None, code=None, params=None):
        self.message = message or self.default_message
        self.code = code or 'core_error'
        self.params = params or {}
        super().__init__(self.message)


class ConfigurationError(CorecodeError):
    """Site configuration errors"""
    default_message = _("System configuration error")
    code = 'config_error'


class AcademicStructureError(CorecodeError):
    """Academic session/term/class errors"""
    default_message = _("Academic structure error")
    code = 'academic_error'


class ClassNotFoundError(AcademicStructureError):
    """Student class not found"""
    default_message = _("The requested class does not exist")
    code = 'class_not_found'


class SessionNotFoundError(AcademicStructureError):
    """Academic session not found"""
    default_message = _("The requested academic session does not exist")
    code = 'session_not_found'


class TermNotFoundError(AcademicStructureError):
    """Academic term not found"""
    default_message = _("The requested term does not exist")
    code = 'term_not_found'


class InvalidClassProgressionError(AcademicStructureError):
    """Invalid class progression (e.g., skipping levels)"""
    default_message = _("Invalid class progression")
    code = 'invalid_progression'


class NoActiveSessionError(AcademicStructureError):
    """No active academic session configured"""
    default_message = _("No active academic session is configured")
    code = 'no_active_session'


class NoActiveTermError(AcademicStructureError):
    """No active academic term configured"""
    default_message = _("No active academic term is configured")
    code = 'no_active_term'


class SystemLogError(CorecodeError):
    """System logging errors"""
    default_message = _("System log error")
    code = 'log_error'


class PermissionDefinitionError(CorecodeError):
    """Permission definition errors"""
    default_message = _("Permission configuration error")
    code = 'permission_error'


# Type mapping for API responses
EXCEPTION_TYPE_MAP = {
    'ConfigurationError': 400,
    'AcademicStructureError': 400,
    'ClassNotFoundError': 404,
    'SessionNotFoundError': 404,
    'TermNotFoundError': 404,
    'NoActiveSessionError': 503,
    'NoActiveTermError': 503,
    'SystemLogError': 500,
    'PermissionDefinitionError': 500,
}


def get_exception_status_code(exception):
    """Get HTTP status code for exception type"""
    exception_class = exception.__class__.__name__
    return EXCEPTION_TYPE_MAP.get(exception_class, 500)
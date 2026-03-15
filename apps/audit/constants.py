"""
Audit App Constants
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditAction:
    """Types of audited actions"""
    
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    VIEW = 'VIEW'
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'
    EXPORT = 'EXPORT'
    IMPORT = 'IMPORT'
    DOWNLOAD = 'DOWNLOAD'
    PRINT = 'PRINT'
    
    CHOICES = [
        (CREATE, _('Create')),
        (UPDATE, _('Update')),
        (DELETE, _('Delete')),
        (VIEW, _('View')),
        (LOGIN, _('Login')),
        (LOGOUT, _('Logout')),
        (EXPORT, _('Export')),
        (IMPORT, _('Import')),
        (DOWNLOAD, _('Download')),
        (PRINT, _('Print')),
    ]


class AuditStatus:
    """Status of audited operation"""
    
    SUCCESS = 'success'
    FAILURE = 'failure'
    ATTEMPT = 'attempt'
    
    CHOICES = [
        (SUCCESS, _('Success')),
        (FAILURE, _('Failure')),
        (ATTEMPT, _('Attempt')),
    ]


class AuditCategory:
    """Categories for grouping audits"""
    
    AUTHENTICATION = 'auth'
    AUTHORIZATION = 'authz'
    DATA_ACCESS = 'data_access'
    DATA_MODIFICATION = 'data_mod'
    SYSTEM = 'system'
    FINANCIAL = 'financial'
    ACADEMIC = 'academic'
    
    CHOICES = [
        (AUTHENTICATION, _('Authentication')),
        (AUTHORIZATION, _('Authorization')),
        (DATA_ACCESS, _('Data Access')),
        (DATA_MODIFICATION, _('Data Modification')),
        (SYSTEM, _('System')),
        (FINANCIAL, _('Financial')),
        (ACADEMIC, _('Academic')),
    ]
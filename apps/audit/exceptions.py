"""
Audit App Exceptions
"""

from apps.corecode.exceptions import CorecodeError


class AuditError(CorecodeError):
    """Base exception for audit errors"""
    default_message = "An audit error occurred"
    code = 'audit_error'


class AuditLogNotFoundError(AuditError):
    """Audit log not found"""
    default_message = "Audit log not found"
    code = 'audit_log_not_found'


class AuditArchiveError(AuditError):
    """Error archiving audit logs"""
    default_message = "Failed to archive audit logs"
    code = 'archive_error'


class RetentionPolicyError(AuditError):
    """Error with retention policy"""
    default_message = "Retention policy error"
    code = 'retention_policy_error'
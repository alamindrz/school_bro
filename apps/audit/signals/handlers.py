"""
Audit Signals - Automatic audit logging
Modified to handle migrations safely with proper detection
"""

from django.db.models.signals import post_save, pre_delete, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db import connection
import threading
import sys
import logging

from ..services import AuditService
from ..constants import AuditAction, AuditCategory

User = get_user_model()
logger = logging.getLogger(__name__)

# Thread local storage to track user for current request
_thread_locals = threading.local()


def get_current_user():
    """Get current user from thread locals"""
    return getattr(_thread_locals, 'user', None)


def set_current_user(user):
    """Set current user for thread"""
    _thread_locals.user = user


class CurrentUserMiddleware:
    """Middleware to set current user for audit"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        set_current_user(request.user if request.user.is_authenticated else None)
        response = self.get_response(request)
        set_current_user(None)
        return response


def is_migration_running():
    """
    Check if migrations are currently running.
    Uses multiple detection methods for reliability.
    """
    # Check command line arguments
    if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
        return True
    
    # Check if we're in a migration context
    try:
        from django.db.migrations.state import ProjectState
        if hasattr(connection, 'migration_state'):
            return True
    except ImportError:
        pass
    
    # Check for migration-specific attributes
    if hasattr(connection, 'migration_apps'):
        return connection.migration_apps is not None
    
    # Check if tables are being created
    if hasattr(connection, 'creation') and hasattr(connection.creation, 'create_test_db'):
        return False
    
    return False


def safe_json_serializable(obj):
    """Convert non-serializable objects to strings"""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if hasattr(obj, '__dict__'):
        # For model instances, convert to string representation
        return str(obj)
    if hasattr(obj, 'isoformat'):  # datetime, date, time
        return obj.isoformat()
    return str(obj)


def prepare_audit_data(data):
    """Prepare data for JSON serialization"""
    if data is None:
        return {}
    
    if isinstance(data, dict):
        return {k: prepare_audit_data(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return [prepare_audit_data(item) for item in data]
    else:
        return safe_json_serializable(data)


@receiver(pre_save)
def audit_pre_save(sender, instance, **kwargs):
    """Audit changes before save - skip during migrations"""
    # Skip during migrations
    if is_migration_running():
        return
    
    # Skip audit for audit models themselves
    if sender.__name__ in ['AuditLog', 'AuditArchive', 'AuditRetentionPolicy']:
        return
    
    # Skip if no primary key (new object)
    if not instance.pk:
        return
    
    try:
        old = sender.objects.get(pk=instance.pk)
        # Store old values for later comparison
        instance._audit_old = old
    except sender.DoesNotExist:
        pass
    except Exception as e:
        logger.debug(f"Audit pre_save failed: {e}")


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    """Audit after save - skip during migrations"""
    # Skip during migrations
    if is_migration_running():
        return
    
    # Skip audit for audit models themselves
    if sender.__name__ in ['AuditLog', 'AuditArchive', 'AuditRetentionPolicy']:
        return
    
    user = get_current_user()
    
    try:
        if created:
            # Log create - prepare data for JSON
            instance_dict = {}
            for field in instance._meta.fields:
                value = getattr(instance, field.name)
                instance_dict[field.name] = safe_json_serializable(value)
            
            AuditService.log_create(
                user=user,
                app_label=sender._meta.app_label,
                model_name=sender.__name__,
                object_id=str(instance.pk),
                object_repr=str(instance),
                new_value=prepare_audit_data(instance_dict),
            )
        else:
            # Log update
            if hasattr(instance, '_audit_old'):
                old = instance._audit_old
                
                # Prepare old and new data
                old_dict = {}
                new_dict = {}
                
                for field in instance._meta.fields:
                    field_name = field.name
                    old_value = getattr(old, field_name)
                    new_value = getattr(instance, field_name)
                    
                    if old_value != new_value:
                        old_dict[field_name] = safe_json_serializable(old_value)
                        new_dict[field_name] = safe_json_serializable(new_value)
                
                # Only log if there are changes
                if old_dict or new_dict:
                    AuditService.log_update(
                        user=user,
                        app_label=sender._meta.app_label,
                        model_name=sender.__name__,
                        object_id=str(instance.pk),
                        object_repr=str(instance),
                        old_value=prepare_audit_data(old_dict),
                        new_value=prepare_audit_data(new_dict),
                    )
    except Exception as e:
        logger.error(f"Audit post_save failed for {sender.__name__}: {e}")


@receiver(pre_delete)
def audit_pre_delete(sender, instance, **kwargs):
    """Audit before delete - skip during migrations"""
    # Skip during migrations
    if is_migration_running():
        return
    
    # Skip audit for audit models themselves
    if sender.__name__ in ['AuditLog', 'AuditArchive', 'AuditRetentionPolicy']:
        return
    
    user = get_current_user()
    
    try:
        # Store instance data for audit
        instance_dict = {}
        for field in instance._meta.fields:
            value = getattr(instance, field.name)
            instance_dict[field.name] = safe_json_serializable(value)
        
        instance._audit_data = prepare_audit_data(instance_dict)
    except Exception as e:
        logger.debug(f"Audit pre_delete failed: {e}")


@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    """Audit after delete - skip during migrations"""
    # Skip during migrations
    if is_migration_running():
        return
    
    # Skip audit for audit models themselves
    if sender.__name__ in ['AuditLog', 'AuditArchive', 'AuditRetentionPolicy']:
        return
    
    user = get_current_user()
    
    try:
        if hasattr(instance, '_audit_data'):
            AuditService.log_delete(
                user=user,
                app_label=sender._meta.app_label,
                model_name=sender.__name__,
                object_id=str(instance.pk),
                object_repr=str(instance),
                old_value=instance._audit_data,
            )
    except Exception as e:
        logger.error(f"Audit post_delete failed for {sender.__name__}: {e}")


@receiver(user_logged_in)
def audit_user_login(sender, request, user, **kwargs):
    """Audit user login - skip during migrations"""
    if is_migration_running():
        return
    
    try:
        AuditService.log_login(user, request, success=True)
    except Exception as e:
        logger.error(f"Audit login failed: {e}")


@receiver(user_logged_out)
def audit_user_logout(sender, request, user, **kwargs):
    """Audit user logout - skip during migrations"""
    if is_migration_running():
        return
    
    try:
        if user:
            AuditService.log(
                user=user,
                action=AuditAction.LOGOUT,
                category=AuditCategory.AUTHENTICATION,
                app_label='auth',
                model_name='User',
                object_id=str(user.id),
                object_repr=user.get_username(),
                request=request,
            )
    except Exception as e:
        logger.error(f"Audit logout failed: {e}")
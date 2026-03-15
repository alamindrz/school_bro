"""
Audit Service
Centralized audit logging for all apps
Fixed to handle missing request data gracefully
"""

from django.utils import timezone
from django.contrib.auth import get_user_model
from typing import Optional, Dict, Any
import json
import logging

from .models import AuditLog
from .constants import AuditAction, AuditStatus, AuditCategory

logger = logging.getLogger(__name__)
User = get_user_model()


class AuditService:
    """
    Centralized audit logging service
    Use this service for all audit logging across apps
    """
    
    @classmethod
    def log(
        cls,
        user,
        action: str,
        app_label: str,
        model_name: str,
        category: str = AuditCategory.DATA_ACCESS,
        status: str = AuditStatus.SUCCESS,
        object_id: str = None,
        object_repr: str = None,
        old_value: Dict = None,
        new_value: Dict = None,
        changes: Dict = None,
        request=None,
        ip_address: str = None,
        user_agent: str = None,
        request_method: str = None,
        request_path: str = None,
    ) -> Optional[AuditLog]:
        """
        Create an audit log entry.
        Returns None if logging fails (to prevent breaking main flow).
        """
        try:
            # Extract request info if provided
            if request:
                ip_address = ip_address or cls._get_client_ip(request)
                user_agent = user_agent or request.META.get('HTTP_USER_AGENT', '')[:500]
                request_method = request_method or request.method
                request_path = request_path or request.path
            
            # Default values for required fields
            user_agent = user_agent or ''
            ip_address = ip_address or '0.0.0.0'
            
            # Get user info
            user_obj = None
            username = ''
            user_email = ''
            user_role = ''
            
            if user:
                if isinstance(user, User):
                    user_obj = user
                    username = user.get_username()
                    user_email = user.email or ''
                    # Get user role from groups
                    user_role = ', '.join([g.name for g in user.groups.all()])
                elif isinstance(user, int):
                    try:
                        user_obj = User.objects.get(id=user)
                        username = user_obj.get_username()
                        user_email = user_obj.email or ''
                    except User.DoesNotExist:
                        username = str(user)
                else:
                    username = str(user)
            
            # Generate changes if old and new provided
            if old_value and new_value and not changes:
                changes = cls._compute_changes(old_value, new_value)
            
            # Ensure all JSON fields are serializable
            old_value = cls._ensure_serializable(old_value or {})
            new_value = cls._ensure_serializable(new_value or {})
            changes = cls._ensure_serializable(changes or {})
            
            # Create audit log
            log = AuditLog(
                user=user_obj,
                username=username or 'system',
                user_email=user_email,
                user_role=user_role,
                action=action,
                category=category,
                status=status,
                app_label=app_label,
                model_name=model_name,
                object_id=str(object_id) if object_id else None,
                object_repr=str(object_repr)[:200] if object_repr else None,
                old_value=old_value,
                new_value=new_value,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path,
            )
            
            log.save()
            return log
            
        except Exception as e:
            # Log error but don't crash the main operation
            logger.error(f"Audit logging failed: {e}")
            return None
    
    @classmethod
    def log_create(
        cls,
        user,
        app_label: str,
        model_name: str,
        object_id: str,
        object_repr: str = None,
        new_value: Dict = None,
        request=None,
    ) -> Optional[AuditLog]:
        """Log create operation"""
        return cls.log(
            user=user,
            action=AuditAction.CREATE,
            category=AuditCategory.DATA_MODIFICATION,
            app_label=app_label,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr,
            new_value=new_value,
            request=request,
        )
    
    @classmethod
    def log_update(
        cls,
        user,
        app_label: str,
        model_name: str,
        object_id: str,
        object_repr: str = None,
        old_value: Dict = None,
        new_value: Dict = None,
        changes: Dict = None,
        request=None,
    ) -> Optional[AuditLog]:
        """Log update operation"""
        return cls.log(
            user=user,
            action=AuditAction.UPDATE,
            category=AuditCategory.DATA_MODIFICATION,
            app_label=app_label,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr,
            old_value=old_value,
            new_value=new_value,
            changes=changes,
            request=request,
        )
    
    @classmethod
    def log_delete(
        cls,
        user,
        app_label: str,
        model_name: str,
        object_id: str,
        object_repr: str = None,
        old_value: Dict = None,
        request=None,
    ) -> Optional[AuditLog]:
        """Log delete operation"""
        return cls.log(
            user=user,
            action=AuditAction.DELETE,
            category=AuditCategory.DATA_MODIFICATION,
            status=AuditStatus.SUCCESS,
            app_label=app_label,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr,
            old_value=old_value,
            request=request,
        )
    
    @classmethod
    def log_login(cls, user, request=None, success=True) -> Optional[AuditLog]:
        """Log login attempt"""
        return cls.log(
            user=user,
            action=AuditAction.LOGIN,
            category=AuditCategory.AUTHENTICATION,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            app_label='auth',
            model_name='User',
            object_id=str(user.id) if user else None,
            object_repr=user.get_username() if user else 'anonymous',
            request=request,
        )
    
    @classmethod
    def log_export(cls, user, app_label: str, model_name: str, count: int, request=None) -> Optional[AuditLog]:
        """Log data export"""
        return cls.log(
            user=user,
            action=AuditAction.EXPORT,
            category=AuditCategory.DATA_ACCESS,
            app_label=app_label,
            model_name=model_name,
            object_repr=f"Exported {count} records",
            new_value={'count': count},
            request=request,
        )
    
    @classmethod
    def _get_client_ip(cls, request):
        """Get client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')
    
    @classmethod
    def _compute_changes(cls, old: Dict, new: Dict) -> Dict:
        """Compute changes between old and new values"""
        changes = {}
        all_keys = set(old.keys()) | set(new.keys())
        
        for key in all_keys:
            old_val = old.get(key)
            new_val = new.get(key)
            
            # Handle different types appropriately
            if isinstance(old_val, (dict, list)) or isinstance(new_val, (dict, list)):
                if json.dumps(old_val, sort_keys=True, default=str) != json.dumps(new_val, sort_keys=True, default=str):
                    changes[key] = {
                        'old': cls._ensure_serializable(old_val),
                        'new': cls._ensure_serializable(new_val)
                    }
            elif old_val != new_val:
                changes[key] = {
                    'old': cls._ensure_serializable(old_val),
                    'new': cls._ensure_serializable(new_val)
                }
        
        return changes
    
    @classmethod
    def _ensure_serializable(cls, obj):
        """Ensure object is JSON serializable"""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, (dict, list)):
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                pass
        # Convert to string as fallback
        return str(obj)
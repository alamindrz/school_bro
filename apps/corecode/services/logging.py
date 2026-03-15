"""
System Logging Services
Comprehensive audit trail for all sensitive operations
"""

from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from typing import Optional, Dict, Any
import json

from ..models import SystemLog
from ..exceptions import SystemLogError

User = get_user_model()


class SystemLogService:
    """
    System-wide audit logging service
    Tracks who did what and when across the entire platform
    """
    
    @staticmethod
    @transaction.atomic
    def log_action(
        user,
        action: str,
        app_label: str,
        model_name: str,
        object_id: str = None,
        object_repr: str = None,
        changes: Dict = None,
        request=None,
        ip_address: str = None,
        user_agent: str = None
    ) -> SystemLog:
        """
        Create a system log entry - CENTRAL LOGGING METHOD
        
        Args:
            user: User performing the action (User instance or None for system)
            action: Action type from SystemLog.ActionType
            app_label: App label from SystemLog.AppLabel
            model_name: Name of the model being acted upon
            object_id: Primary key of the object (as string)
            object_repr: String representation of the object
            changes: Dictionary of changes made
            request: HTTP request object (extracts IP and user agent)
            ip_address: Manual IP address (overrides request)
            user_agent: Manual user agent (overrides request)
            
        Returns:
            SystemLog: Created log entry
        """
        # Extract request info if provided
        if request and not ip_address:
            ip_address = request.META.get('REMOTE_ADDR')
        if request and not user_agent:
            user_agent = user_agent or (request.META.get('HTTP_USER_AGENT', '') if request else '') or 'unknown'
        
        # Get username
        username = None
        if user:
            if isinstance(user, User):
                username = user.get_username()
            else:
                username = str(user)
        
        # Create log entry
        log = SystemLog(
            user=user if isinstance(user, User) else None,
            username=username or 'system',
            action=action,
            app_label=app_label,
            model_name=model_name,
            object_id=str(object_id) if object_id else None,
            object_repr=str(object_repr)[:200] if object_repr else None,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=timezone.now()
        )
        
        log.save()
        return log
    
    @staticmethod
    def log_create(
        user,
        app_label: str,
        model_name: str,
        object_id: str,
        object_repr: str = None,
        changes: Dict = None,
        request=None
    ) -> SystemLog:
        """Convenience method for CREATE actions"""
        return SystemLogService.log_action(
            user=user,
            action=SystemLog.ActionType.CREATE,
            app_label=app_label,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr,
            changes=changes,
            request=request
        )
    
    @staticmethod
    def log_update(
        user,
        app_label: str,
        model_name: str,
        object_id: str,
        object_repr: str = None,
        changes: Dict = None,
        request=None
    ) -> SystemLog:
        """Convenience method for UPDATE actions"""
        return SystemLogService.log_action(
            user=user,
            action=SystemLog.ActionType.UPDATE,
            app_label=app_label,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr,
            changes=changes,
            request=request
        )
    
    @staticmethod
    def log_delete(
        user,
        app_label: str,
        model_name: str,
        object_id: str,
        object_repr: str = None,
        request=None
    ) -> SystemLog:
        """Convenience method for DELETE actions"""
        return SystemLogService.log_action(
            user=user,
            action=SystemLog.ActionType.DELETE,
            app_label=app_label,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr,
            changes={'deleted': True},
            request=request
        )
    
    @staticmethod
    def log_login(user, request=None, success=True) -> SystemLog:
        """Log user login attempts"""
        return SystemLogService.log_action(
            user=user,
            action=SystemLog.ActionType.LOGIN,
            app_label=SystemLog.AppLabel.CORE,
            model_name='User',
            object_id=str(user.id) if user else None,
            object_repr=user.get_username() if user else 'anonymous',
            changes={'success': success},
            request=request
        )
    
    @staticmethod
    def log_logout(user, request=None) -> SystemLog:
        """Log user logout"""
        return SystemLogService.log_action(
            user=user,
            action=SystemLog.ActionType.LOGOUT,
            app_label=SystemLog.AppLabel.CORE,
            model_name='User',
            object_id=str(user.id) if user else None,
            object_repr=user.get_username() if user else 'anonymous',
            request=request
        )
    
    @staticmethod
    def log_grade_change(
        user,
        student,
        subject: str,
        old_grade: str,
        new_grade: str,
        request=None
    ) -> SystemLog:
        """Specialized logging for grade changes"""
        return SystemLogService.log_action(
            user=user,
            action=SystemLog.ActionType.GRADE_CHANGE,
            app_label=SystemLog.AppLabel.RESULTS,
            model_name='Result',
            object_id=str(student.id),
            object_repr=f"{student} - {subject}",
            changes={
                'old_grade': old_grade,
                'new_grade': new_grade,
                'subject': subject,
                'student_id': student.id,
                'student_name': str(student),
            },
            request=request
        )
    
    @staticmethod
    def log_payment(
        user,
        invoice,
        amount,
        payment_method: str,
        transaction_ref: str = None,
        request=None
    ) -> SystemLog:
        """Specialized logging for payments"""
        return SystemLogService.log_action(
            user=user,
            action=SystemLog.ActionType.PAYMENT,
            app_label=SystemLog.AppLabel.FINANCE,
            model_name='Invoice',
            object_id=str(invoice.id),
            object_repr=f"Invoice #{invoice.invoice_number}",
            changes={
                'amount': str(amount),
                'payment_method': payment_method,
                'transaction_ref': transaction_ref,
                'status': 'completed',
                'invoice_number': invoice.invoice_number,
            },
            request=request
        )
    
    @staticmethod
    def log_promotion(
        user,
        student,
        from_class,
        to_class,
        academic_session,
        request=None
    ) -> SystemLog:
        """Specialized logging for student promotions"""
        return SystemLogService.log_action(
            user=user,
            action=SystemLog.ActionType.PROMOTION,
            app_label=SystemLog.AppLabel.STUDENTS,
            model_name='Student',
            object_id=str(student.id),
            object_repr=str(student),
            changes={
                'from_class': str(from_class),
                'to_class': str(to_class),
                'academic_session': str(academic_session),
                'student_id': student.id,
                'student_name': str(student),
            },
            request=request
        )
    
    @staticmethod
    def log_waiver(
        user,
        invoice,
        amount,
        reason: str,
        approved_by,
        request=None
    ) -> SystemLog:
        """Specialized logging for fee waivers"""
        return SystemLogService.log_action(
            user=user,
            action=SystemLog.ActionType.WAIVER,
            app_label=SystemLog.AppLabel.FINANCE,
            model_name='Invoice',
            object_id=str(invoice.id),
            object_repr=f"Invoice #{invoice.invoice_number}",
            changes={
                'waived_amount': str(amount),
                'reason': reason,
                'approved_by': str(approved_by),
                'invoice_number': invoice.invoice_number,
            },
            request=request
        )
    
    @staticmethod
    @transaction.atomic
    def bulk_log(
        logs: list,
        user=None
    ) -> int:
        """
        Bulk create log entries (for performance)
        
        Args:
            logs: List of log entry dictionaries
            user: Default user for all entries
            
        Returns:
            int: Number of logs created
        """
        log_objects = []
        timestamp = timezone.now()
        
        for log_data in logs:
            log_objects.append(
                SystemLog(
                    user=user if isinstance(user, User) else None,
                    username=user.get_username() if user else 'system',
                    action=log_data.get('action'),
                    app_label=log_data.get('app_label'),
                    model_name=log_data.get('model_name'),
                    object_id=log_data.get('object_id'),
                    object_repr=log_data.get('object_repr', '')[:200],
                    changes=log_data.get('changes', {}),
                    ip_address=log_data.get('ip_address'),
                    user_agent=log_data.get('user_agent', '')[:500],
                    timestamp=timestamp
                )
            )
        
        return SystemLog.objects.bulk_create(log_objects).__len__()
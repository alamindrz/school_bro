"""
Audit Selectors
"""

from django.db.models import Q, Count
from django.utils import timezone
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from .models import AuditLog, AuditArchive, AuditRetentionPolicy
from .constants import AuditAction, AuditStatus, AuditCategory


class AuditLogSelector:
    """Audit log read operations"""
    
    @staticmethod
    def get_by_id(log_id: int) -> Optional[Dict[str, Any]]:
        """Get audit log by ID"""
        try:
            log = AuditLog.objects.get(id=log_id)
            return {
                'id': log.id,
                'audit_id': str(log.audit_id),
                'timestamp': log.timestamp.isoformat(),
                'user': {
                    'id': log.user.id if log.user else None,
                    'username': log.username,
                    'email': log.user_email,
                    'role': log.user_role,
                },
                'action': log.action,
                'action_display': log.get_action_display(),
                'category': log.category,
                'category_display': log.get_category_display(),
                'status': log.status,
                'status_display': log.get_status_display(),
                'target': {
                    'app': log.app_label,
                    'model': log.model_name,
                    'object_id': log.object_id,
                    'object_repr': log.object_repr,
                },
                'changes': {
                    'old': log.old_value,
                    'new': log.new_value,
                    'diff': log.changes,
                },
                'context': {
                    'ip': log.ip_address,
                    'user_agent': log.user_agent,
                    'method': log.request_method,
                    'path': log.request_path,
                    'request_id': log.request_id,
                },
            }
        except AuditLog.DoesNotExist:
            return None
    
    @staticmethod
    def list_logs(
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        category: Optional[str] = None,
        app_label: Optional[str] = None,
        model_name: Optional[str] = None,
        object_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ip_address: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List audit logs with filters"""
        queryset = AuditLog.objects.all()
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        if action:
            queryset = queryset.filter(action=action)
        
        if category:
            queryset = queryset.filter(category=category)
        
        if app_label:
            queryset = queryset.filter(app_label=app_label)
        
        if model_name:
            queryset = queryset.filter(model_name=model_name)
        
        if object_id:
            queryset = queryset.filter(object_id=object_id)
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        if ip_address:
            queryset = queryset.filter(ip_address=ip_address)
        
        logs = []
        for log in queryset.order_by('-timestamp')[:limit]:
            logs.append({
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'username': log.username,
                'action': log.action,
                'action_display': log.get_action_display(),
                'category': log.category,
                'app_label': log.app_label,
                'model_name': log.model_name,
                'object_repr': log.object_repr,
                'ip_address': log.ip_address,
                'status': log.status,
            })
        
        return logs
    
    @staticmethod
    def get_user_activity(user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get activity summary for a user"""
        start_date = timezone.now() - timedelta(days=days)
        
        logs = AuditLog.objects.filter(
            user_id=user_id,
            timestamp__gte=start_date
        )
        
        return {
            'user_id': user_id,
            'period_days': days,
            'total_actions': logs.count(),
            'by_action': {
                action: logs.filter(action=action).count()
                for action, _ in AuditAction.CHOICES
            },
            'by_category': {
                cat: logs.filter(category=cat).count()
                for cat, _ in AuditCategory.CHOICES
            },
            'by_date': [
                {
                    'date': date.strftime('%Y-%m-%d'),
                    'count': count
                }
                for date, count in logs.extra(
                    select={'date': 'date(timestamp)'}
                ).values('date').annotate(count=Count('id')).order_by('date')
            ],
            'recent_ips': logs.values('ip_address').annotate(
                count=Count('id')
            ).order_by('-count')[:5],
        }
    
    @staticmethod
    def get_model_history(
        app_label: str,
        model_name: str,
        object_id: Optional[str] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get history for a specific model/object"""
        queryset = AuditLog.objects.filter(
            app_label=app_label,
            model_name=model_name,
            timestamp__gte=timezone.now() - timedelta(days=days)
        )
        
        if object_id:
            queryset = queryset.filter(object_id=object_id)
        
        history = []
        for log in queryset.order_by('-timestamp'):
            history.append({
                'timestamp': log.timestamp.isoformat(),
                'user': log.username,
                'action': log.action_display,
                'changes': log.changes,
                'old_value': log.old_value,
                'new_value': log.new_value,
            })
        
        return history


class AuditStatsSelector:
    """Audit statistics"""
    
    @staticmethod
    def get_summary(days: int = 30) -> Dict[str, Any]:
        """Get summary statistics"""
        start_date = timezone.now() - timedelta(days=days)
        logs = AuditLog.objects.filter(timestamp__gte=start_date)
        
        return {
            'period_days': days,
            'total_logs': logs.count(),
            'by_action': {
                action: logs.filter(action=action).count()
                for action, _ in AuditAction.CHOICES
            },
            'by_category': {
                cat: logs.filter(category=cat).count()
                for cat, _ in AuditCategory.CHOICES
            },
            'by_status': {
                status: logs.filter(status=status).count()
                for status, _ in AuditStatus.CHOICES
            },
            'by_app': logs.values('app_label').annotate(
                count=Count('id')
            ).order_by('-count')[:10],
            'active_users': logs.values('user_id').distinct().count(),
            'unique_ips': logs.values('ip_address').distinct().count(),
        }
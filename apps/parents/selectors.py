"""
Parents Selectors - READ Layer
Returns dicts, never model instances
"""

from django.db.models import Q, Count
from django.utils import timezone
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from .models import ParentProfile, ChildLink, Notification, Message, PortalSession
from .constants import PortalAccessStatus, NotificationType, NotificationChannel

from apps.students.selectors import StudentSelector
from apps.finance.selectors import InvoiceSelector, PaymentSelector, FinancialStatusSelector
from apps.results.selectors import ScoreEntrySelector as ScoreEntrySelector  # Will be implemented later
from apps.attendance.selectors import AttendanceSelector  # Will be implemented later
from apps.finance.selectors import InvoiceSelector



class ParentProfileSelector:
    """All parent profile read operations"""
    
    @staticmethod
    def get_by_id(parent_id: int) -> Optional[Dict[str, Any]]:
        """Get parent profile by ID"""
        try:
            parent = ParentProfile.objects.prefetch_related('children').get(id=parent_id)
            
            return {
                'id': parent.id,
                'user_id': parent.user.id if parent.user else None,
                'guardian_id': parent.guardian_id,
                'full_name': parent.full_name,
                'first_name': parent.first_name,
                'last_name': parent.last_name,
                'email': parent.email,
                'phone': parent.phone,
                'alternate_phone': parent.alternate_phone,
                'access_status': parent.access_status,
                'access_status_display': parent.get_access_status_display(),
                'access_key': parent.access_key,
                'last_login': parent.last_login.isoformat() if parent.last_login else None,
                'login_count': parent.login_count,
                'preferred_language': parent.preferred_language,
                'notification_preferences': parent.notification_preferences,
                'created_at': parent.created_at.isoformat(),
                'children_count': parent.children.count(),
                'children': [
                    {
                        'id': child.id,
                        'student_id': child.student_id,
                        'student_name': child.student_name,
                        'student_class': child.student_class,
                        'relationship': child.get_relationship_display(),
                        'is_primary': child.is_primary,
                    }
                    for child in parent.children.all()
                ],
            }
        except ParentProfile.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_guardian_id(guardian_id: int) -> Optional[Dict[str, Any]]:
        """Get parent profile by guardian ID from students app"""
        try:
            parent = ParentProfile.objects.get(guardian_id=guardian_id)
            return ParentProfileSelector.get_by_id(parent.id)
        except ParentProfile.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get parent profile by email"""
        try:
            parent = ParentProfile.objects.get(email=email)
            return ParentProfileSelector.get_by_id(parent.id)
        except ParentProfile.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_access_key(access_key: str) -> Optional[Dict[str, Any]]:
        """Get parent profile by access key (for magic links)"""
        try:
            parent = ParentProfile.objects.get(access_key=access_key)
            return ParentProfileSelector.get_by_id(parent.id)
        except ParentProfile.DoesNotExist:
            return None
    
    @staticmethod
    def search_parents(
        query: str,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search parents by name, email, or phone"""
        queryset = ParentProfile.objects.all()
        
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query)
            )
        
        if status:
            queryset = queryset.filter(access_status=status)
        
        parents = []
        for parent in queryset.order_by('last_name', 'first_name')[:limit]:
            parents.append({
                'id': parent.id,
                'full_name': parent.full_name,
                'email': parent.email,
                'phone': parent.phone,
                'access_status': parent.access_status,
                'access_status_display': parent.get_access_status_display(),
                'children_count': parent.children.count(),
                'last_login': parent.last_login.isoformat() if parent.last_login else None,
            })
        
        return parents
    
    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """Get parent portal statistics"""
        total_parents = ParentProfile.objects.count()
        
        return {
            'total_parents': total_parents,
            'active_parents': ParentProfile.objects.filter(access_status=PortalAccessStatus.ACTIVE).count(),
            'pending_parents': ParentProfile.objects.filter(access_status=PortalAccessStatus.PENDING).count(),
            'inactive_parents': ParentProfile.objects.filter(access_status=PortalAccessStatus.INACTIVE).count(),
            'parents_with_users': ParentProfile.objects.filter(user__isnull=False).count(),
            'total_children': ChildLink.objects.count(),
            'avg_children_per_parent': ChildLink.objects.count() / total_parents if total_parents > 0 else 0,
        }


class ChildLinkSelector:
    """Child link read operations"""
    
    @staticmethod
    def get_for_parent(parent_id: int) -> List[Dict[str, Any]]:
        """Get all children linked to a parent"""
        links = ChildLink.objects.filter(parent_id=parent_id).order_by('student_name')
        
        return [
            {
                'id': link.id,
                'student_id': link.student_id,
                'student_name': link.student_name,
                'student_class': link.student_class,
                'relationship': link.get_relationship_display(),
                'is_primary': link.is_primary,
                'permissions': {
                    'view_results': link.can_view_results,
                    'view_attendance': link.can_view_attendance,
                    'view_fees': link.can_view_fees,
                    'make_payments': link.can_make_payments,
                    'communicate': link.can_communicate,
                }
            }
            for link in links
        ]
    
    @staticmethod
    def get_for_student(student_id: int) -> List[Dict[str, Any]]:
        """Get all parents linked to a student"""
        links = ChildLink.objects.filter(student_id=student_id).select_related('parent')
        
        return [
            {
                'id': link.id,
                'parent_id': link.parent.id,
                'parent_name': link.parent.full_name,
                'parent_email': link.parent.email,
                'parent_phone': link.parent.phone,
                'relationship': link.get_relationship_display(),
                'is_primary': link.is_primary,
                'permissions': {
                    'view_results': link.can_view_results,
                    'view_attendance': link.can_view_attendance,
                    'view_fees': link.can_view_fees,
                    'make_payments': link.can_make_payments,
                    'communicate': link.can_communicate,
                }
            }
            for link in links
        ]
    
    @staticmethod
    def verify_access(parent_id: int, student_id: int, feature: str) -> bool:
        """Verify if parent has access to a specific feature for a student"""
        try:
            link = ChildLink.objects.get(parent_id=parent_id, student_id=student_id)
            
            feature_map = {
                'view_results': link.can_view_results,
                'view_attendance': link.can_view_attendance,
                'view_fees': link.can_view_fees,
                'make_payments': link.can_make_payments,
                'communicate': link.can_communicate,
            }
            
            return feature_map.get(feature, False)
            
        except ChildLink.DoesNotExist:
            return False


class NotificationSelector:
    """Notification read operations"""
    
    @staticmethod
    def get_for_parent(
        parent_id: int,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get notifications for a parent"""
        queryset = Notification.objects.filter(parent_id=parent_id)
        
        if unread_only:
            queryset = queryset.filter(is_read=False)
        
        notifications = []
        for note in queryset.order_by('-created_at')[:limit]:
            notifications.append({
                'id': note.id,
                'type': note.notification_type,
                'type_display': note.get_notification_type_display(),
                'channel': note.channel,
                'priority': note.priority,
                'title': note.title,
                'message': note.message,
                'data': note.data,
                'link_url': note.link_url,
                'link_text': note.link_text,
                'is_read': note.is_read,
                'is_sent': note.is_sent,
                'created_at': note.created_at.isoformat(),
                'time_ago': NotificationSelector._time_ago(note.created_at),
                'related_students': note.related_student_ids,
            })
        
        return notifications
    
    @staticmethod
    def get_unread_count(parent_id: int) -> int:
        """Get count of unread notifications"""
        return Notification.objects.filter(
            parent_id=parent_id,
            is_read=False
        ).count()
    
    @staticmethod
    def _time_ago(timestamp):
        """Human readable time ago"""
        diff = timezone.now() - timestamp
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "just now"


class MessageSelector:
    """Message read operations"""
    
    @staticmethod
    def get_conversations(parent_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get message conversations for a parent"""
        # Get messages where parent is sender or recipient
        messages = Message.objects.filter(
            Q(sender_parent_id=parent_id) | Q(recipient_parent_id=parent_id)
        ).select_related('sender_parent', 'recipient_parent').order_by('-sent_at')[:limit]
        
        conversations = []
        seen_students = set()
        
        for msg in messages:
            if msg.student_id not in seen_students:
                seen_students.add(msg.student_id)
                
                # Get last message for this student
                last_msg = Message.objects.filter(
                    Q(sender_parent_id=parent_id) | Q(recipient_parent_id=parent_id),
                    student_id=msg.student_id
                ).order_by('-sent_at').first()
                
                if last_msg:
                    conversations.append({
                        'student_id': last_msg.student_id,
                        'student_name': last_msg.student_name,
                        'last_message': last_msg.body[:100],
                        'last_message_date': last_msg.sent_at.isoformat(),
                        'last_message_time_ago': NotificationSelector._time_ago(last_msg.sent_at),
                        'unread_count': Message.objects.filter(
                            recipient_parent_id=parent_id,
                            student_id=last_msg.student_id,
                            is_read=False
                        ).count(),
                        'is_from_parent': last_msg.sender_parent_id == parent_id,
                    })
        
        return conversations
    
    @staticmethod
    def get_messages_for_student(
        parent_id: int,
        student_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get message thread for a specific student"""
        messages = Message.objects.filter(
            Q(sender_parent_id=parent_id) | Q(recipient_parent_id=parent_id),
            student_id=student_id
        ).select_related('sender_parent', 'recipient_parent').order_by('sent_at')[:limit]
        
        return [
            {
                'id': msg.id,
                'subject': msg.subject,
                'body': msg.body,
                'sent_at': msg.sent_at.isoformat(),
                'time_ago': NotificationSelector._time_ago(msg.sent_at),
                'is_from_parent': msg.sender_parent_id == parent_id,
                'sender_name': msg.sender_parent.full_name if msg.sender_parent else 'Teacher',
                'is_read': msg.is_read,
                'is_urgent': msg.is_urgent,
            }
            for msg in messages
        ]


class PortalDashboardSelector:
    """
    Aggregator for parent portal dashboard data
    Combines data from multiple sources
    """
    
    @staticmethod
    def get_dashboard_data(parent_id: int) -> Dict[str, Any]:
        """Get complete dashboard data for a parent"""
        parent = ParentProfileSelector.get_by_id(parent_id)
        if not parent:
            return {}
        
        children = ChildLinkSelector.get_for_parent(parent_id)
        
        dashboard_data = {
            'parent': parent,
            'children': [],
            'notifications': NotificationSelector.get_for_parent(parent_id, unread_only=False, limit=10),
            'unread_notifications': NotificationSelector.get_unread_count(parent_id),
            'recent_messages': MessageSelector.get_conversations(parent_id, limit=5),
        }
        
        # For each child, gather relevant data
        for child in children:
            student_id = child['student_id']
            student = StudentSelector.get_by_id(student_id)
            
            if student:
                child_data = {
                    'link': child,
                    'student': student,
                    'financial': InvoiceSelector.get_student_balance(student_id),
                    'exam_clearance': FinancialStatusSelector.is_student_cleared_for_exams(student_id),
                    
                'recent_invoices': InvoiceSelector.list_invoices(
                    student_id=student_id,
                    status=['pending', 'partial', 'overdue'],
                    limit=5
                ),   
                                    'recent_payments': PaymentSelector.list_payments(
                        student_id=student_id,
                        limit=5
                    ),
                }
                
                # Add application status for this student
                from apps.admissions.selectors import ApplicationSelector
                application = ApplicationSelector.get_by_student_id(student_id)
                if application:
                    child_data['application'] = {
                        'status': application['status'],
                        'status_display': application['status_display'],
                        'application_number': application['application_number'],
                        'submitted_at': application['submitted_at'],
                    }
                
                # Add results if available (will be implemented later)
                # child_data['recent_results'] = ScoreEntrySelector.get_recent_for_student(student_id, limit=3)
                
                # Add attendance later when available
                # child_data['attendance_summary'] = AttendanceSelector.get_student_summary(student_id)
                
                dashboard_data['children'].append(child_data)
        
        return dashboard_data
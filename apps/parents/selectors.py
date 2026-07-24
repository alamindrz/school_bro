"""
Parents Selectors - READ Layer
Returns dicts, never model instances
All queries optimized with select_related and prefetch_related
"""

from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from typing import Optional, List, Dict, Any, TypedDict
from datetime import timedelta

from .models import ParentProfile, ChildLink, Message
from .constants import PortalAccessStatus

# Import notification selectors from central app
from apps.notifications.selectors import NotificationSelector as CentralNotificationSelector
from apps.notifications.selectors import UserPreferenceSelector


# Type definitions
class ParentProfileData(TypedDict, total=False):
    id: int
    user_id: Optional[int]
    guardian_id: int
    full_name: str
    first_name: str
    last_name: str
    email: str
    phone: str
    alternate_phone: str
    access_status: str
    access_status_display: str
    access_key: str
    last_login: Optional[str]
    login_count: int
    preferred_language: str
    created_at: str
    children_count: int
    children: List[Dict]


class ChildLinkData(TypedDict):
    id: int
    student_id: int
    student_name: str
    student_class: str
    relationship: str
    is_primary: bool
    permissions: Dict[str, bool]


class MessageData(TypedDict):
    id: int
    subject: str
    body: str
    sent_at: str
    time_ago: str
    is_from_parent: bool
    sender_name: str
    is_read: bool
    is_urgent: bool


class ConversationData(TypedDict):
    student_id: int
    student_name: str
    last_message: str
    last_message_date: str
    last_message_time_ago: str
    unread_count: int
    is_from_parent: bool


class ParentProfileSelector:
    """All parent profile read operations"""
    
    @staticmethod
    def get_by_id(parent_id: int) -> Optional[ParentProfileData]:
        try:
            parent = ParentProfile.objects.select_related('user').prefetch_related(
                Prefetch('children', queryset=ChildLink.objects.select_related('parent'))
            ).get(id=parent_id)
            return ParentProfileSelector._serialize(parent)
        except ParentProfile.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_guardian_id(guardian_id: int) -> Optional[ParentProfileData]:
        try:
            parent = ParentProfile.objects.select_related('user').prefetch_related(
                Prefetch('children', queryset=ChildLink.objects.select_related('parent'))
            ).get(guardian_id=guardian_id)
            return ParentProfileSelector._serialize(parent)
        except ParentProfile.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_email(email: str) -> Optional[ParentProfileData]:
        parent = ParentProfile.objects.select_related('user').get_by_email(email)
        if parent:
            return ParentProfileSelector._serialize(parent)
        return None
    
    @staticmethod
    def get_by_access_key(access_key: str) -> Optional[ParentProfileData]:
        try:
            parent = ParentProfile.objects.select_related('user').prefetch_related('children').get(access_key=access_key)
            return ParentProfileSelector._serialize(parent)
        except ParentProfile.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_magic_token(token: str) -> Optional[ParentProfileData]:
        from .models import MagicLink
        try:
            magic_link = MagicLink.objects.select_related('parent').get(
                token=token, is_used=False, expires_at__gt=timezone.now()
            )
            return ParentProfileSelector._serialize(magic_link.parent)
        except MagicLink.DoesNotExist:
            return None
    
    @staticmethod
    def search_parents(query: str, status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        queryset = ParentProfile.objects.select_related('user')
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) | Q(last_name__icontains=query) |
                Q(email__icontains=query) | Q(phone__icontains=query)
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
        total_parents = ParentProfile.objects.count()
        child_count = ChildLink.objects.count()
        return {
            'total_parents': total_parents,
            'active_parents': ParentProfile.objects.filter(access_status=PortalAccessStatus.ACTIVE).count(),
            'pending_parents': ParentProfile.objects.filter(access_status=PortalAccessStatus.PENDING).count(),
            'inactive_parents': ParentProfile.objects.filter(access_status=PortalAccessStatus.INACTIVE).count(),
            'suspended_parents': ParentProfile.objects.filter(access_status=PortalAccessStatus.SUSPENDED).count(),
            'parents_with_users': ParentProfile.objects.filter(user__isnull=False).count(),
            'total_children': child_count,
            'avg_children_per_parent': child_count / total_parents if total_parents > 0 else 0,
        }
    
    @staticmethod
    def _serialize(parent: ParentProfile) -> ParentProfileData:
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


class ChildLinkSelector:
    @staticmethod
    def get_for_parent(parent_id: int) -> List[ChildLinkData]:
        links = ChildLink.objects.filter(parent_id=parent_id).select_related('parent').order_by('student_name')
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
        try:
            link = ChildLink.objects.get(parent_id=parent_id, student_id=student_id)
            return link.has_permission(feature)
        except ChildLink.DoesNotExist:
            return False


class MessageSelector:
    """Message read operations - parent-teacher messages, NOT notifications"""
    
    @staticmethod
    def get_conversations(parent_id: int, limit: int = 20) -> List[ConversationData]:
        student_ids = Message.objects.filter(
            Q(sender_parent_id=parent_id) | Q(recipient_parent_id=parent_id)
        ).values_list('student_id', flat=True).distinct()
        conversations = []
        for student_id in student_ids[:limit]:
            last_msg = Message.objects.filter(
                Q(sender_parent_id=parent_id) | Q(recipient_parent_id=parent_id),
                student_id=student_id
            ).select_related('sender_parent', 'recipient_parent').order_by('-sent_at').first()
            if last_msg:
                conversations.append({
                    'student_id': last_msg.student_id,
                    'student_name': last_msg.student_name,
                    'last_message': last_msg.body[:100],
                    'last_message_date': last_msg.sent_at.isoformat(),
                    'last_message_time_ago': MessageSelector._time_ago(last_msg.sent_at),
                    'unread_count': Message.objects.filter(
                        recipient_parent_id=parent_id,
                        student_id=last_msg.student_id,
                        is_read=False
                    ).count(),
                    'is_from_parent': last_msg.sender_parent_id == parent_id,
                })
        return conversations
    
    @staticmethod
    def get_messages_for_student(parent_id: int, student_id: int, limit: int = 50, offset: int = 0) -> List[MessageData]:
        messages = Message.objects.filter(
            Q(sender_parent_id=parent_id) | Q(recipient_parent_id=parent_id),
            student_id=student_id
        ).select_related('sender_parent', 'recipient_parent').order_by('-sent_at')[offset:offset+limit]
        return [
            {
                'id': msg.id,
                'subject': msg.subject,
                'body': msg.body,
                'sent_at': msg.sent_at.isoformat(),
                'time_ago': MessageSelector._time_ago(msg.sent_at),
                'is_from_parent': msg.sender_parent_id == parent_id,
                'sender_name': msg.sender_parent.full_name if msg.sender_parent else msg.sender_name or 'Teacher',
                'is_read': msg.is_read,
                'is_urgent': msg.is_urgent,
            }
            for msg in messages
        ]
    
    @staticmethod
    def get_unread_count_for_student(parent_id: int, student_id: int) -> int:
        return Message.objects.filter(
            recipient_parent_id=parent_id,
            student_id=student_id,
            is_read=False
        ).count()
    
    @staticmethod
    def _time_ago(timestamp):
        diff = timezone.now() - timestamp
        if diff.days > 30:
            return f"{diff.days // 30} months ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "just now"


class PortalDashboardSelector:
    """
    Aggregator for parent portal dashboard data
    Uses central notification selectors for notifications
    """
    
    @staticmethod
    def get_dashboard_data(parent_id: int) -> Dict[str, Any]:
        parent = ParentProfileSelector.get_by_id(parent_id)
        if not parent:
            return {}
        
        children = ChildLinkSelector.get_for_parent(parent_id)
        student_ids = [child['student_id'] for child in children]
        
        # Batch financial data
        financial_data = {}
        if student_ids:
            from apps.finance.selectors import InvoiceSelector, FinancialStatusSelector

        for student_id in student_ids:
            balance = InvoiceSelector.get_student_balance(student_id)
            financial_data[student_id] = {
                'financial': balance,
                'exam_clearance': FinancialStatusSelector.is_student_cleared_for_exams(student_id),
                'has_outstanding': balance['pending_count'] > 0,
            }
        


        # Use central notification selector
        notifications, total = CentralNotificationSelector.list_for_recipient(
            recipient_type='parent',
            recipient_id=parent_id,
            limit=10
        )
        unread_count = CentralNotificationSelector.get_unread_count(
            recipient_type='parent',
            recipient_id=parent_id
        )
        
        dashboard_data = {
            'parent': parent,
            'children': [],
            'notifications': notifications,
            'unread_notifications': unread_count,
            'recent_messages': MessageSelector.get_conversations(parent_id, limit=5),
        }
        
        for child in children:
            student_id = child['student_id']
            from apps.students.selectors import StudentSelector
            student = StudentSelector.get_by_id(student_id)
            if student:
                child_data = {'link': child, 'student': student}
                if student_id in financial_data:
                    child_data.update(financial_data[student_id])
                try:
                    from apps.admissions.selectors import ApplicationSelector
                    application = ApplicationSelector.get_by_student_id(student_id)
                    if application:
                        child_data['application'] = {
                            'status': application['status'],
                            'status_display': application['status_display'],
                            'application_number': application['application_number'],
                            'submitted_at': application.get('submitted_at'),
                        }
                except ImportError:
                    pass
                dashboard_data['children'].append(child_data)
        
        return dashboard_data
"""
Portal Service - Parent portal business logic
Handles profile creation, child linking, and portal access
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from typing import Optional, Dict, Any, List
import secrets
import logging
import uuid

from ..models import ParentProfile, ChildLink, PortalSession, ParentAccessLog
from ..constants import PortalAccessStatus, RelationshipType
from ..exceptions import (
    ParentNotFoundError,
    ChildNotFoundError,
    PortalAccessError,
    PortalAccountAlreadyExistsError,
)
from ..selectors import ParentProfileSelector, ChildLinkSelector

from apps.students.selectors import StudentSelector, GuardianSelector
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)
User = get_user_model()


class PortalService:
    """
    Parent portal business operations
    Single source of truth for parent portal management
    """
    
    @staticmethod
    @transaction.atomic
    def create_parent_profile(
        guardian_id: int,
        first_name: str,
        last_name: str,
        email: str,
        phone: str,
        alternate_phone: str = "",
        created_by_id: Optional[int] = None
    ) -> ParentProfile:
        """
        Create a parent portal profile from guardian data
        Usually called when guardian is created in students app
        """
        # Check if profile already exists
        existing = ParentProfile.objects.filter(guardian_id=guardian_id).first()
        if existing:
            logger.info(f"Parent profile already exists for guardian {guardian_id}")
            return existing
        
        # Create profile
        profile = ParentProfile.objects.create(
            guardian_id=guardian_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            alternate_phone=alternate_phone,
            access_status=PortalAccessStatus.PENDING,
            access_key=PortalService._generate_access_key(),
        )
        
        logger.info(f"Parent profile created for guardian {guardian_id}")
        return profile
    
    @staticmethod
    @transaction.atomic
    def link_child(
        parent_id: int,
        student_id: int,
        relationship: str,
        is_primary: bool = False,
        created_by_id: Optional[int] = None
    ) -> ChildLink:
        """
        Link a parent to a student (child)
        """
        # Get parent
        try:
            parent = ParentProfile.objects.get(id=parent_id)
        except ParentProfile.DoesNotExist:
            raise ParentNotFoundError(f"Parent profile {parent_id} not found")
        
        # Get student info
        student = StudentSelector.get_by_id(student_id)
        if not student:
            raise ChildNotFoundError(f"Student {student_id} not found")
        
        # Check if already linked
        existing = ChildLink.objects.filter(
            parent=parent,
            student_id=student_id
        ).first()
        
        if existing:
            logger.info(f"Child already linked to parent {parent_id}")
            return existing
        
        # Get relationship permissions
        from ..constants import PORTAL_FEATURES
        features = PORTAL_FEATURES.get(relationship, PORTAL_FEATURES[RelationshipType.OTHER])
        
        # Create link
        link = ChildLink.objects.create(
            parent=parent,
            student_id=student_id,
            student_name=student['full_name'],
            student_class=student['current_class']['display_name'],
            relationship=relationship,
            is_primary=is_primary,
            can_view_results='view_results' in features,
            can_view_attendance='view_attendance' in features,
            can_view_fees='view_fees' in features,
            can_make_payments='make_payments' in features,
            can_communicate='communicate' in features,
        )
        
        # If this is the first child, activate portal
        if parent.children.count() == 1:
            parent.access_status = PortalAccessStatus.ACTIVE
            parent.save(update_fields=['access_status'])
        
        logger.info(f"Child {student_id} linked to parent {parent_id}")
        return link
    
    @staticmethod
    @transaction.atomic
    def create_portal_user(
        parent_id: int,
        password: Optional[str] = None,
        send_welcome_email: bool = True,
        created_by_id: Optional[int] = None
    ) -> User:
        """
        Create Django user account for parent portal access
        """
        try:
            parent = ParentProfile.objects.get(id=parent_id)
        except ParentProfile.DoesNotExist:
            raise ParentNotFoundError(f"Parent profile {parent_id} not found")
        
        if parent.user:
            raise PortalAccountAlreadyExistsError(
                f"Portal account already exists for {parent.email}"
            )
        
        # Generate username
        username = PortalService._generate_username(parent)
        
        # Generate password if not provided
        if not password:
            password = PortalService._generate_password()
        
        # Create user
        user = User.objects.create_user(
            username=username,
            password=password,
            email=parent.email,
            first_name=parent.first_name,
            last_name=parent.last_name,
        )
        
        # Assign to parent group
        from django.contrib.auth.models import Group
        parent_group, _ = Group.objects.get_or_create(name='Parents')
        user.groups.add(parent_group)
        
        # Link to parent profile
        parent.user = user
        parent.access_status = PortalAccessStatus.ACTIVE
        parent.save(update_fields=['user', 'access_status'])
        
        # Send welcome email if requested
        if send_welcome_email:
            PortalService._send_welcome_email(parent, user, password)
        
        # Log the action
        SystemLogService.log_action(
            user_id=created_by_id,
            action=SystemLog.ActionType.CREATE,
            app_label=SystemLog.AppLabel.PARENTS,
            model_name='User',
            object_id=str(user.id),
            object_repr=username,
            changes={
                'parent_id': parent.id,
                'email': parent.email,
                'action': 'portal_account_created'
            }
        )
        
        logger.info(f"Portal user created for parent {parent_id}")
        return user
    
    @staticmethod
    @transaction.atomic
    def create_portal_session(
        parent_id: int,
        ip_address: str,
        user_agent: str = "",
        expires_in_hours: int = 24
    ) -> PortalSession:
        """
        Create a new portal session (magic link style)
        """
        try:
            parent = ParentProfile.objects.get(id=parent_id)
        except ParentProfile.DoesNotExist:
            raise ParentNotFoundError(f"Parent profile {parent_id} not found")
        
        # Deactivate old sessions
        PortalSession.objects.filter(
            parent=parent,
            is_active=True
        ).update(is_active=False)
        
        # Create new session
        session = PortalSession.objects.create(
            parent=parent,
            session_key=uuid.uuid4().hex,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=timezone.now() + timezone.timedelta(hours=expires_in_hours)
        )
        
        logger.info(f"Portal session created for parent {parent_id}")
        return session
    
    @staticmethod
    def validate_session(session_key: str) -> Optional[ParentProfile]:
        """
        Validate a portal session and return parent profile if valid
        """
        try:
            session = PortalSession.objects.select_related('parent').get(
                session_key=session_key,
                is_active=True,
                expires_at__gt=timezone.now()
            )
            
            # Update last activity
            session.save()  # auto_now updates last_activity
            
            return session.parent
            
        except PortalSession.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def log_parent_action(
        parent_id: int,
        action: str,
        ip_address: str,
        user_agent: str = "",
        student_id: Optional[int] = None
    ) -> ParentAccessLog:
        """
        Log parent portal access for audit
        """
        try:
            parent = ParentProfile.objects.get(id=parent_id)
        except ParentProfile.DoesNotExist:
            raise ParentNotFoundError(f"Parent profile {parent_id} not found")
        
        log = ParentAccessLog.objects.create(
            parent=parent,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            student_id=student_id
        )
        
        return log
    
    @staticmethod
    def verify_child_access(
        parent_id: int,
        student_id: int,
        feature: str
    ) -> bool:
        """
        Verify if parent has access to a specific feature for a child
        """
        return ChildLinkSelector.verify_access(parent_id, student_id, feature)
    
    @staticmethod
    def _generate_access_key() -> str:
        """Generate unique access key for magic links"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def _generate_username(parent: ParentProfile) -> str:
        """Generate unique username for parent"""
        base = f"parent_{parent.id}"
        username = base
        
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        
        return username
    
    @staticmethod
    def _generate_password(length: int = 10) -> str:
        """Generate secure random password"""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def _send_welcome_email(parent: ParentProfile, user: User, password: str):
        """Send welcome email with login credentials"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f"Welcome to the Parent Portal - {settings.COMPANY_NAME}"
        message = f"""
        Dear {parent.full_name},
        
        Your parent portal account has been created.
        
        Login Details:
        Username: {user.username}
        Password: {password}
        
        Portal URL: {settings.PARENT_PORTAL_URL}
        
        You can access:
        • View your children's academic results
        • Check attendance records
        • View fee statements and make payments
        • Communicate with teachers
        • Receive important notifications
        
        For security, please change your password after first login.
        
        Regards,
        School Administration
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[parent.email],
            fail_silently=True,
        )
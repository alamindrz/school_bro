"""
Access Service - Parent portal access control and magic links
"""

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from typing import Optional
import logging

from ..models import ParentProfile, PortalSession
from ..exceptions import ParentNotFoundError, PortalAccessError
from .portal import PortalService

logger = logging.getLogger(__name__)


class AccessService:
    """
    Parent portal access management
    Handles magic links, login tracking, and access control
    """
    
    @classmethod
    def generate_magic_link(cls, parent_id: int, ip_address: str) -> str:
        """
        Generate a magic link for parent portal access
        Returns the full URL with access key
        """
        try:
            parent = ParentProfile.objects.get(id=parent_id)
        except ParentProfile.DoesNotExist:
            raise ParentNotFoundError(f"Parent {parent_id} not found")
        
        # Create session
        session = PortalService.create_portal_session(
            parent_id=parent_id,
            ip_address=ip_address
        )
        
        # Build magic link URL
        base_url = getattr(settings, 'PARENT_PORTAL_URL', 'http://localhost:8000/parents')
        magic_link = f"{base_url}/access/{session.session_key}/"
        
        logger.info(f"Magic link generated for parent {parent_id}")
        return magic_link
    
    @classmethod
    def send_magic_link_email(cls, parent_id: int, ip_address: str) -> bool:
        """
        Generate and email a magic link to the parent
        """
        try:
            parent = ParentProfile.objects.get(id=parent_id)
        except ParentProfile.DoesNotExist:
            raise ParentNotFoundError(f"Parent {parent_id} not found")
        
        # Generate magic link
        magic_link = cls.generate_magic_link(parent_id, ip_address)
        
        # Send email
        subject = "Your Parent Portal Access Link"
        message = f"""
        Dear {parent.full_name},
        
        Click the link below to access the Parent Portal:
        {magic_link}
        
        This link will expire in 24 hours.
        
        If you didn't request this, please ignore this email.
        
        Regards,
        School Administration
        """
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[parent.email],
                fail_silently=False,
            )
            
            logger.info(f"Magic link email sent to {parent.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send magic link email: {e}")
            return False
    
    @classmethod
    def validate_magic_link(cls, session_key: str, ip_address: str) -> Optional[ParentProfile]:
        """
        Validate a magic link and log access
        """
        parent = PortalService.validate_session(session_key)
        
        if parent:
            # Log the access
            PortalService.log_parent_action(
                parent_id=parent.id,
                action='MAGIC_LINK_LOGIN',
                ip_address=ip_address
            )
            
            # Update last login
            parent.record_login()
            
            logger.info(f"Parent {parent.id} logged in via magic link")
        
        return parent
    
    @classmethod
    def validate_password_login(
        cls,
        username: str,
        password: str,
        ip_address: str
    ) -> Optional[ParentProfile]:
        """
        Validate username/password login
        """
        from django.contrib.auth import authenticate
        
        user = authenticate(username=username, password=password)
        
        if user and hasattr(user, 'parent_profile'):
            parent = user.parent_profile
            
            # Log the access
            PortalService.log_parent_action(
                parent_id=parent.id,
                action='PASSWORD_LOGIN',
                ip_address=ip_address
            )
            
            # Update last login
            parent.record_login()
            
            logger.info(f"Parent {parent.id} logged in via password")
            return parent
        
        return None
    
    @classmethod
    def logout(cls, session_key: str) -> bool:
        """
        Invalidate a portal session
        """
        try:
            session = PortalSession.objects.get(
                session_key=session_key,
                is_active=True
            )
            session.is_active = False
            session.save(update_fields=['is_active'])
            
            logger.info(f"Session {session_key} invalidated")
            return True
            
        except PortalSession.DoesNotExist:
            return False
    
    @classmethod
    def get_active_sessions(cls, parent_id: int) -> int:
        """
        Get count of active sessions for a parent
        """
        return PortalSession.objects.filter(
            parent_id=parent_id,
            is_active=True,
            expires_at__gt=timezone.now()
        ).count()
    
    @classmethod
    def revoke_all_sessions(cls, parent_id: int) -> int:
        """
        Revoke all active sessions for a parent
        """
        count = PortalSession.objects.filter(
            parent_id=parent_id,
            is_active=True
        ).update(is_active=False)
        
        logger.info(f"Revoked {count} sessions for parent {parent_id}")
        return count
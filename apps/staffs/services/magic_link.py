"""
Magic Link Service - Passwordless login for staff
"""

import uuid
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from ..models import Staff


class MagicLinkService:
    """Handle passwordless login via magic links"""
    
    LINK_EXPIRY_MINUTES = 15
    
    @classmethod
    def send_magic_link(cls, staff: Staff) -> bool:
        """Send magic link email for passwordless login"""
        # Generate session token
        from ..models import PortalSession
        session = PortalSession.objects.create(
            staff=staff,
            expires_at=timezone.now() + timedelta(minutes=cls.LINK_EXPIRY_MINUTES)
        )
        
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        magic_url = f"{base_url}{reverse('staffs:magic_link_login', kwargs={'token': session.token})}"
        
        subject = f"Login link for {settings.COMPANY_NAME} Staff Portal"
        message = f"""
        Hello {staff.get_full_name},
        
        Click the link below to login to the staff portal:
        {magic_url}
        
        This link expires in {cls.LINK_EXPIRY_MINUTES} minutes.
        
        If you didn't request this, please ignore this email.
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[staff.email],
            fail_silently=False,
        )
        
        return True
"""
Staff Invite Service - Secure staff onboarding
"""

import uuid
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.contrib.auth import get_user_model
import logging

from ..models import Staff

User = get_user_model()
logger = logging.getLogger(__name__)


class StaffInviteService:
    """Handle secure staff onboarding via invite links"""
    
    INVITE_EXPIRY_DAYS = 7
    
    @classmethod
    def send_invite(cls, staff_id: int, invited_by_id: int = None) -> bool:
        """Send invite email to staff member"""
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from datetime import datetime
        
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            logger.error(f"Staff {staff_id} not found")
            return False
        
        # Generate new invite token
        staff.invite_token = uuid.uuid4()
        staff.invite_sent_at = timezone.now()
        staff.invite_expires_at = timezone.now() + timedelta(days=cls.INVITE_EXPIRY_DAYS)
        staff.save(update_fields=['invite_token', 'invite_sent_at', 'invite_expires_at'])
        
        # Build invite URL
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        invite_url = f"{base_url}{reverse('staffs:accept_invite', kwargs={'token': staff.invite_token})}"
        
        # Prepare email content
        context = {
            'company_name': getattr(settings, 'COMPANY_NAME', 'DETs Toolkit'),
            'staff_name': staff.get_full_name,
            'invite_url': invite_url,
            'expiry_days': cls.INVITE_EXPIRY_DAYS,
            'year': datetime.now().year,
        }
        
        html_message = render_to_string('staffs/email/invite_email.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=f"Invitation to join {context['company_name']} Staff Portal",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[staff.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Invite sent to {staff.email}")
        return True
    
    
    @classmethod
    def accept_invite(cls, token: str, password: str = None) -> tuple:
        """Accept invite and create user account"""
        try:
            staff = Staff.objects.get(invite_token=token)
        except Staff.DoesNotExist:
            return None, "Invalid or expired invitation link"
        
        # Check if already accepted
        if staff.user:
            return staff.user, None
        
        # Check if expired
        if staff.invite_expires_at and staff.invite_expires_at < timezone.now():
            return None, "Invitation link has expired. Please request a new one."
        
        # Generate a username from staff_id
        username = staff.staff_id.lower()
        
        # Create user account
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Generate a temporary password if none provided (for magic link)
        if not password:
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for _ in range(12))
        
        user = User.objects.create_user(
            username=username,
            email=staff.email,
            password=password,
            first_name=staff.first_name,
            last_name=staff.last_name,
            is_staff=True
        )
        
        staff.user = user
        staff.invite_accepted_at = timezone.now()
        staff.is_active = True
        staff.save(update_fields=['user', 'invite_accepted_at', 'is_active'])
        
        logger.info(f"Staff {staff.staff_id} accepted invite and created account")
        return user, None
    
        
    @classmethod
    def resend_invite(cls, staff_id: int) -> bool:
        """Resend invite email"""
        return cls.send_invite(staff_id)
    
    @classmethod
    def is_invite_valid(cls, token: str) -> bool:
        """Check if invite token is valid"""
        try:
            staff = Staff.objects.get(invite_token=token)
            if staff.user:
                return False
            if staff.invite_expires_at and staff.invite_expires_at < timezone.now():
                return False
            return True
        except Staff.DoesNotExist:
            return False
"""
Student User Account Integration Service
DEPENDS ON: students/exceptions.py, students/models.py, corecode/services/logging.py
"""

import secrets
import string
from typing import Optional, Tuple
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog
from ..exceptions import (
    StudentUserError,
    StudentUserAlreadyExistsError,
    ParentPortalAccessError,
    StudentNotFoundError,
)
from ..models import Student, Guardian

User = get_user_model()


class StudentUserService:
    """
    Service for creating and managing student user accounts.
    This is the ONLY place where student-linked User accounts are created.
    """
    
    DEFAULT_STUDENT_GROUP = 'Students'
    DEFAULT_PARENT_GROUP = 'Parents'
    
    @classmethod
    @transaction.atomic
    def create_user_for_student(
        cls,
        student: Student,
        password: Optional[str] = None,
        send_welcome_email: bool = True,
        created_by_id: Optional[int] = None
    ) -> User:
        """
        Create a Django user account for a student.
        
        Args:
            student: Student instance
            password: Optional password (auto-generated if not provided)
            send_welcome_email: Whether to send welcome email
            created_by_id: User ID performing the action
            
        Returns:
            User: Created user instance
            
        Raises:
            StudentUserAlreadyExistsError: If user already exists
            StudentNotFoundError: If student doesn't exist
        """
        # Check if user already exists
        if student.user:
            raise StudentUserAlreadyExistsError(
                f"Student {student.admission_number} already has user account: {student.user.username}"
            )
        
        # Generate username
        username = cls._generate_username(student)
        
        # Generate password if not provided
        if not password:
            password = cls._generate_password()
        
        # Create user
        user = User.objects.create_user(
            username=username,
            password=password,
            email=student.email or '',
            first_name=student.first_name,
            last_name=student.last_name,
        )
        
        # Assign to student group
        student_group, _ = Group.objects.get_or_create(name=cls.DEFAULT_STUDENT_GROUP)
        user.groups.add(student_group)
        
        # Link to student
        student.user = user
        student.save(update_fields=['user'])
        
        # Log the action
        SystemLogService.log_action(
            user_id=created_by_id,
            action=SystemLog.ActionType.CREATE,
            app_label=SystemLog.AppLabel.STUDENTS,
            model_name='User',
            object_id=str(user.id),
            object_repr=username,
            changes={
                'student_id': student.id,
                'admission_number': student.admission_number,
                'username': username,
            }
        )
        
        # Send welcome email
        if send_welcome_email and student.email:
            cls._send_welcome_email(student, user, password)
        
        return user
    
    @classmethod
    @transaction.atomic
    def create_parent_portal_account(
        cls,
        guardian: Guardian,
        password: Optional[str] = None,
        send_welcome_email: bool = True,
        created_by_id: Optional[int] = None
    ) -> User:
        """
        Create a parent portal account for a guardian.
        
        Args:
            guardian: Guardian instance
            password: Optional password (auto-generated if not provided)
            send_welcome_email: Whether to send welcome email
            created_by_id: User ID performing the action
            
        Returns:
            User: Created user instance
        """
        # Generate username from guardian email or phone
        if guardian.email:
            username = cls._generate_username_from_email(guardian.email)
        else:
            username = f"parent_{guardian.phone}_{guardian.student.admission_number}"
        
        # Generate password if not provided
        if not password:
            password = cls._generate_password()
        
        # Create user
        user = User.objects.create_user(
            username=username,
            password=password,
            email=guardian.email or '',
            first_name=guardian.first_name,
            last_name=guardian.last_name,
        )
        
        # Assign to parent group
        parent_group, _ = Group.objects.get_or_create(name=cls.DEFAULT_PARENT_GROUP)
        user.groups.add(parent_group)
        
        # Store guardian ID in user profile (would need Profile model extension)
        # For now, we'll use a simple User attribute
        user.guardian_id = guardian.id
        user.save()
        
        # Log the action
        SystemLogService.log_action(
            user_id=created_by_id,
            action=SystemLog.ActionType.CREATE,
            app_label=SystemLog.AppLabel.STUDENTS,
            model_name='User',
            object_id=str(user.id),
            object_repr=username,
            changes={
                'guardian_id': guardian.id,
                'student_id': guardian.student.id,
                'username': username,
            }
        )
        
        # Send welcome email
        if send_welcome_email and guardian.email:
            cls._send_parent_welcome_email(guardian, user, password)
        
        return user
    
    @classmethod
    def reset_password(cls, user_id: int, reset_by_id: Optional[int] = None) -> str:
        """
        Reset user password and return new password.
        Used for password reset functionality.
        """
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise StudentUserError(f"User with id {user_id} not found")
        
        new_password = cls._generate_password()
        user.set_password(new_password)
        user.save()
        
        # Log password reset
        SystemLogService.log_action(
            user_id=reset_by_id,
            action=SystemLog.ActionType.UPDATE,
            app_label=SystemLog.AppLabel.STUDENTS,
            model_name='User',
            object_id=str(user.id),
            object_repr=user.username,
            changes={'action': 'password_reset'}
        )
        
        return new_password
    
    @staticmethod
    def _generate_username(student: Student) -> str:
        """Generate unique username for student"""
        base = f"{student.admission_number.lower()}"
        username = base
        
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        
        return username
    
    @staticmethod
    def _generate_username_from_email(email: str) -> str:
        """Generate username from email address"""
        base = email.split('@')[0]
        username = base
        
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        
        return username
    
    @staticmethod
    def _generate_password(length: int = 10) -> str:
        """Generate secure random password"""
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    @staticmethod
    def _send_welcome_email(student: Student, user: User, password: str):
        """Send welcome email with login credentials"""
        subject = f"Welcome to {getattr(settings, 'COMPANY_NAME', 'School Portal')}"
        message = f"""
        Dear {student.get_full_name},
        
        Your student portal account has been created.
        
        Username: {user.username}
        Password: {password}
        
        Please login at: {getattr(settings, 'PORTAL_URL', 'http://localhost:8000')}
        
        We recommend changing your password after first login.
        
        Regards,
        School Administration
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            fail_silently=True,
        )
    
    @staticmethod
    def _send_parent_welcome_email(guardian: Guardian, user: User, password: str):
        """Send welcome email to parent/guardian"""
        subject = f"Parent Portal Access - {guardian.student.get_full_name}"
        message = f"""
        Dear {guardian.get_full_name},
        
        You have been granted parent portal access for {guardian.student.get_full_name}.
        
        Username: {user.username}
        Password: {password}
        
        Login at: {getattr(settings, 'PORTAL_URL', 'http://localhost:8000')}
        
        You can view your child's academic progress, attendance, and fee statements.
        
        Regards,
        School Administration
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[guardian.email],
            fail_silently=True,
        )
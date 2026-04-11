"""
Portal Sync Service - Syncs enrollment data to parent portal
Called by admissions app when a student is enrolled
"""

import logging
from django.db import transaction
from django.utils import timezone
from typing import Dict, Any, Optional

from ..models import ParentProfile, ChildLink
from ..constants import PortalAccessStatus, RelationshipType
from .notification import NotificationService

logger = logging.getLogger(__name__)


class PortalSyncService:
    """
    Sync enrollment data from admissions to parent portal.
    This is the ONLY bridge between admissions and parents apps.
    """
    
    @staticmethod
    @transaction.atomic
    def sync_from_enrollment(
        application,
        student,
        guardian_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create or update parent profile and child link after enrollment.
        
        Args:
            application: Application model instance
            student: Student model instance  
            guardian_info: Dict with guardian details
        
        Returns:
            Dict with sync result or None if failed
        """
        try:
            logger.info(f"Starting portal sync for student {student.id}, application {application.application_number}")
            
            # Find or create parent profile by email
            parent_email = guardian_info.get('email', '')
            parent_phone = guardian_info.get('phone', '')
            
            parent = None
            
            # Try to find by email first
            if parent_email:
                parent = ParentProfile.objects.filter(email=parent_email).first()
            
            # If not found by email, try by phone
            if not parent and parent_phone:
                parent = ParentProfile.objects.filter(phone=parent_phone).first()
            
            # Create new parent profile if not found
            if not parent:
                parent = ParentProfile.objects.create(
                    first_name=guardian_info.get('first_name', ''),
                    last_name=guardian_info.get('last_name', ''),
                    email=parent_email,
                    phone=parent_phone,
                    guardian_id=None,  # Will be updated if we have guardian ID from students app
                    access_status=PortalAccessStatus.ACTIVE,
                    notification_preferences={}  # Will use defaults
                )
                logger.info(f"Created new parent profile: {parent.full_name} (ID: {parent.id})")
            else:
                # Update existing parent profile with latest info
                updated = False
                if guardian_info.get('first_name') and parent.first_name != guardian_info['first_name']:
                    parent.first_name = guardian_info['first_name']
                    updated = True
                if guardian_info.get('last_name') and parent.last_name != guardian_info['last_name']:
                    parent.last_name = guardian_info['last_name']
                    updated = True
                if guardian_info.get('phone') and parent.phone != guardian_info['phone']:
                    parent.phone = guardian_info['phone']
                    updated = True
                if guardian_info.get('address') and not parent.address:
                    parent.address = guardian_info['address']
                    updated = True
                
                if updated:
                    parent.save()
                    logger.info(f"Updated existing parent profile: {parent.full_name} (ID: {parent.id})")
            
            # Create or update child link
            child_link, created = ChildLink.objects.get_or_create(
                parent=parent,
                student_id=student.id,
                defaults={
                    'student_name': student.get_full_name,
                    'student_class': student.current_class.display_name if hasattr(student, 'current_class') else '',
                    'relationship': guardian_info.get('relationship', RelationshipType.GUARDIAN),
                    'is_primary': True,
                    'can_view_results': True,
                    'can_view_attendance': True,
                    'can_view_fees': True,
                    'can_make_payments': True,
                    'can_communicate': True,
                }
            )
            
            if not created:
                # Update existing child link
                child_link.student_name = student.get_full_name
                if hasattr(student, 'current_class'):
                    child_link.student_class = student.current_class.display_name
                child_link.save(update_fields=['student_name', 'student_class', 'updated_at'])
                logger.info(f"Updated existing child link for student {student.id}")
            else:
                logger.info(f"Created new child link for student {student.id}")
            
            # Send welcome notification to parent
            try:
                NotificationService.send_application_status_notification(
                    parent=parent,
                    student=student,
                    status='enrolled',
                    application_number=application.application_number
                )
                logger.info(f"Sent welcome notification to parent {parent.id}")
            except Exception as e:
                # Don't fail sync if notification fails
                logger.warning(f"Failed to send welcome notification: {e}")
            
            return {
                'success': True,
                'parent_id': parent.id,
                'child_link_id': child_link.id,
                'created': created,
            }
            
        except Exception as e:
            logger.error(f"Portal sync failed for student {student.id}: {e}")
            # Don't raise - enrollment should succeed even if portal sync fails
            return None
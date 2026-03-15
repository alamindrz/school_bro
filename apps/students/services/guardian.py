"""
Guardian Service Layer
All guardian write operations - SINGLE SOURCE OF TRUTH
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from typing import Optional, Dict, Any
import logging

from ..models import Guardian, Student
from ..exceptions import (
    GuardianError,
    GuardianLimitExceededError,
    PrimaryGuardianRequiredError,
    StudentNotFoundError
)
from ..validators import GuardianValidator
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class GuardianService:
    """
    Guardian business operations.
    This is the ONLY place where Guardian objects are created/updated.
    """
    
    @staticmethod
    @transaction.atomic
    def create_guardian(
        student_id: int,
        first_name: str,
        last_name: str,
        relationship: str,
        phone: str,
        email: Optional[str] = None,
        alternate_phone: Optional[str] = None,
        address: Optional[str] = None,
        occupation: Optional[str] = None,
        employer: Optional[str] = None,
        is_primary: bool = False,
        is_emergency_contact: bool = True,
        created_by_id: Optional[int] = None
    ) -> Guardian:
        """
        Create a new guardian for a student.
        
        Args:
            student_id: ID of the student
            first_name: Guardian's first name
            last_name: Guardian's last name
            relationship: Relationship to student (father, mother, etc.)
            phone: Primary phone number
            email: Email address (optional)
            alternate_phone: Alternate phone number (optional)
            address: Physical address (optional)
            occupation: Occupation (optional)
            employer: Employer (optional)
            is_primary: Whether this is a primary guardian
            is_emergency_contact: Whether this is an emergency contact
            created_by_id: User ID creating the guardian
            
        Returns:
            Guardian: Created guardian instance
            
        Raises:
            StudentNotFoundError: If student doesn't exist
            GuardianLimitExceededError: If too many guardians
            PrimaryGuardianRequiredError: If too many primary guardians
        """
        # Get student
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            raise StudentNotFoundError(f"Student with id {student_id} not found")
        
        # Check guardian limit
        current_count = student.guardians.count()
        GuardianValidator.validate_guardian_limit(current_count)
        
        # Check primary guardian limit
        current_primary_count = student.guardians.filter(is_primary=True).count()
        GuardianValidator.validate_primary_guardian_count(current_primary_count, is_primary)
        
        # Validate relationship
        GuardianValidator.validate_relationship(relationship)
        
        # Create guardian
        guardian = Guardian.objects.create(
            student=student,
            first_name=first_name,
            last_name=last_name,
            relationship=relationship,
            email=email or '',
            phone=phone,
            alternate_phone=alternate_phone or '',
            address=address or '',
            occupation=occupation or '',
            employer=employer or '',
            is_primary=is_primary,
            is_emergency_contact=is_emergency_contact
        )
        
        # If this is the first guardian, automatically make them primary
        if current_count == 0 and not is_primary:
            guardian.is_primary = True
            guardian.save(update_fields=['is_primary'])
        
        # Log the action
        SystemLogService.log_action(
            user_id=created_by_id,
            action=SystemLog.ActionType.CREATE,
            app_label=SystemLog.AppLabel.STUDENTS,
            model_name='Guardian',
            object_id=str(guardian.id),
            object_repr=guardian.get_full_name,
            changes={
                'student_id': student.id,
                'student_name': str(student),
                'relationship': relationship,
                'is_primary': guardian.is_primary
            }
        )
        
        logger.info(f"Guardian created for student {student.admission_number}: {guardian.get_full_name}")
        return guardian
    
    @staticmethod
    @transaction.atomic
    def update_guardian(
        guardian_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        relationship: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        alternate_phone: Optional[str] = None,
        address: Optional[str] = None,
        occupation: Optional[str] = None,
        employer: Optional[str] = None,
        is_primary: Optional[bool] = None,
        is_emergency_contact: Optional[bool] = None,
        updated_by_id: Optional[int] = None
    ) -> Guardian:
        """
        Update an existing guardian.
        
        Args:
            guardian_id: ID of the guardian to update
            Various fields to update (only provided fields are updated)
            updated_by_id: User ID performing the update
            
        Returns:
            Guardian: Updated guardian instance
            
        Raises:
            GuardianError: If guardian doesn't exist
            PrimaryGuardianRequiredError: If primary guardian limit would be exceeded
        """
        try:
            guardian = Guardian.objects.select_related('student').get(id=guardian_id)
        except Guardian.DoesNotExist:
            raise GuardianError(f"Guardian with id {guardian_id} not found")
        
        changes = {}
        
        # Update fields if provided
        if first_name is not None and first_name != guardian.first_name:
            changes['first_name'] = {'old': guardian.first_name, 'new': first_name}
            guardian.first_name = first_name
        
        if last_name is not None and last_name != guardian.last_name:
            changes['last_name'] = {'old': guardian.last_name, 'new': last_name}
            guardian.last_name = last_name
        
        if relationship is not None and relationship != guardian.relationship:
            GuardianValidator.validate_relationship(relationship)
            changes['relationship'] = {'old': guardian.relationship, 'new': relationship}
            guardian.relationship = relationship
        
        if phone is not None and phone != guardian.phone:
            changes['phone'] = {'old': guardian.phone, 'new': phone}
            guardian.phone = phone
        
        if email is not None and email != guardian.email:
            changes['email'] = {'old': guardian.email, 'new': email}
            guardian.email = email
        
        if alternate_phone is not None and alternate_phone != guardian.alternate_phone:
            changes['alternate_phone'] = {'old': guardian.alternate_phone, 'new': alternate_phone}
            guardian.alternate_phone = alternate_phone
        
        if address is not None and address != guardian.address:
            changes['address'] = {'old': guardian.address, 'new': address}
            guardian.address = address
        
        if occupation is not None and occupation != guardian.occupation:
            changes['occupation'] = {'old': guardian.occupation, 'new': occupation}
            guardian.occupation = occupation
        
        if employer is not None and employer != guardian.employer:
            changes['employer'] = {'old': guardian.employer, 'new': employer}
            guardian.employer = employer
        
        # Handle primary guardian changes with validation
        if is_primary is not None and is_primary != guardian.is_primary:
            if is_primary:
                # Check primary guardian limit
                current_primary_count = guardian.student.guardians.filter(
                    is_primary=True
                ).exclude(id=guardian.id).count()
                GuardianValidator.validate_primary_guardian_count(current_primary_count, True)
            
            changes['is_primary'] = {'old': guardian.is_primary, 'new': is_primary}
            guardian.is_primary = is_primary
        
        if is_emergency_contact is not None and is_emergency_contact != guardian.is_emergency_contact:
            changes['is_emergency_contact'] = {
                'old': guardian.is_emergency_contact,
                'new': is_emergency_contact
            }
            guardian.is_emergency_contact = is_emergency_contact
        
        if changes:
            guardian.save()
            
            # Log the update
            SystemLogService.log_action(
                user_id=updated_by_id,
                action=SystemLog.ActionType.UPDATE,
                app_label=SystemLog.AppLabel.STUDENTS,
                model_name='Guardian',
                object_id=str(guardian.id),
                object_repr=guardian.get_full_name,
                changes=changes
            )
            
            logger.info(f"Guardian {guardian.id} updated")
        
        return guardian
    
    @staticmethod
    @transaction.atomic
    def delete_guardian(
        guardian_id: int,
        deleted_by_id: Optional[int] = None
    ) -> bool:
        """
        Delete a guardian.
        
        Args:
            guardian_id: ID of the guardian to delete
            deleted_by_id: User ID performing the deletion
            
        Returns:
            bool: True if deleted
            
        Raises:
            GuardianError: If guardian doesn't exist
            PrimaryGuardianRequiredError: If deleting the last primary guardian
        """
        try:
            guardian = Guardian.objects.select_related('student').get(id=guardian_id)
        except Guardian.DoesNotExist:
            raise GuardianError(f"Guardian with id {guardian_id} not found")
        
        # Check if this is the only primary guardian
        if guardian.is_primary:
            other_primary_count = guardian.student.guardians.filter(
                is_primary=True
            ).exclude(id=guardian.id).count()
            
            if other_primary_count == 0:
                # Check if there are other guardians that could become primary
                other_guardians = guardian.student.guardians.exclude(id=guardian.id)
                if other_guardians.exists():
                    # Automatically make the first other guardian primary
                    new_primary = other_guardians.first()
                    new_primary.is_primary = True
                    new_primary.save(update_fields=['is_primary'])
                else:
                    raise PrimaryGuardianRequiredError(
                        "Cannot delete the only guardian. At least one guardian is required."
                    )
        
        # Store info for logging
        guardian_info = {
            'id': guardian.id,
            'name': guardian.get_full_name,
            'student_id': guardian.student.id,
            'student_name': str(guardian.student)
        }
        
        guardian.delete()
        
        # Log the deletion
        SystemLogService.log_action(
            user_id=deleted_by_id,
            action=SystemLog.ActionType.DELETE,
            app_label=SystemLog.AppLabel.STUDENTS,
            model_name='Guardian',
            object_id=str(guardian_id),
            object_repr=guardian_info['name'],
            changes={'deleted_guardian': guardian_info}
        )
        
        logger.info(f"Guardian {guardian_id} deleted")
        return True
    
    @staticmethod
    def set_primary_guardian(
        guardian_id: int,
        updated_by_id: Optional[int] = None
    ) -> Guardian:
        """
        Set a guardian as the primary guardian.
        
        Args:
            guardian_id: ID of the guardian to set as primary
            updated_by_id: User ID performing the action
            
        Returns:
            Guardian: Updated guardian instance
        """
        try:
            guardian = Guardian.objects.select_related('student').get(id=guardian_id)
        except Guardian.DoesNotExist:
            raise GuardianError(f"Guardian with id {guardian_id} not found")
        
        with transaction.atomic():
            # Remove primary status from all other guardians
            guardian.student.guardians.filter(is_primary=True).exclude(
                id=guardian.id
            ).update(is_primary=False)
            
            # Set this guardian as primary
            guardian.is_primary = True
            guardian.save(update_fields=['is_primary'])
        
        # Log the action
        SystemLogService.log_action(
            user_id=updated_by_id,
            action=SystemLog.ActionType.UPDATE,
            app_label=SystemLog.AppLabel.STUDENTS,
            model_name='Guardian',
            object_id=str(guardian.id),
            object_repr=guardian.get_full_name,
            changes={'action': 'set_as_primary_guardian'}
        )
        
        return guardian
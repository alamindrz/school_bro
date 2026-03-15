"""
Academic Session and Term Services
Business logic for managing academic sessions and terms
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, List, Dict, Any
from datetime import date

from ..models import AcademicSession, AcademicTerm
from ..selectors import AcademicSessionSelector, AcademicTermSelector
from ..exceptions import (
    NoActiveSessionError,
    NoActiveTermError,
    AcademicStructureError,
    SessionNotFoundError,
    TermNotFoundError,
    InvalidClassProgressionError,
)
from ..constants import TermType


class AcademicSessionService:
    """
    Academic Session business operations
    Manages the lifecycle of academic sessions
    """
    
    @staticmethod
    @transaction.atomic
    def create_session(
        name: str,
        code: str,
        start_date: date,
        end_date: date,
        is_current: bool = False,
        created_by=None
    ) -> AcademicSession:
        """
        Create a new academic session
        
        Args:
            name: Display name (e.g., "2024/2025")
            code: Short code (e.g., "202425")
            start_date: Session start date
            end_date: Session end date
            is_current: Whether this is the current session
            created_by: User creating the session
            
        Returns:
            AcademicSession: Created session instance
            
        Raises:
            ValidationError: If session dates are invalid
        """
        # Validate dates
        if start_date >= end_date:
            raise ValidationError("Start date must be before end date")
        
        # Check for overlapping dates
        overlapping = AcademicSession.objects.filter(
            start_date__lte=end_date,
            end_date__gte=start_date
        ).exclude(pk=None)
        
        if overlapping.exists():
            raise ValidationError(
                "Session dates overlap with existing session: "
                f"{overlapping.first().name}"
            )
        
        # Create session
        session = AcademicSession(
            name=name,
            code=code,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current
        )
        session.full_clean()
        session.save()
        
        # Automatically create terms for this session
        AcademicTermService.create_terms_for_session(session, created_by)
        
        # If this is current session, ensure others are not current
        if is_current:
            AcademicSession.objects.exclude(pk=session.pk).update(is_current=False)
        
        return session
    
    @staticmethod
    @transaction.atomic
    def set_current_session(session_id: int, updated_by=None) -> AcademicSession:
        """
        Set a specific session as the current session
        
        Args:
            session_id: ID of session to set as current
            updated_by: User performing the action
            
        Returns:
            AcademicSession: Updated session instance
            
        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        try:
            # Clear current flag from all sessions
            AcademicSession.objects.filter(is_current=True).update(is_current=False)
            
            # Set new current session
            session = AcademicSession.objects.get(id=session_id)
            session.is_current = True
            session.save(update_fields=['is_current'])
            
            # Also set first term as current by default
            first_term = session.terms.order_by('term').first()
            if first_term:
                AcademicTermService.set_current_term(first_term.id, updated_by)
            
            return session
            
        except AcademicSession.DoesNotExist:
            raise SessionNotFoundError(f"Session with id {session_id} not found")
    
    @staticmethod
    @transaction.atomic
    def archive_session(session_id: int) -> None:
        """
        Archive a session - mark as not current
        
        Args:
            session_id: ID of session to archive
            
        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        try:
            session = AcademicSession.objects.get(id=session_id)
            session.is_current = False
            session.save(update_fields=['is_current'])
            
            # Also archive its terms
            session.terms.update(is_current=False)
            
        except AcademicSession.DoesNotExist:
            raise SessionNotFoundError(f"Session with id {session_id} not found")
    
    @staticmethod
    def get_or_create_current_session() -> AcademicSession:
        """
        Get current session or create a default one if none exists
        
        Returns:
            AcademicSession: Current or newly created session
        """
        current = AcademicSessionSelector.get_current_session()
        if current:
            return current
        
        # Create default session
        today = timezone.now().date()
        year = today.year
        
        return AcademicSessionService.create_session(
            name=f"{year}/{year + 1}",
            code=f"{year}{year + 1}",
            start_date=date(year, 9, 1),  # Nigerian academic year starts September
            end_date=date(year + 1, 8, 31),
            is_current=True
        )


class AcademicTermService:
    """
    Academic Term business operations
    Manages terms within academic sessions
    """
    
    @staticmethod
    @transaction.atomic
    def create_terms_for_session(
        session: AcademicSession,
        created_by=None
    ) -> List[AcademicTerm]:
        """
        Automatically create 3 terms for a session
        Follows Nigerian standard: First, Second, Third Term
        
        Args:
            session: AcademicSession instance
            created_by: User creating the terms
            
        Returns:
            List[AcademicTerm]: Created terms
        """
        terms = []
        session_length = (session.end_date - session.start_date).days
        term_length = session_length // 3
        
        for i in range(1, 4):
            term_start = session.start_date + timezone.timedelta(days=term_length * (i - 1))
            term_end = session.start_date + timezone.timedelta(days=term_length * i - 1)
            
            if i == 3:  # Last term
                term_end = session.end_date
            
            # Check if term already exists
            term, created = AcademicTerm.objects.get_or_create(
                session=session,
                term=i,
                defaults={
                    'name': f"{dict(TermType.CHOICES)[i]} {session.name}",
                    'start_date': term_start,
                    'end_date': term_end,
                    'is_current': (i == 1 and session.is_current)
                }
            )
            
            if not created:
                # Update existing term dates
                term.start_date = term_start
                term.end_date = term_end
                term.save(update_fields=['start_date', 'end_date'])
            
            terms.append(term)
        
        return terms
    
    @staticmethod
    @transaction.atomic
    def set_current_term(term_id: int, updated_by=None) -> AcademicTerm:
        """
        Set a specific term as the current term
        
        Args:
            term_id: ID of term to set as current
            updated_by: User performing the action
            
        Returns:
            AcademicTerm: Updated term instance
            
        Raises:
            TermNotFoundError: If term doesn't exist
        """
        try:
            # Clear current flag from all terms
            AcademicTerm.objects.filter(is_current=True).update(is_current=False)
            
            # Set new current term
            term = AcademicTerm.objects.select_related('session').get(id=term_id)
            term.is_current = True
            term.save(update_fields=['is_current'])
            
            # Ensure parent session is also current
            if not term.session.is_current:
                AcademicSessionService.set_current_session(term.session.id, updated_by)
            
            return term
            
        except AcademicTerm.DoesNotExist:
            raise TermNotFoundError(f"Term with id {term_id} not found")
    
    @staticmethod
    @transaction.atomic
    def promote_term(updated_by=None) -> Optional[AcademicTerm]:
        """
        Move to next term automatically
        
        Returns:
            Optional[AcademicTerm]: New current term or None if at end
            
        Raises:
            NoActiveTermError: If no current term exists
        """
        current_term = AcademicTermSelector.get_current_term()
        if not current_term:
            raise NoActiveTermError("No active term to promote from")
        
        # Get next term in same session
        next_term = AcademicTerm.objects.filter(
            session=current_term.session,
            term=current_term.term + 1
        ).first()
        
        if next_term:
            return AcademicTermService.set_current_term(next_term.id, updated_by)
        
        # If no next term, move to next session's first term
        next_session = AcademicSession.objects.filter(
            start_date__gt=current_term.session.start_date
        ).order_by('start_date').first()
        
        if next_session:
            first_term = next_session.terms.order_by('term').first()
            if first_term:
                return AcademicTermService.set_current_term(first_term.id, updated_by)
        
        return None
    
    @staticmethod
    def get_current_academic_period() -> Dict[str, Any]:
        """
        Get comprehensive current academic period information
        
        Returns:
            Dict containing session and term details
        """
        current_term = AcademicTermSelector.get_current_term()
        current_session = AcademicSessionSelector.get_current_session()
        
        return {
            'has_current_term': current_term is not None,
            'has_current_session': current_session is not None,
            'session': {
                'id': current_session.id if current_session else None,
                'name': current_session.name if current_session else None,
                'code': current_session.code if current_session else None,
                'start_date': current_session.start_date if current_session else None,
                'end_date': current_session.end_date if current_session else None,
            } if current_session else None,
            'term': {
                'id': current_term.id if current_term else None,
                'number': current_term.term if current_term else None,
                'name': current_term.name if current_term else None,
                'display_name': current_term.get_term_display() if current_term else None,
                'start_date': current_term.start_date if current_term else None,
                'end_date': current_term.end_date if current_term else None,
            } if current_term else None,
            'academic_year': current_session.name if current_session else None,
        }
    
    @staticmethod
    def validate_term_dates(term: AcademicTerm) -> bool:
        """
        Validate that term dates are within session dates
        
        Args:
            term: AcademicTerm instance
            
        Returns:
            bool: True if valid
            
        Raises:
            ValidationError: If dates are invalid
        """
        if term.start_date < term.session.start_date:
            raise ValidationError(
                f"Term start date {term.start_date} is before session start "
                f"{term.session.start_date}"
            )
        
        if term.end_date > term.session.end_date:
            raise ValidationError(
                f"Term end date {term.end_date} is after session end "
                f"{term.session.end_date}"
            )
        
        if term.start_date >= term.end_date:
            raise ValidationError("Term start date must be before end date")
        
        return True
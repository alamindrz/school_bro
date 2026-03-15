"""
Student History Service
Records and manages student academic history and audit trail
"""

from django.db import transaction
from django.utils import timezone
from typing import Optional, Dict, Any, List
import logging

from ..models import Student, StudentHistory
from ..constants import StudentStatus
from ..exceptions import StudentHistoryError, StudentNotFoundError
from apps.corecode.selectors import AcademicTermSelector, AcademicSessionSelector
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class StudentHistoryService:
    """
    Student history and audit trail service.
    Records all significant events in a student's academic journey.
    """
    
    @staticmethod
    @transaction.atomic
    def record_enrollment(
        student: Student,
        performed_by_id: Optional[int] = None,
        notes: str = ""
    ) -> StudentHistory:
        """
        Record initial student enrollment.
        
        Args:
            student: Student instance
            performed_by_id: User ID performing the enrollment
            notes: Additional notes
            
        Returns:
            StudentHistory: Created history record
        """
        current_term = AcademicTermSelector.get_current_term()
        
        history = StudentHistory.objects.create(
            student=student,
            academic_session=student.enrollment_session,
            term=current_term.term if current_term else 1,
            class_at_time=student.current_class,
            status_at_time=student.status,
            action="ENROLLED",
            notes=notes or f"Student enrolled in {student.current_class.display_name}",
            performed_by_id=performed_by_id
        )
        
        logger.info(f"Enrollment recorded for student {student.admission_number}")
        return history
    
    @staticmethod
    @transaction.atomic
    def record_promotion(
        student: Student,
        from_class,
        to_class,
        academic_session_id: Optional[int] = None,
        term: int = 1,
        performed_by_id: Optional[int] = None,
        notes: str = ""
    ) -> StudentHistory:
        """
        Record student promotion to next class.
        
        Args:
            student: Student instance
            from_class: Previous class
            to_class: New class
            academic_session_id: Academic session ID
            term: Term number (1-3)
            performed_by_id: User ID performing the promotion
            notes: Additional notes
            
        Returns:
            StudentHistory: Created history record
        """
        if not academic_session_id:
            current_session = AcademicSessionSelector.get_current_session()
            academic_session_id = current_session.id if current_session else None
        
        history = StudentHistory.objects.create(
            student=student,
            academic_session_id=academic_session_id,
            term=term,
            class_at_time=to_class,
            status_at_time=student.status,
            action="PROMOTED",
            previous_class=from_class,
            notes=notes or f"Promoted from {from_class.display_name} to {to_class.display_name}",
            performed_by_id=performed_by_id
        )
        
        return history
    
    @staticmethod
    @transaction.atomic
    def record_status_change(
        student: Student,
        old_status: str,
        new_status: str,
        reason: str = "",
        performed_by_id: Optional[int] = None
    ) -> StudentHistory:
        """
        Record student status change.
        
        Args:
            student: Student instance
            old_status: Previous status
            new_status: New status
            reason: Reason for status change
            performed_by_id: User ID performing the change
            
        Returns:
            StudentHistory: Created history record
        """
        current_term = AcademicTermSelector.get_current_term()
        current_session = AcademicSessionSelector.get_current_session()
        
        history = StudentHistory.objects.create(
            student=student,
            academic_session=current_session,
            term=current_term.term if current_term else 1,
            class_at_time=student.current_class,
            status_at_time=new_status,
            action=f"STATUS_CHANGE_{old_status}_TO_{new_status}",
            notes=reason or f"Status changed from {old_status} to {new_status}",
            performed_by_id=performed_by_id
        )
        
        return history
    
    @staticmethod
    @transaction.atomic
    def record_graduation(
        student: Student,
        academic_session_id: Optional[int] = None,
        performed_by_id: Optional[int] = None,
        notes: str = ""
    ) -> StudentHistory:
        """
        Record student graduation.
        
        Args:
            student: Student instance
            academic_session_id: Graduation session
            performed_by_id: User ID processing graduation
            notes: Additional notes
            
        Returns:
            StudentHistory: Created history record
        """
        if not academic_session_id:
            current_session = AcademicSessionSelector.get_current_session()
            academic_session_id = current_session.id if current_session else None
        
        history = StudentHistory.objects.create(
            student=student,
            academic_session_id=academic_session_id,
            term=3,  # Graduation is always third term
            class_at_time=student.current_class,
            status_at_time=StudentStatus.GRADUATED,
            action="GRADUATED",
            notes=notes or "Completed secondary education",
            performed_by_id=performed_by_id
        )
        
        return history
    
    @staticmethod
    @transaction.atomic
    def record_transfer(
        student: Student,
        from_class,
        to_class,
        reason: str = "",
        performed_by_id: Optional[int] = None
    ) -> StudentHistory:
        """
        Record student transfer to different class/school.
        
        Args:
            student: Student instance
            from_class: Original class
            to_class: New class
            reason: Reason for transfer
            performed_by_id: User ID processing transfer
            
        Returns:
            StudentHistory: Created history record
        """
        current_term = AcademicTermSelector.get_current_term()
        current_session = AcademicSessionSelector.get_current_session()
        
        history = StudentHistory.objects.create(
            student=student,
            academic_session=current_session,
            term=current_term.term if current_term else 1,
            class_at_time=to_class,
            status_at_time=student.status,
            action="TRANSFERRED",
            previous_class=from_class,
            notes=reason or f"Transferred from {from_class.display_name} to {to_class.display_name}",
            performed_by_id=performed_by_id
        )
        
        return history
    
    @staticmethod
    def get_student_timeline(
        student_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get formatted timeline of student's academic history.
        
        Args:
            student_id: Student ID
            limit: Maximum number of entries
            
        Returns:
            List of timeline entries
        """
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            raise StudentNotFoundError(f"Student with id {student_id} not found")
        
        history_entries = StudentHistory.objects.filter(
            student=student
        ).select_related(
            'academic_session', 'class_at_time', 'previous_class', 'performed_by'
        ).order_by('-performed_at')[:limit]
        
        timeline = []
        for entry in history_entries:
            timeline.append({
                'id': entry.id,
                'date': entry.performed_at,
                'date_formatted': entry.performed_at.strftime('%b %d, %Y %H:%M'),
                'action': entry.get_action_display() if hasattr(entry, 'get_action_display') else entry.action,
                'action_code': entry.action,
                'class': entry.class_at_time.display_name if entry.class_at_time else None,
                'previous_class': entry.previous_class.display_name if entry.previous_class else None,
                'session': entry.academic_session.name if entry.academic_session else None,
                'term': f"Term {entry.term}",
                'status': entry.get_status_at_time_display() if hasattr(entry, 'get_status_at_time_display') else entry.status_at_time,
                'notes': entry.notes,
                'performed_by': entry.performed_by.get_full_name() if entry.performed_by else 'System',
                'performed_by_username': entry.performed_by.username if entry.performed_by else 'system',
            })
        
        return timeline
    
    @staticmethod
    @transaction.atomic
    def add_custom_history_entry(
        student_id: int,
        action: str,
        notes: str,
        academic_session_id: Optional[int] = None,
        term: int = 1,
        performed_by_id: Optional[int] = None
    ) -> StudentHistory:
        """
        Add a custom history entry for a student.
        
        Args:
            student_id: Student ID
            action: Custom action description
            notes: Detailed notes
            academic_session_id: Academic session ID
            term: Term number
            performed_by_id: User ID
            
        Returns:
            StudentHistory: Created history record
        """
        try:
            student = Student.objects.select_related('current_class').get(id=student_id)
        except Student.DoesNotExist:
            raise StudentNotFoundError(f"Student with id {student_id} not found")
        
        if not academic_session_id:
            current_session = AcademicSessionSelector.get_current_session()
            academic_session_id = current_session.id if current_session else None
        
        history = StudentHistory.objects.create(
            student=student,
            academic_session_id=academic_session_id,
            term=term,
            class_at_time=student.current_class,
            status_at_time=student.status,
            action=action.upper().replace(' ', '_')[:50],
            notes=notes,
            performed_by_id=performed_by_id
        )
        
        logger.info(f"Custom history entry added for student {student.admission_number}")
        return history
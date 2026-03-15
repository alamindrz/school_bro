"""
READ Layer - All complex student queries live here.
NO model mutations. Pure read operations.
Returns dictionaries, not model instances (for cross-app safety).
"""

from django.db.models import Q, Count, Prefetch, F, OuterRef, Subquery
from django.utils import timezone
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from .models import Student, Guardian, StudentHistory
from .constants import StudentStatus
from apps.corecode.selectors import StudentClassSelector, AcademicTermSelector


class StudentSelector:
    """All student read operations"""
    
    @staticmethod
    def get_by_id(student_id: int) -> Optional[Dict[str, Any]]:
        """
        Get student by ID. Returns dict, not model instance.
        This is the PUBLIC interface for other apps.
        """
        try:
            student = Student.objects.select_related(
                'current_class', 'enrollment_session', 'user'
            ).prefetch_related('guardians').get(id=student_id)
            
            return {
                'id': student.id,
                'admission_number': student.admission_number,
                'full_name': student.get_full_name,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'middle_name': student.middle_name,
                'gender': student.gender,
                'date_of_birth': student.date_of_birth.isoformat(),
                'age': student.age,
                'email': student.email,
                'phone': student.phone,
                'current_class': {
                    'id': student.current_class.id,
                    'name': student.current_class.name,
                    'display_name': student.current_class.display_name,
                },
                'enrollment_date': student.enrollment_date.isoformat(),
                'enrollment_session': student.enrollment_session.name,
                'status': student.status,
                'status_display': student.get_status_display(),
                'created_via': student.created_via,
                'guardians': [
                    {
                        'id': g.id,
                        'name': g.get_full_name,
                        'relationship': g.get_relationship_display(),
                        'phone': g.phone,
                        'email': g.email,
                        'is_primary': g.is_primary,
                    }
                    for g in student.guardians.all()
                ],
            }
        except Student.DoesNotExist:
            return None
    
    @staticmethod
    def get_class_students(
        class_id: int, 
        academic_session_id: Optional[int] = None,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all students in a class for a specific session.
        If no session provided, uses current session.
        """
        from apps.corecode.selectors import AcademicSessionSelector
        
        if not academic_session_id:
            current_session = AcademicSessionSelector.get_current_session()
            academic_session_id = current_session.id if current_session else None
        
        queryset = Student.objects.filter(
            current_class_id=class_id,
            enrollment_session_id=academic_session_id
        ).select_related('current_class')
        
        if not include_inactive:
            queryset = queryset.filter(status=StudentStatus.ACTIVE)
        
        students = []
        for student in queryset:
            students.append({
                'id': student.id,
                'admission_number': student.admission_number,
                'name': student.get_full_name,
                'gender': student.gender,
                'status': student.status,
            })
        
        return students
    
    @staticmethod
    def search_students(query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search students by name, admission number
        """
        queryset = Student.objects.filter(
            Q(admission_number__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).select_related('current_class')[:limit]
        
        return [
            {
                'id': s.id,
                'admission_number': s.admission_number,
                'name': s.get_full_name,
                'class': s.current_class.display_name if s.current_class else None,
                'status': s.status,
            }
            for s in queryset
        ]
    
    @staticmethod
    def get_students_for_promotion(
        from_class_id: int,
        academic_session_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get students eligible for promotion
        """
        students = Student.objects.filter(
            current_class_id=from_class_id,
            enrollment_session_id=academic_session_id,
            status=StudentStatus.ACTIVE
        ).select_related('current_class')
        
        return [
            {
                'id': s.id,
                'admission_number': s.admission_number,
                'name': s.get_full_name,
                'current_class': s.current_class.display_name,
            }
            for s in students
        ]
    
    @staticmethod
    def get_student_counts_by_class(academic_session_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get student counts grouped by class
        """
        from apps.corecode.selectors import AcademicSessionSelector
        
        if not academic_session_id:
            current_session = AcademicSessionSelector.get_current_session()
            academic_session_id = current_session.id if current_session else None
        
        counts = Student.objects.filter(
            enrollment_session_id=academic_session_id,
            status=StudentStatus.ACTIVE
        ).values(
            'current_class__id',
            'current_class__display_name'
        ).annotate(
            count=Count('id')
        ).order_by('current_class__sort_order')
        
        return [
            {
                'class_id': c['current_class__id'],
                'class_name': c['current_class__display_name'],
                'student_count': c['count'],
            }
            for c in counts
        ]


class GuardianSelector:
    """Guardian read operations"""
    
    @staticmethod
    def get_student_guardians(student_id: int) -> List[Dict[str, Any]]:
        """Get all guardians for a student"""
        guardians = Guardian.objects.filter(student_id=student_id).order_by('-is_primary')
        
        return [
            {
                'id': g.id,
                'full_name': g.get_full_name,
                'relationship': g.get_relationship_display(),
                'phone': g.phone,
                'email': g.email,
                'is_primary': g.is_primary,
                'is_emergency': g.is_emergency_contact,
            }
            for g in guardians
        ]
    
    @staticmethod
    def get_primary_guardian(student_id: int) -> Optional[Dict[str, Any]]:
        """Get primary guardian for a student"""
        try:
            guardian = Guardian.objects.get(student_id=student_id, is_primary=True)
            return {
                'id': guardian.id,
                'full_name': guardian.get_full_name,
                'relationship': guardian.get_relationship_display(),
                'phone': guardian.phone,
                'email': guardian.email,
            }
        except Guardian.DoesNotExist:
            return None


class StudentHistorySelector:
    """Student history/audit read operations"""
    
    @staticmethod
    def get_student_timeline(student_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get chronological timeline of student's academic history"""
        history = StudentHistory.objects.filter(
            student_id=student_id
        ).select_related(
            'academic_session', 'class_at_time', 'previous_class', 'performed_by'
        ).order_by('-performed_at')[:limit]
        
        return [
            {
                'date': h.performed_at.isoformat(),
                'action': h.action,
                'class': h.class_at_time.display_name,
                'previous_class': h.previous_class.display_name if h.previous_class else None,
                'session': h.academic_session.name,
                'term': h.get_term_display(),
                'performed_by': h.performed_by.get_full_name() if h.performed_by else 'System',
                'notes': h.notes,
            }
            for h in history
        ]
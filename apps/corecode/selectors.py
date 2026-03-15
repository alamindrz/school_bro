"""
READ Layer - All complex queries live here.
No cross-app imports allowed. Pure corecode queries only.
"""

from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from typing import Optional, List, Dict, Any
from .models import AcademicSession, AcademicTerm, StudentClass, SiteConfig, SystemLog, Subject
from .constants import SiteConfigKey, NigerianClassLevel


class AcademicSessionSelector:
    """All academic session read operations"""
    
    @staticmethod
    def get_current_session() -> Optional[AcademicSession]:
        """Get the currently active academic session"""
        return AcademicSession.objects.filter(is_current=True).first()
    
    @staticmethod
    def get_session_by_code(code: str) -> Optional[AcademicSession]:
        """Get session by code (e.g., '202425')"""
        return AcademicSession.objects.filter(code=code).first()
    
    @staticmethod
    def list_sessions(include_past: bool = True, limit: int = None) -> List[AcademicSession]:
        """List academic sessions with optional filtering"""
        queryset = AcademicSession.objects.all()
        if not include_past:
            queryset = queryset.filter(end_date__gte=timezone.now().date())
        if limit:
            queryset = queryset[:limit]
        return list(queryset)
    
    @staticmethod
    def get_queryset_for_forms(active_only: bool = True):
        """
        Get queryset of academic sessions for use in Django forms.
        Returns queryset, not dict (for form field compatibility).
        
        Args:
            active_only: If True, return only sessions that are current or future
            
        Returns:
            Django queryset of AcademicSession objects
        """
        queryset = AcademicSession.objects.all()
        
        if active_only:
            # Include current and future sessions, exclude past sessions
            queryset = queryset.filter(end_date__gte=timezone.now().date())
        
        return queryset.order_by('-start_date')
    
    @staticmethod
    def get_current_session_queryset():
        """
        Get queryset containing only the current session.
        Useful for forms that should only show the current session.
        
        Returns:
            Django queryset with only the current session
        """
        current = AcademicSession.objects.filter(is_current=True)
        return current
    
    @staticmethod
    def get_choices_for_forms(active_only: bool = True) -> List[tuple]:
        """
        Get choices of academic sessions for form select fields.
        Returns list of (id, name) tuples.
        
        Args:
            active_only: If True, return only current/future sessions
            
        Returns:
            List of (id, name) tuples for select field choices
        """
        queryset = AcademicSession.objects.all()
        
        if active_only:
            queryset = queryset.filter(end_date__gte=timezone.now().date())
        
        return [(session.id, session.name) for session in queryset.order_by('-start_date')]



class AcademicTermSelector:
    """All academic term read operations"""
    
    @staticmethod
    def get_current_term() -> Optional[AcademicTerm]:
        """Get the currently active academic term"""
        return AcademicTerm.objects.filter(is_current=True).select_related('session').first()
    
    @staticmethod
    def get_terms_for_session(session_id: int) -> List[AcademicTerm]:
        """Get all terms for a specific session"""
        return list(AcademicTerm.objects.filter(session_id=session_id).order_by('term'))
    
    @staticmethod
    def get_terms_queryset_for_session(session_id: int):
        """
        Get queryset of terms for a specific session.
        Useful for form fields.
        
        Args:
            session_id: ID of the academic session
            
        Returns:
            Django queryset of AcademicTerm objects for the session
        """
        return AcademicTerm.objects.filter(session_id=session_id).order_by('term')
    
    @staticmethod
    def get_active_term_details() -> Dict[str, Any]:
        """Get comprehensive current term information"""
        current_term = AcademicTerm.objects.filter(is_current=True).select_related('session').first()
        if not current_term:
            return {}
        
        return {
            'id': current_term.id,
            'term': current_term.term,
            'term_name': current_term.get_term_display(),
            'session': current_term.session.name,
            'session_id': current_term.session.id,
            'start_date': current_term.start_date,
            'end_date': current_term.end_date,
            'is_active': current_term.is_current,
        }


class StudentClassSelector:
    """
    All class-related read operations.
    ARCHITECTURE COMPLIANT: Returns dicts, not model instances.
    Single source of truth for class data retrieval.
    """

    @staticmethod
    def get_by_id(class_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific class by its primary key.
        Returns dictionary with class data or None if not found.
        
        Args:
            class_id: Primary key of the class
            
        Returns:
            Dictionary with class data or None
        """
        if not class_id:
            return None
            
        try:
            class_obj = StudentClass.objects.get(id=class_id)
            
            return {
                'id': class_obj.id,
                'name': class_obj.name,
                'display_name': class_obj.display_name,
                'education_level': class_obj.education_level,
                'education_level_display': class_obj.get_education_level_display(),
                'max_students': class_obj.max_students,
                'sort_order': class_obj.sort_order,
                'is_active': class_obj.is_active,
                'is_graduating_class': class_obj.is_graduating_class,
                'next_class_id': class_obj.next_class.id if class_obj.next_class else None,
                'next_class_name': class_obj.next_class.display_name if class_obj.next_class else None,
                'created_at': class_obj.created_at.isoformat() if class_obj.created_at else None,
                'updated_at': class_obj.updated_at.isoformat() if class_obj.updated_at else None,
            }
            
        except (StudentClass.DoesNotExist, ValueError):
            return None
            
            
    @staticmethod
    def active_classes() -> List[Dict[str, Any]]:
        """
        Get all active classes for use in forms and dropdowns.
        Returns list of class dictionaries with id and display_name.
        This is a convenience method for get_all_classes(active_only=True).
        
        Returns:
            List of active class dictionaries
        """
        return StudentClassSelector.get_all_classes(active_only=True, include_inactive=False)
    

    @staticmethod
    def get_by_name(name: str) -> Optional[Dict[str, Any]]:
        """
        Get class by name (e.g., 'SS1', 'JSS1').
        
        Args:
            name: Class name (e.g., 'SS1')
            
        Returns:
            Dictionary with class data or None if not found
        """
        if not name:
            return None
            
        try:
            class_obj = StudentClass.objects.get(name=name, is_active=True)
            return StudentClassSelector.get_by_id(class_obj.id)
        except StudentClass.DoesNotExist:
            return None

    @staticmethod
    def get_all_classes(
        active_only: bool = True,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all classes with optional filtering.
        
        Args:
            active_only: If True, return only active classes
            include_inactive: If True, include inactive classes (overrides active_only)
            
        Returns:
            List of class dictionaries
        """
        queryset = StudentClass.objects.all()
        
        if not include_inactive and active_only:
            queryset = queryset.filter(is_active=True)
        
        classes = []
        for class_obj in queryset.order_by('sort_order', 'name'):
            classes.append({
                'id': class_obj.id,
                'name': class_obj.name,
                'display_name': class_obj.display_name,
                'education_level': class_obj.education_level,
                'education_level_display': class_obj.get_education_level_display(),
                'max_students': class_obj.max_students,
                'sort_order': class_obj.sort_order,
                'is_active': class_obj.is_active,
                'is_graduating_class': class_obj.is_graduating_class,
            })
        
        return classes

    @staticmethod
    def get_classes_by_level(education_level: str) -> List[Dict[str, Any]]:
        """
        Get classes for specific education level.
        
        Args:
            education_level: Education level from EducationLevel constants
            
        Returns:
            List of class dictionaries for the specified level
        """
        if not education_level:
            return []
        
        classes = StudentClass.objects.filter(
            education_level=education_level,
            is_active=True
        ).order_by('sort_order', 'name')
        
        return [
            {
                'id': c.id,
                'name': c.name,
                'display_name': c.display_name,
                'max_students': c.max_students,
                'sort_order': c.sort_order,
            }
            for c in classes
        ]

    @staticmethod
    def get_graduating_classes() -> List[Dict[str, Any]]:
        """
        Get SS3 classes - graduating students.
        
        Returns:
            List of graduating class dictionaries
        """
        from .constants import NigerianClassLevel
        
        classes = StudentClass.objects.filter(
            name=NigerianClassLevel.SS_3,
            is_active=True
        ).order_by('sort_order', 'name')
        
        return [
            {
                'id': c.id,
                'name': c.name,
                'display_name': c.display_name,
                'max_students': c.max_students,
            }
            for c in classes
        ]

    @staticmethod
    def search_classes(query: str) -> List[Dict[str, Any]]:
        """
        Search classes by name or display name.
        
        Args:
            query: Search string
            
        Returns:
            List of matching class dictionaries
        """
        if not query or len(query) < 2:
            return []
        
        from django.db import models
        
        classes = StudentClass.objects.filter(
            models.Q(name__icontains=query) |
            models.Q(display_name__icontains=query)
        ).filter(is_active=True)[:20]
        
        return [
            {
                'id': c.id,
                'name': c.name,
                'display_name': c.display_name,
                'education_level': c.education_level,
                'education_level_display': c.get_education_level_display(),
            }
            for c in classes
        ]

    @staticmethod
    def get_class_progression_path(start_class_id: int) -> List[Dict[str, Any]]:
        """
        Get full progression path from a starting class.
        Returns list of classes in progression order until graduation.
        
        Args:
            start_class_id: ID of the starting class
            
        Returns:
            List of class dictionaries in progression order
        """
        try:
            current_class = StudentClass.objects.get(id=start_class_id)
        except (StudentClass.DoesNotExist, ValueError):
            return []
        
        path = []
        seen = set()
        
        while current_class and current_class.id not in seen:
            seen.add(current_class.id)
            path.append({
                'id': current_class.id,
                'name': current_class.name,
                'display_name': current_class.display_name,
                'level': current_class.education_level,
                'level_display': current_class.get_education_level_display(),
                'is_graduating': current_class.is_graduating_class,
                'max_students': current_class.max_students,
            })
            
            current_class = current_class.next_class
        
        return path

    @staticmethod
    def get_class_statistics() -> Dict[str, Any]:
        """
        Get overall class statistics including capacity and enrollment.
        
        Returns:
            Dictionary with class statistics
        """
        from apps.students.models import Student
        
        total_classes = StudentClass.objects.filter(is_active=True).count()
        total_capacity = sum(
            c.max_students for c in StudentClass.objects.filter(is_active=True)
        )
        total_enrolled = Student.objects.filter(status='active').count()
        
        # Classes nearing capacity (>80%)
        nearing_capacity = []
        for class_obj in StudentClass.objects.filter(is_active=True):
            enrolled = Student.objects.filter(
                current_class=class_obj, 
                status='active'
            ).count()
            
            if enrolled > 0:
                percentage = (enrolled / class_obj.max_students) * 100
                if percentage > 80:
                    nearing_capacity.append({
                        'id': class_obj.id,
                        'name': class_obj.display_name,
                        'enrolled': enrolled,
                        'max': class_obj.max_students,
                        'percentage': round(percentage, 1),
                        'available': class_obj.max_students - enrolled,
                    })
        
        # Classes by level
        by_level = {}
        for level_code, level_label in EducationLevel.CHOICES:
            level_classes = StudentClass.objects.filter(
                education_level=level_code,
                is_active=True
            )
            total_level_capacity = sum(c.max_students for c in level_classes)
            total_level_enrolled = Student.objects.filter(
                current_class__in=level_classes,
                status='active'
            ).count()
            
            if level_classes.exists():
                by_level[level_code] = {
                    'label': level_label,
                    'class_count': level_classes.count(),
                    'total_capacity': total_level_capacity,
                    'total_enrolled': total_level_enrolled,
                    'utilization': round(
                        (total_level_enrolled / total_level_capacity * 100) 
                        if total_level_capacity > 0 else 0, 
                        1
                    ),
                }
        
        return {
            'total_classes': total_classes,
            'total_capacity': total_capacity,
            'total_enrolled': total_enrolled,
            'overall_utilization': round(
                (total_enrolled / total_capacity * 100) if total_capacity > 0 else 0,
                1
            ),
            'nearing_capacity': nearing_capacity[:10],  # Top 10
            'by_level': by_level,
            'graduating_classes': StudentClassSelector.get_graduating_classes(),
        }

    @staticmethod
    def get_queryset_for_forms(active_only: bool = True):
        """
        Get queryset of classes for use in Django forms.
        Returns queryset, not dict (for form field compatibility).
        
        Args:
            active_only: If True, return only active classes
            
        Returns:
            Django queryset of StudentClass objects
        """
        queryset = StudentClass.objects.all()
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('sort_order', 'name')

    @staticmethod
    def get_enrollment_summary(class_id: int) -> Dict[str, Any]:
        """
        Get detailed enrollment summary for a specific class.
        
        Args:
            class_id: ID of the class
            
        Returns:
            Dictionary with enrollment statistics
        """
        from apps.students.models import Student
        
        try:
            class_obj = StudentClass.objects.get(id=class_id)
        except (StudentClass.DoesNotExist, ValueError):
            return {}
        
        # Get all students in this class
        students = Student.objects.filter(
            current_class=class_obj,
            status='active'
        )
        
        total_students = students.count()
        gender_counts = {
            'male': students.filter(gender='M').count(),
            'female': students.filter(gender='F').count(),
        }
        
        # Age distribution
        from datetime import date
        today = date.today()
        age_groups = {
            'under_10': 0,
            '10_12': 0,
            '13_15': 0,
            '16_18': 0,
            'over_18': 0,
        }
        
        for student in students:
            age = (today - student.date_of_birth).days // 365
            if age < 10:
                age_groups['under_10'] += 1
            elif 10 <= age <= 12:
                age_groups['10_12'] += 1
            elif 13 <= age <= 15:
                age_groups['13_15'] += 1
            elif 16 <= age <= 18:
                age_groups['16_18'] += 1
            else:
                age_groups['over_18'] += 1
        
        return {
            'class_id': class_obj.id,
            'class_name': class_obj.display_name,
            'max_capacity': class_obj.max_students,
            'total_enrolled': total_students,
            'available_slots': class_obj.max_students - total_students,
            'utilization_percentage': round(
                (total_students / class_obj.max_students * 100) 
                if class_obj.max_students > 0 else 0,
                1
            ),
            'gender_distribution': gender_counts,
            'age_distribution': age_groups,
            'is_full': total_students >= class_obj.max_students,
            'is_over_capacity': total_students > class_obj.max_students,
        }


class SiteConfigSelector:
    """All configuration read operations"""
    
    @staticmethod
    def get_config_value(key: str, default=None):
        """Get a single configuration value"""
        return SiteConfig.get(key, default)
    
    @staticmethod
    def get_many_configs(keys: List[str]) -> Dict[str, Any]:
        """Get multiple configuration values efficiently"""
        configs = SiteConfig.objects.filter(key__in=keys)
        result = {}
        for config in configs:
            result[config.key] = SiteConfig.get(config.key)
        
        # Add defaults for missing keys
        for key in keys:
            if key not in result:
                result[key] = None
        
        return result
    
    @staticmethod
    def get_current_academic_config() -> Dict[str, Any]:
        """Get current academic year configuration"""
        current_session = AcademicSessionSelector.get_current_session()
        current_term = AcademicTermSelector.get_current_term()
        
        return {
            'current_session': current_session.name if current_session else None,
            'current_session_id': current_session.id if current_session else None,
            'current_term': current_term.term if current_term else None,
            'current_term_name': current_term.get_term_display() if current_term else None,
            'current_term_id': current_term.id if current_term else None,
        }


class SystemLogSelector:
    """All system log read operations"""
    
    @staticmethod
    def get_user_logs(user_id: int, limit: int = 100) -> List[SystemLog]:
        """Get recent logs for a specific user"""
        return list(SystemLog.objects.filter(user_id=user_id)[:limit])
    
    @staticmethod
    def get_model_logs(app_label: str, model_name: str, object_id: str = None) -> List[SystemLog]:
        """Get logs for a specific model/object"""
        queryset = SystemLog.objects.filter(
            app_label=app_label,
            model_name=model_name
        )
        if object_id:
            queryset = queryset.filter(object_id=object_id)
        return list(queryset[:50])
    
    @staticmethod
    def get_recent_actions(limit: int = 20) -> List[SystemLog]:
        """Get most recent system actions"""
        return list(SystemLog.objects.select_related('user')[:limit])


class SubjectSelector:
    """Subject read operations"""
    
    @staticmethod
    def get_by_id(subject_id: int) -> Optional[Dict[str, Any]]:
        """Get subject by ID"""
        try:
            subject = Subject.objects.get(id=subject_id)
            return {
                'id': subject.id,
                'name': subject.name,
                'code': subject.code,
                'subject_type': subject.subject_type,
                'subject_type_display': subject.get_subject_type_display(),
                'description': subject.description,
                'is_active': subject.is_active,
                'is_nigerian_core': subject.is_nigerian_core,
                'offered_in_classes': [
                    {'id': c.id, 'name': c.display_name}
                    for c in subject.offered_in_classes.all()
                ],
            }
        except Subject.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_code(code: str) -> Optional[Dict[str, Any]]:
        """Get subject by code"""
        try:
            subject = Subject.objects.get(code=code)
            return SubjectSelector.get_by_id(subject.id)
        except Subject.DoesNotExist:
            return None
    
    @staticmethod
    def list_subjects(
        class_id: Optional[int] = None,
        subject_type: Optional[str] = None,
        active_only: bool = True,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List subjects with filters"""
        queryset = Subject.objects.all()
        
        if class_id:
            queryset = queryset.filter(offered_in_classes__id=class_id)
        
        if subject_type:
            queryset = queryset.filter(subject_type=subject_type)
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search)
            )
        
        subjects = []
        for subject in queryset.order_by('name'):
            subjects.append({
                'id': subject.id,
                'name': subject.name,
                'code': subject.code,
                'subject_type': subject.get_subject_type_display(),
                'is_nigerian_core': subject.is_nigerian_core,
            })
        
        return subjects
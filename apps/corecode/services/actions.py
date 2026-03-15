"""
Corecode Service Actions
All write operations and business logic
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Dict, Any, Optional, List

from ..models import AcademicSession, AcademicTerm, StudentClass, SiteConfig, SystemLog
from ..constants import NigerianClassLevel, SiteConfigKey, TermType
from ..selectors import AcademicSessionSelector, AcademicTermSelector


class AcademicSessionService:
    """Academic Session business operations"""
    
    @staticmethod
    @transaction.atomic
    def create_session(name: str, code: str, start_date, end_date, is_current: bool = False) -> AcademicSession:
        """
        Create a new academic session
        If is_current=True, automatically deactivate other current sessions
        """
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
        AcademicTermService.create_terms_for_session(session)
        
        return session
    
    @staticmethod
    @transaction.atomic
    def set_current_session(session_id: int) -> AcademicSession:
        """Set a session as current, unset others"""
        AcademicSession.objects.filter(is_current=True).update(is_current=False)
        session = AcademicSession.objects.get(id=session_id)
        session.is_current = True
        session.save()
        return session
    
    @staticmethod
    @transaction.atomic
    def archive_session(session_id: int) -> None:
        """Archive a session - mark as not current"""
        AcademicSession.objects.filter(id=session_id).update(is_current=False)


class AcademicTermService:
    """Academic Term business operations"""
    
    @staticmethod
    @transaction.atomic
    def create_terms_for_session(session: AcademicSession) -> List[AcademicTerm]:
        """
        Automatically create 3 terms for a session
        Follows Nigerian standard: First, Second, Third Term
        """
        terms = []
        session_length = (session.end_date - session.start_date).days
        term_length = session_length // 3
        
        for i in range(1, 4):
            term_start = session.start_date + timezone.timedelta(days=term_length * (i-1))
            term_end = session.start_date + timezone.timedelta(days=term_length * i - 1)
            
            if i == 3:  # Last term
                term_end = session.end_date
            
            term = AcademicTerm(
                session=session,
                term=i,
                name=f"{TermType.CHOICES[i-1][1]} {session.name}",
                start_date=term_start,
                end_date=term_end,
                is_current=(i == 1 and session.is_current)  # First term current if session current
            )
            term.full_clean()
            term.save()
            terms.append(term)
        
        return terms
    
    @staticmethod
    @transaction.atomic
    def set_current_term(term_id: int) -> AcademicTerm:
        """Set a specific term as current"""
        AcademicTerm.objects.filter(is_current=True).update(is_current=False)
        term = AcademicTerm.objects.select_related('session').get(id=term_id)
        term.is_current = True
        term.save()
        
        # Ensure parent session is also current
        if not term.session.is_current:
            AcademicSessionService.set_current_session(term.session.id)
        
        return term
    
    @staticmethod
    @transaction.atomic
    def promote_term() -> Optional[AcademicTerm]:
        """Move to next term automatically"""
        current_term = AcademicTermSelector.get_current_term()
        if not current_term:
            return None
        
        # Get next term in same session
        next_term = AcademicTerm.objects.filter(
            session=current_term.session,
            term=current_term.term + 1
        ).first()
        
        if next_term:
            return AcademicTermService.set_current_term(next_term.id)
        
        # If no next term, move to next session's first term
        next_session = AcademicSession.objects.filter(
            start_date__gt=current_term.session.start_date
        ).order_by('start_date').first()
        
        if next_session:
            first_term = next_session.terms.order_by('term').first()
            if first_term:
                return AcademicTermService.set_current_term(first_term.id)
        
        return None


class StudentClassService:
    """Student Class business operations"""
    
    @staticmethod
    @transaction.atomic
    def create_class(name: str, display_name: str, education_level: str, 
                    max_students: int = 40, sort_order: int = 0) -> StudentClass:
        """
        Create a new student class
        Must use NigerianClassLevel constants
        """
        if name not in dict(NigerianClassLevel.CHOICES):
            raise ValidationError(f"Invalid class name: {name}. Must use Nigerian standard classes.")
        
        student_class = StudentClass(
            name=name,
            display_name=display_name,
            education_level=education_level,
            max_students=max_students,
            sort_order=sort_order,
            is_active=True
        )
        student_class.full_clean()
        student_class.save()
        return student_class
    
    @staticmethod
    @transaction.atomic
    def update_class_capacity(class_id: int, max_students: int) -> StudentClass:
        """Update maximum students for a class"""
        student_class = StudentClass.objects.get(id=class_id)
        student_class.max_students = max_students
        student_class.full_clean()
        student_class.save()
        return student_class
    
    @staticmethod
    @transaction.atomic
    def bulk_create_nigerian_classes() -> List[StudentClass]:
        """Create all standard Nigerian 6-3-3-4 classes"""
        classes = []
        order = 0
        
        # Nursery
        nursery_classes = [
            (NigerianClassLevel.NURSERY_1, "Nursery 1", EducationLevel.NURSERY, 25),
            (NigerianClassLevel.NURSERY_2, "Nursery 2", EducationLevel.NURSERY, 25),
            (NigerianClassLevel.NURSERY_3, "Nursery 3", EducationLevel.NURSERY, 25),
        ]
        
        # Primary
        primary_classes = [
            (NigerianClassLevel.PRIMARY_1, "Primary 1", EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_2, "Primary 2", EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_3, "Primary 3", EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_4, "Primary 4", EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_5, "Primary 5", EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_6, "Primary 6", EducationLevel.PRIMARY, 40),
        ]
        
        # JSS
        jss_classes = [
            (NigerianClassLevel.JSS_1, "JSS 1", EducationLevel.JSS, 45),
            (NigerianClassLevel.JSS_2, "JSS 2", EducationLevel.JSS, 45),
            (NigerianClassLevel.JSS_3, "JSS 3", EducationLevel.JSS, 45),
        ]
        
        # SSS
        sss_classes = [
            (NigerianClassLevel.SS_1, "SS 1", EducationLevel.SSS, 45),
            (NigerianClassLevel.SS_2, "SS 2", EducationLevel.SSS, 45),
            (NigerianClassLevel.SS_3, "SS 3", EducationLevel.SSS, 45),
        ]
        
        all_classes = nursery_classes + primary_classes + jss_classes + sss_classes
        
        for name, display_name, level, max_students in all_classes:
            cls, created = StudentClass.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'education_level': level,
                    'max_students': max_students,
                    'sort_order': order,
                    'is_active': True,
                }
            )
            classes.append(cls)
            order += 1
        
        return classes


class SiteConfigService:
    """Site Configuration business operations"""
    
    @staticmethod
    @transaction.atomic
    def set_config(key: str, value: Any, user=None, description: str = "") -> SiteConfig:
        """Set a configuration value with audit trail"""
        config, created = SiteConfig.objects.update_or_create(
            key=key,
            defaults={
                'value': str(value) if value is not None else None,
                'updated_by': user,
                'description': description,
            }
        )
        return config
    
    @staticmethod
    @transaction.atomic
    def initialize_default_configs(user=None) -> Dict[str, SiteConfig]:
        """Initialize all required site configurations with defaults"""
        defaults = {
            SiteConfigKey.TERMS_PER_SESSION: '3',
            SiteConfigKey.CURRENT_SESSION: None,
            SiteConfigKey.CURRENT_TERM: None,
            SiteConfigKey.ADMISSIONS_OPEN: 'False',
            SiteConfigKey.AUTO_ENROLL_APPROVED: 'True',
            SiteConfigKey.EXAM_CLEARANCE_REQUIRED: 'True',
            SiteConfigKey.PASS_MARK: '40',
            SiteConfigKey.DISTINCTION_MARK: '70',
            SiteConfigKey.ATTENDANCE_TRACKING_ENABLED: 'True',
            SiteConfigKey.MAINTENANCE_MODE: 'False',
            SiteConfigKey.COMPANY_NAME: 'DETs Toolkit',
        }
        
        configs = {}
        for key, default_value in defaults.items():
            config, _ = SiteConfig.objects.get_or_create(
                key=key,
                defaults={
                    'value': default_value,
                    'updated_by': user,
                    'description': f'Default configuration for {key}',
                }
            )
            configs[key] = config
        
        return configs


class SystemLogService:
    """System-wide audit logging service"""
    
    @staticmethod
    @transaction.atomic
    def log_action(
        user,
        action: str,
        app_label: str,
        model_name: str,
        object_id: str = None,
        object_repr: str = None,
        changes: Dict = None,
        request=None
    ) -> SystemLog:
        """Create a system log entry"""
        
        log = SystemLog(
            user=user,
            username=user.get_username() if user else 'system',
            action=action,
            app_label=app_label,
            model_name=model_name,
            object_id=str(object_id) if object_id else None,
            object_repr=object_repr[:200] if object_repr else None,
            changes=changes or {},
        )
        
        if request:
            log.ip_address = request.META.get('REMOTE_ADDR')
            log.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        log.save()
        return log
    
    @staticmethod
    def log_grade_change(user, student, subject, old_grade, new_grade, request=None):
        """Specialized logging for grade changes"""
        return SystemLogService.log_action(
            user=user,
            action=SystemLog.ActionType.GRADE_CHANGE,
            app_label=SystemLog.AppLabel.RESULTS,
            model_name='Result',
            object_id=str(student.id),
            object_repr=f"{student} - {subject}",
            changes={
                'old_grade': old_grade,
                'new_grade': new_grade,
                'subject': subject,
            },
            request=request
        )
    
    @staticmethod
    def log_payment(user, invoice, amount, payment_method, request=None):
        """Specialized logging for payments"""
        return SystemLogService.log_action(
            user=user,
            action=SystemLog.ActionType.PAYMENT,
            app_label=SystemLog.AppLabel.FINANCE,
            model_name='Invoice',
            object_id=str(invoice.id),
            object_repr=f"Invoice #{invoice.invoice_number}",
            changes={
                'amount': str(amount),
                'payment_method': payment_method,
                'status': 'completed',
            },
            request=request
        )
"""
Nigerian 6-3-3-4 Education System Constants
No dependencies - pure Python constants
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

class EducationLevel:
    """Strict 6-3-3-4 Nigerian education structure"""
    
    NURSERY = 'nursery'
    PRIMARY = 'primary'
    JSS = 'jss'  # Junior Secondary School
    SSS = 'sss'  # Senior Secondary School
    TERTIARY = 'tertiary'
    
    CHOICES = [
        (NURSERY, _('Nursery')),
        (PRIMARY, _('Primary')),
        (JSS, _('Junior Secondary')),
        (SSS, _('Senior Secondary')),
        (TERTIARY, _('Tertiary')),
    ]


class NigerianClassLevel:
    """
    Standardized Nigerian class names
    No custom classes - schools must map to these
    """
    
    # Nursery: 3 years
    NURSERY_1 = 'NUR1'
    NURSERY_2 = 'NUR2'
    NURSERY_3 = 'NUR3'
    
    # Primary: 6 years
    PRIMARY_1 = 'PRI1'
    PRIMARY_2 = 'PRI2'
    PRIMARY_3 = 'PRI3'
    PRIMARY_4 = 'PRI4'
    PRIMARY_5 = 'PRI5'
    PRIMARY_6 = 'PRI6'
    
    # Junior Secondary: 3 years
    JSS_1 = 'JSS1'
    JSS_2 = 'JSS2'
    JSS_3 = 'JSS3'
    
    # Senior Secondary: 3 years
    SS_1 = 'SS1'
    SS_2 = 'SS2'
    SS_3 = 'SS3'
    
    CHOICES = [
        # Nursery
        (NURSERY_1, _('Nursery 1')),
        (NURSERY_2, _('Nursery 2')),
        (NURSERY_3, _('Nursery 3')),
        # Primary
        (PRIMARY_1, _('Primary 1')),
        (PRIMARY_2, _('Primary 2')),
        (PRIMARY_3, _('Primary 3')),
        (PRIMARY_4, _('Primary 4')),
        (PRIMARY_5, _('Primary 5')),
        (PRIMARY_6, _('Primary 6')),
        # Junior Secondary
        (JSS_1, _('JSS 1')),
        (JSS_2, _('JSS 2')),
        (JSS_3, _('JSS 3')),
        # Senior Secondary
        (SS_1, _('SS 1')),
        (SS_2, _('SS 2')),
        (SS_3, _('SS 3')),
    ]
    
    # Progression mapping - used for promotions
    NEXT_CLASS = {
        NURSERY_1: NURSERY_2,
        NURSERY_2: NURSERY_3,
        NURSERY_3: PRIMARY_1,
        PRIMARY_1: PRIMARY_2,
        PRIMARY_2: PRIMARY_3,
        PRIMARY_3: PRIMARY_4,
        PRIMARY_4: PRIMARY_5,
        PRIMARY_5: PRIMARY_6,
        PRIMARY_6: JSS_1,
        JSS_1: JSS_2,
        JSS_2: JSS_3,
        JSS_3: SS_1,
        SS_1: SS_2,
        SS_2: SS_3,
        SS_3: None,  # Graduation
    }


class TermType:
    """Nigerian standard: 3 terms per academic session"""
    
    FIRST = 1
    SECOND = 2
    THIRD = 3
    
    CHOICES = [
        (FIRST, _('First Term')),
        (SECOND, _('Second Term')),
        (THIRD, _('Third Term')),
    ]


class SiteConfigKey:
    """
    All configurable site settings.
    The "No-Customization" Rule: Every school-specific requirement must be a toggle here.
    """
    
    # Academic Structure
    TERMS_PER_SESSION = 'TERMS_PER_SESSION'  # Default: 3, never 4
    CURRENT_SESSION = 'CURRENT_SESSION'
    CURRENT_TERM = 'CURRENT_TERM'
    
    # Admissions
    ADMISSIONS_OPEN = 'ADMISSIONS_OPEN'
    ADMISSION_DEADLINE = 'ADMISSION_DEADLINE'
    AUTO_ENROLL_APPROVED = 'AUTO_ENROLL_APPROVED'  # Auto enroll approved applicants
    APPLICATION_FEE = 'APPLICATION_FEE'  # ADD THIS
    ADMISSION_DEADLINE_DAYS = 'ADMISSION_DEADLINE_DAYS'  # ADD THIS
    
  
    # Finance
    INCLUDE_FEE_BALANCE_IN_REPORT = 'INCLUDE_FEE_BALANCE_IN_REPORT'
    EXAM_CLEARANCE_REQUIRED = 'EXAM_CLEARANCE_REQUIRED'
    
    # Results
    RESULT_TEMPLATE = 'RESULT_TEMPLATE'  # Standard, Cambridge, etc.
    PASS_MARK = 'PASS_MARK'  # Default: 40
    DISTINCTION_MARK = 'DISTINCTION_MARK'  # Default: 70
    
    # Attendance
    ATTENDANCE_TRACKING_ENABLED = 'ATTENDANCE_TRACKING_ENABLED'
    
    # System
    MAINTENANCE_MODE = 'MAINTENANCE_MODE'
    COMPANY_NAME = 'COMPANY_NAME'
    COMPANY_EMAIL = 'COMPANY_EMAIL'
    
    # All configurable keys
    ALL_KEYS = [
        TERMS_PER_SESSION,
        CURRENT_SESSION,
        CURRENT_TERM,
        ADMISSIONS_OPEN,
        ADMISSION_DEADLINE,
        AUTO_ENROLL_APPROVED,
        INCLUDE_FEE_BALANCE_IN_REPORT,
        EXAM_CLEARANCE_REQUIRED,
        RESULT_TEMPLATE,
        PASS_MARK,
        DISTINCTION_MARK,
        ATTENDANCE_TRACKING_ENABLED,
        MAINTENANCE_MODE,
        COMPANY_NAME,
        COMPANY_EMAIL,
        APPLICATION_FEE,
        ADMISSION_DEADLINE_DAYS
        ]
        
class SubjectType:
    """Subject categories"""
    
    CORE = 'core'
    ELECTIVE = 'elective'
    VOCATIONAL = 'vocational'
    
    CHOICES = [
        (CORE, _('Core Subject')),
        (ELECTIVE, _('Elective')),
        (VOCATIONAL, _('Vocational')),
    ]
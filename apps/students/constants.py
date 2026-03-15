"""
Student-specific constants
No dependencies on other apps
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class StudentStatus:
    """Student lifecycle status"""
    
    ACTIVE = 'active'
    GRADUATED = 'graduated'
    TRANSFERRED = 'transferred'
    WITHDRAWN = 'withdrawn'
    SUSPENDED = 'suspended'
    EXPELED = 'expelled'
    DEFERRED = 'deferred'
    
    CHOICES = [
        (ACTIVE, _('Active')),
        (GRADUATED, _('Graduated')),
        (TRANSFERRED, _('Transferred')),
        (WITHDRAWN, _('Withdrawn')),
        (SUSPENDED, _('Suspended')),
        (EXPELED, _('Expelled')),
        (DEFERRED, _('Deferred')),
    ]
    
    # Valid transitions for state machine
    VALID_TRANSITIONS = {
        ACTIVE: [GRADUATED, TRANSFERRED, WITHDRAWN, SUSPENDED, DEFERRED],
        SUSPENDED: [ACTIVE, EXPELED, WITHDRAWN],
        DEFERRED: [ACTIVE, WITHDRAWN],
        TRANSFERRED: [],  # Terminal state
        WITHDRAWN: [],    # Terminal state
        GRADUATED: [],    # Terminal state
        EXPELED: [],      # Terminal state
    }


class StudentCreationMethod:
    """How the student record was created"""
    
    ADMISSION = 'admission'
    BULK_IMPORT = 'bulk_import'
    MANUAL = 'manual'
    API = 'api'
    
    CHOICES = [
        (ADMISSION, _('Via Admissions')),
        (BULK_IMPORT, _('Bulk Import')),
        (MANUAL, _('Manual Entry')),
        (API, _('API Integration')),
    ]


class GuardianRelationship:
    """Relationship to student"""
    
    FATHER = 'father'
    MOTHER = 'mother'
    GUARDIAN = 'guardian'
    SIBLING = 'sibling'
    OTHER = 'other'
    
    CHOICES = [
        (FATHER, _('Father')),
        (MOTHER, _('Mother')),
        (GUARDIAN, _('Guardian')),
        (SIBLING, _('Sibling')),
        (OTHER, _('Other')),
    ]


class BloodGroup:
    """Blood group for medical records"""
    
    A_POS = 'A+'
    A_NEG = 'A-'
    B_POS = 'B+'
    B_NEG = 'B-'
    O_POS = 'O+'
    O_NEG = 'O-'
    AB_POS = 'AB+'
    AB_NEG = 'AB-'
    
    CHOICES = [
        (A_POS, _('A+')),
        (A_NEG, _('A-')),
        (B_POS, _('B+')),
        (B_NEG, _('B-')),
        (O_POS, _('O+')),
        (O_NEG, _('O-')),
        (AB_POS, _('AB+')),
        (AB_NEG, _('AB-')),
    ]
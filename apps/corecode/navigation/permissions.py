"""
Permission Registry - Centralized permission management
Defines all permissions in the system with metadata for UI display
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from django.utils.translation import gettext_lazy as _


@dataclass
class PermissionDef:
    """Permission definition with metadata"""
    codename: str
    name: str
    app_label: str
    model: str
    description: str = ""
    category: str = "general"
    icon: str = "heroicons:lock-closed"
    
    @property
    def full_codename(self) -> str:
        return f"{self.app_label}.{self.codename}"


@dataclass
class RoleDef:
    """Predefined role definition"""
    name: str
    display_name: str
    description: str
    permissions: List[str]  # List of full codenames
    icon: str = "heroicons:user-group"


class PermissionRegistry:
    """
    Central registry of all system permissions
    Single source of truth for permission definitions
    """
    
    # Corecode Permissions
    ACADEMIC_SESSION = [
        PermissionDef(
            codename="view_academicsession",
            name="View Academic Session",
            app_label="corecode",
            model="academicsession",
            category="academic",
            icon="heroicons:calendar"
        ),
        PermissionDef(
            codename="add_academicsession",
            name="Add Academic Session",
            app_label="corecode",
            model="academicsession",
            category="academic",
            icon="heroicons:plus-circle"
        ),
        PermissionDef(
            codename="change_academicsession",
            name="Change Academic Session",
            app_label="corecode",
            model="academicsession",
            category="academic",
            icon="heroicons:pencil"
        ),
        PermissionDef(
            codename="delete_academicsession",
            name="Delete Academic Session",
            app_label="corecode",
            model="academicsession",
            category="academic",
            icon="heroicons:trash"
        ),
    ]
    
    ACADEMIC_TERM = [
        PermissionDef(
            codename="view_academicterm",
            name="View Academic Term",
            app_label="corecode",
            model="academicterm",
            category="academic",
            icon="heroicons:calendar-days"
        ),
        PermissionDef(
            codename="add_academicterm",
            name="Add Academic Term",
            app_label="corecode",
            model="academicterm",
            category="academic",
            icon="heroicons:plus-circle"
        ),
        PermissionDef(
            codename="change_academicterm",
            name="Change Academic Term",
            app_label="corecode",
            model="academicterm",
            category="academic",
            icon="heroicons:pencil"
        ),
        PermissionDef(
            codename="delete_academicterm",
            name="Delete Academic Term",
            app_label="corecode",
            model="academicterm",
            category="academic",
            icon="heroicons:trash"
        ),
    ]
    
    STUDENT_CLASS = [
        PermissionDef(
            codename="view_studentclass",
            name="View Student Class",
            app_label="corecode",
            model="studentclass",
            category="academic",
            icon="heroicons:academic-cap"
        ),
        PermissionDef(
            codename="change_studentclass",
            name="Change Student Class",
            app_label="corecode",
            model="studentclass",
            category="academic",
            icon="heroicons:pencil"
        ),
    ]
    
    SITE_CONFIG = [
        PermissionDef(
            codename="view_siteconfig",
            name="View Site Configuration",
            app_label="corecode",
            model="siteconfig",
            category="system",
            icon="heroicons:cog"
        ),
        PermissionDef(
            codename="change_siteconfig",
            name="Change Site Configuration",
            app_label="corecode",
            model="siteconfig",
            category="system",
            icon="heroicons:cog-6-tooth"
        ),
    ]
    
    SYSTEM_LOG = [
        PermissionDef(
            codename="view_systemlog",
            name="View System Log",
            app_label="corecode",
            model="systemlog",
            category="system",
            icon="heroicons:clipboard-document-list"
        ),
    ]
    
    # Student Permissions
    STUDENT = [
        PermissionDef(
            codename="view_student",
            name="View Student",
            app_label="students",
            model="student",
            category="student_management",
            icon="heroicons:user"
        ),
        PermissionDef(
            codename="add_student",
            name="Add Student",
            app_label="students",
            model="student",
            category="student_management",
            icon="heroicons:user-plus"
        ),
        PermissionDef(
            codename="change_student",
            name="Change Student",
            app_label="students",
            model="student",
            category="student_management",
            icon="heroicons:user-pencil"
        ),
        PermissionDef(
            codename="delete_student",
            name="Delete Student",
            app_label="students",
            model="student",
            category="student_management",
            icon="heroicons:user-minus"
        ),
        PermissionDef(
            codename="promote_student",
            name="Promote Student",
            app_label="students",
            model="student",
            category="student_management",
            icon="heroicons:arrow-up-circle"
        ),
        PermissionDef(
            codename="bulk_import_students",
            name="Bulk Import Students",
            app_label="students",
            model="student",
            category="student_management",
            icon="heroicons:document-arrow-up"
        ),
    ]
    
    GUARDIAN = [
        PermissionDef(
            codename="view_guardian",
            name="View Guardian",
            app_label="students",
            model="guardian",
            category="student_management",
            icon="heroicons:users"
        ),
        PermissionDef(
            codename="add_guardian",
            name="Add Guardian",
            app_label="students",
            model="guardian",
            category="student_management",
            icon="heroicons:user-plus"
        ),
        PermissionDef(
            codename="change_guardian",
            name="Change Guardian",
            app_label="students",
            model="guardian",
            category="student_management",
            icon="heroicons:pencil"
        ),
        PermissionDef(
            codename="delete_guardian",
            name="Delete Guardian",
            app_label="students",
            model="guardian",
            category="student_management",
            icon="heroicons:trash"
        ),
    ]
    

    ADMISSIONS = [
        PermissionDef(
            codename="view_application",
            name="View Applications",
            app_label="admissions",
            model="application",
            category="admissions",
            icon="heroicons:clipboard-document-list"
        ),
        PermissionDef(
            codename="add_application",
            name="Add Application",
            app_label="admissions",
            model="application",
            category="admissions",
            icon="heroicons:plus-circle"
        ),
        PermissionDef(
            codename="change_application",
            name="Change Application",
            app_label="admissions",
            model="application",
            category="admissions",
            icon="heroicons:pencil"
        ),
        PermissionDef(
            codename="delete_application",
            name="Delete Application",
            app_label="admissions",
            model="application",
            category="admissions",
            icon="heroicons:trash"
        ),
        PermissionDef(
            codename="enroll_applicant",
            name="Enroll Applicant",
            app_label="admissions",
            model="application",
            category="admissions",
            icon="heroicons:user-plus"
        ),
        PermissionDef(
            codename="process_payment",
            name="Process Payments",
            app_label="admissions",
            model="applicationpayment",
            category="admissions",
            icon="heroicons:banknotes"
        ),
    ]

    
    # Predefined Roles (Nigerian School Context)
    ROLES = [
        RoleDef(
            name="proprietor",
            display_name="Proprietor",
            description="School owner with full access",
            permissions=[
                # All permissions (will be populated dynamically)
            ],
            icon="heroicons:building-office"
        ),
        RoleDef(
            name="principal",
            display_name="Principal",
            description="School administrator with academic oversight",
            permissions=[
                "students.view_student",
                "students.promote_student",
                "students.bulk_import_students",
                "corecode.view_academicsession",
                "corecode.change_academicsession",
                "corecode.view_academicterm",
                "corecode.change_academicterm",
                "corecode.view_studentclass",
                "corecode.change_studentclass",
                "corecode.view_siteconfig",
                "corecode.view_systemlog",
            ],
            icon="heroicons:academic-cap"
        ),
        RoleDef(
            name="bursar",
            display_name="Bursar",
            description="Financial officer",
            permissions=[
                "students.view_student",
                # Finance permissions (to be added)
            ],
            icon="heroicons:banknotes"
        ),
        RoleDef(
            name="class_teacher",
            display_name="Class Teacher",
            description="Teacher responsible for a specific class",
            permissions=[
                "students.view_student",
                # Results permissions (to be added)
                # Attendance permissions (to be added)
            ],
            icon="heroicons:user"
        ),
        RoleDef(
            name="admissions_officer",
            display_name="Admissions Officer",
            description="Handles student admissions",
            permissions=[
                "students.view_student",
                "students.add_student",
                # Admissions permissions (to be added)
            ],
            icon="heroicons:clipboard"
        ),
        RoleDef(
            name="parent",
            display_name="Parent/Guardian",
            description="Parent portal access",
            permissions=[
                # Limited read-only permissions
            ],
            icon="heroicons:home"
        ),
    ]
    
    @classmethod
    def get_all_permissions(cls) -> List[PermissionDef]:
        """Get all permissions in the system"""
        permissions = []
        permissions.extend(cls.ACADEMIC_SESSION)
        permissions.extend(cls.ACADEMIC_TERM)
        permissions.extend(cls.STUDENT_CLASS)
        permissions.extend(cls.SITE_CONFIG)
        permissions.extend(cls.SYSTEM_LOG)
        permissions.extend(cls.STUDENT)
        permissions.extend(cls.ADMISSIONS)
        permissions.extend(cls.GUARDIAN)
        return permissions
    
    @classmethod
    def get_permissions_by_category(cls) -> Dict[str, List[PermissionDef]]:
        """Group permissions by category"""
        categories = {}
        for perm in cls.get_all_permissions():
            if perm.category not in categories:
                categories[perm.category] = []
            categories[perm.category].append(perm)
        return categories
    
    @classmethod
    def get_permission(cls, codename: str) -> Optional[PermissionDef]:
        """Get permission definition by codename"""
        for perm in cls.get_all_permissions():
            if perm.codename == codename:
                return perm
        return None
        




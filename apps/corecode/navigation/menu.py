"""
Dynamic Menu Builder - Permission-Based Navigation
GLOBAL navigation system available on ALL pages
"""

from dataclasses import dataclass
from typing import List, Optional, Callable, Dict
from django.urls import reverse, NoReverseMatch
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User


@dataclass
class MenuItem:
    """Navigation menu item definition"""
    label: str
    url: str
    icon: str
    permission: Optional[str] = None
    permission_check: Optional[Callable[[User], bool]] = None
    active: bool = False
    badge: Optional[str] = None
    badge_color: str = "blue"
    children: List['MenuItem'] = None
    order: int = 0
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def has_permission(self, user: User) -> bool:
        """Check if user has permission to see this menu item"""
        if user.is_superuser:
            return True
        
        if self.permission_check:
            try:
                return bool(self.permission_check(user))
            except Exception:
                return False
        
        if self.permission:
            return user.has_perm(self.permission)
        
        if self.children:
            return any(child.has_permission(user) for child in self.children)
        
        return user.is_authenticated
    
    def is_active(self, current_path: str) -> bool:
        """Check if menu item is active based on current path"""
        if current_path == self.url:
            return True
        
        if self.url != '/' and self.url != '#' and current_path.startswith(self.url):
            return True
        
        for child in self.children:
            if child.is_active(current_path):
                return True
        
        return False


class MenuRegistry:
    """Central menu registry - Single source of truth for navigation"""
    
    _main_menu: List[MenuItem] = []
    _user_menu: List[MenuItem] = []
    _footer_menu: List[MenuItem] = []
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialize all menus - called once at startup"""
        if cls._initialized:
            return
        
        cls._main_menu = cls._build_main_menu()
        cls._user_menu = cls._build_user_menu()
        cls._footer_menu = cls._build_footer_menu()
        
        cls._initialized = True
        print(f"[Navigation] Initialized with {len(cls._main_menu)} main items")
    
    @classmethod
    def _safe_reverse(cls, viewname, default='#'):
        """Safely reverse a URL, returning default if it fails."""
        try:
            return reverse(viewname)
        except NoReverseMatch:
            return default
    
    @classmethod
    def _build_main_menu(cls) -> List[MenuItem]:
        """Build the main navigation menu."""
        menu = []
        
        # Dashboard
        menu.append(MenuItem(
            label=_("Dashboard"),
            url=cls._safe_reverse("corecode:dashboard"),
            icon="fas fa-home",
            permission_check=lambda u: u.is_authenticated,
            order=1
        ))
        
        # Students
        students_menu = cls._build_students_menu()
        if students_menu:
            menu.append(students_menu)
        
        # Staff
        staff_menu = cls._build_staff_menu()
        if staff_menu:
            menu.append(staff_menu)
        
        # Admissions
        admissions_menu = cls._build_admissions_menu()
        if admissions_menu:
            menu.append(admissions_menu)
        
        # Finance
        finance_menu = cls._build_finance_menu()
        if finance_menu:
            menu.append(finance_menu)
        
        # Results
        results_menu = cls._build_results_menu()
        if results_menu:
            menu.append(results_menu)
        
        # Attendance
        attendance_menu = cls._build_attendance_menu()
        if attendance_menu:
            menu.append(attendance_menu)
        
        # Timetable (NEW)
        timetable_menu = cls._build_timetable_menu()
        if timetable_menu:
            menu.append(timetable_menu)
        
        # Parents Portal
        parents_menu = cls._build_parents_menu()
        if parents_menu:
            menu.append(parents_menu)
        
        # System
        system_menu = cls._build_system_menu()
        if system_menu:
            menu.append(system_menu)
        
        menu.sort(key=lambda x: x.order)
        return menu
    
    @classmethod
    def _build_students_menu(cls) -> Optional[MenuItem]:
        """Build students submenu."""
        children = []
        
        all_url = cls._safe_reverse("students:list")
        if all_url != '#':
            children.append(MenuItem(
                label=_("All Students"),
                url=all_url,
                icon="fas fa-users",
                permission="students.view_student",
                order=1
            ))
        
        add_url = cls._safe_reverse("students:create")
        if add_url != '#':
            children.append(MenuItem(
                label=_("Add Student"),
                url=add_url,
                icon="fas fa-user-plus",
                permission="students.add_student",
                order=2
            ))
        
        promote_url = cls._safe_reverse("students:promotion")
        if promote_url != '#':
            children.append(MenuItem(
                label=_("Promote Students"),
                url=promote_url,
                icon="fas fa-arrow-up",
                permission="students.promote_student",
                order=3
            ))
        
        bulk_url = cls._safe_reverse("students:bulk_import")
        if bulk_url != '#':
            children.append(MenuItem(
                label=_("Bulk Import"),
                url=bulk_url,
                icon="fas fa-file-import",
                permission="students.bulk_import_students",
                order=4
            ))
        
        if not children:
            return None
        
        children.sort(key=lambda x: x.order)
        
        return MenuItem(
            label=_("Students"),
            url="#",
            icon="fas fa-user-graduate",
            children=children,
            permission_check=lambda u: u.has_perm("students.view_student"),
            order=2
        )
    
    @classmethod
    def _build_staff_menu(cls) -> Optional[MenuItem]:
        """Build staff submenu."""
        children = []
        
        all_url = cls._safe_reverse("staffs:list")
        if all_url != '#':
            children.append(MenuItem(
                label=_("All Staff"),
                url=all_url,
                icon="fas fa-users",
                permission="staffs.view_staff",
                order=1
            ))
        
        add_url = cls._safe_reverse("staffs:create")
        if add_url != '#':
            children.append(MenuItem(
                label=_("Add Staff"),
                url=add_url,
                icon="fas fa-user-plus",
                permission="staffs.add_staff",
                order=2
            ))
        
        attendance_url = cls._safe_reverse("staffs:attendance")
        if attendance_url != '#':
            children.append(MenuItem(
                label=_("Attendance"),
                url=attendance_url,
                icon="fas fa-clock",
                permission="staffs.view_staffattendance",
                order=3
            ))
        
        leave_url = cls._safe_reverse("staffs:leave_list")
        if leave_url != '#':
            children.append(MenuItem(
                label=_("Leave Requests"),
                url=leave_url,
                icon="fas fa-umbrella-beach",
                permission="staffs.view_leaverequest",
                order=4
            ))
        
        # Staff Portal
        portal_url = cls._safe_reverse("staffs:portal_dashboard")
        if portal_url != '#':
            children.append(MenuItem(
                label=_("Staff Portal"),
                url=portal_url,
                icon="fas fa-chalkboard-user",
                permission_check=lambda u: hasattr(u, 'staff_profile'),
                order=5
            ))
        
        if not children:
            return None
        
        children.sort(key=lambda x: x.order)
        
        return MenuItem(
            label=_("Staff"),
            url="#",
            icon="fas fa-chalkboard-teacher",
            children=children,
            permission_check=lambda u: u.has_perm("staffs.view_staff"),
            order=3
        )
    
    @classmethod
    def _build_admissions_menu(cls) -> Optional[MenuItem]:
        """Build admissions submenu."""
        children = []
        
        apps_url = cls._safe_reverse("admissions:list")
        if apps_url != '#':
            children.append(MenuItem(
                label=_("Applications"),
                url=apps_url,
                icon="fas fa-file-alt",
                permission="admissions.view_application",
                order=1
            ))
        
        new_url = cls._safe_reverse("admissions:create")
        if new_url != '#':
            children.append(MenuItem(
                label=_("New Application"),
                url=new_url,
                icon="fas fa-plus-circle",
                permission="admissions.add_application",
                order=2
            ))
        
        # Public Apply link
        apply_url = cls._safe_reverse("admissions:public_apply")
        if apply_url != '#':
            children.append(MenuItem(
                label=_("Public Apply Form"),
                url=apply_url,
                icon="fas fa-globe",
                permission_check=lambda u: u.is_superuser,
                order=3
            ))
        
        if not children:
            return None
        
        children.sort(key=lambda x: x.order)
        
        return MenuItem(
            label=_("Admissions"),
            url="#",
            icon="fas fa-door-open",
            children=children,
            permission_check=lambda u: u.has_perm("admissions.view_application"),
            order=4
        )
    
    @classmethod
    def _build_finance_menu(cls) -> Optional[MenuItem]:
        """Build finance submenu."""
        children = []
        
        dashboard_url = cls._safe_reverse("finance:dashboard")
        if dashboard_url != '#':
            children.append(MenuItem(
                label=_("Dashboard"),
                url=dashboard_url,
                icon="fas fa-chart-pie",
                permission="finance.view_invoice",
                order=1
            ))
        
        invoices_url = cls._safe_reverse("finance:invoice_list")
        if invoices_url != '#':
            children.append(MenuItem(
                label=_("Invoices"),
                url=invoices_url,
                icon="fas fa-file-invoice",
                permission="finance.view_invoice",
                order=2
            ))
        
        create_url = cls._safe_reverse("finance:invoice_create")
        if create_url != '#':
            children.append(MenuItem(
                label=_("Create Invoice"),
                url=create_url,
                icon="fas fa-plus-circle",
                permission="finance.add_invoice",
                order=3
            ))
        
        payment_url = cls._safe_reverse("finance:record_payment")
        if payment_url != '#':
            children.append(MenuItem(
                label=_("Record Payment"),
                url=payment_url,
                icon="fas fa-money-bill-wave",
                permission="finance.add_payment",
                order=4
            ))
        
        if not children:
            return None
        
        children.sort(key=lambda x: x.order)
        
        return MenuItem(
            label=_("Finance"),
            url="#",
            icon="fas fa-coins",
            children=children,
            permission_check=lambda u: u.has_perm("finance.view_invoice"),
            order=5
        )
    
    @classmethod
    def _build_results_menu(cls) -> Optional[MenuItem]:
        """Build results submenu."""
        children = []
        
        dashboard_url = cls._safe_reverse("results:dashboard")
        if dashboard_url != '#':
            children.append(MenuItem(
                label=_("Dashboard"),
                url=dashboard_url,
                icon="fas fa-chart-bar",
                permission="results.view_result",
                order=1
            ))
        
        sheets_url = cls._safe_reverse("results:sheet_list")
        if sheets_url != '#':
            children.append(MenuItem(
                label=_("Result Sheets"),
                url=sheets_url,
                icon="fas fa-file-alt",
                permission="results.view_resultsheet",
                order=2
            ))
        
        create_url = cls._safe_reverse("results:sheet_create")
        if create_url != '#':
            children.append(MenuItem(
                label=_("Create Sheet"),
                url=create_url,
                icon="fas fa-plus-circle",
                permission="results.add_resultsheet",
                order=3
            ))
        
        subjects_url = cls._safe_reverse("results:subject_list")
        if subjects_url != '#':
            children.append(MenuItem(
                label=_("Subjects"),
                url=subjects_url,
                icon="fas fa-book",
                permission="results.view_subject",
                order=4
            ))
        
        if not children:
            return None
        
        children.sort(key=lambda x: x.order)
        
        return MenuItem(
            label=_("Results"),
            url="#",
            icon="fas fa-scroll",
            children=children,
            permission_check=lambda u: u.has_perm("results.view_result"),
            order=6
        )
    
    @classmethod
    def _build_attendance_menu(cls) -> Optional[MenuItem]:
        """Build attendance submenu."""
        children = []
        
        dashboard_url = cls._safe_reverse("attendance:dashboard")
        if dashboard_url != '#':
            children.append(MenuItem(
                label=_("Dashboard"),
                url=dashboard_url,
                icon="fas fa-calendar-check",
                permission="attendance.view_attendanceregister",
                order=1
            ))
        
        registers_url = cls._safe_reverse("attendance:register_list")
        if registers_url != '#':
            children.append(MenuItem(
                label=_("Registers"),
                url=registers_url,
                icon="fas fa-clipboard-list",
                permission="attendance.view_attendanceregister",
                order=2
            ))
        
        new_url = cls._safe_reverse("attendance:register_create")
        if new_url != '#':
            children.append(MenuItem(
                label=_("New Register"),
                url=new_url,
                icon="fas fa-plus-circle",
                permission="attendance.add_attendanceregister",
                order=3
            ))
        
        if not children:
            return None
        
        children.sort(key=lambda x: x.order)
        
        return MenuItem(
            label=_("Attendance"),
            url="#",
            icon="fas fa-calendar-alt",
            children=children,
            permission_check=lambda u: u.has_perm("attendance.view_attendanceregister"),
            order=7
        )
    
    @classmethod
    def _build_timetable_menu(cls) -> Optional[MenuItem]:
        """Build timetable submenu."""
        children = []
        
        # Admin Timetables
        timetables_url = cls._safe_reverse("timetable:timetable_list")
        if timetables_url != '#':
            children.append(MenuItem(
                label=_("Manage Timetables"),
                url=timetables_url,
                icon="fas fa-calendar-alt",
                permission="timetable.view_timetable",
                order=1
            ))
        
        # Teacher Qualifications
        quals_url = cls._safe_reverse("timetable:teacher_qualifications")
        if quals_url != '#':
            children.append(MenuItem(
                label=_("Teacher Qualifications"),
                url=quals_url,
                icon="fas fa-chalkboard-user",
                permission="timetable.change_teacherqualification",
                order=2
            ))
        
        # My Timetable (Staff Portal)
        my_timetable_url = cls._safe_reverse("timetable:my_timetable")
        if my_timetable_url != '#':
            children.append(MenuItem(
                label=_("My Timetable"),
                url=my_timetable_url,
                icon="fas fa-calendar-week",
                permission_check=lambda u: hasattr(u, 'staff_profile'),
                order=3
            ))
        
        if not children:
            return None
        
        children.sort(key=lambda x: x.order)
        
        return MenuItem(
            label=_("Timetable"),
            url="#",
            icon="fas fa-calendar-alt",
            children=children,
            permission_check=lambda u: u.has_perm("timetable.view_timetable") or hasattr(u, 'staff_profile'),
            order=8
        )
    
    @classmethod
    def _build_parents_menu(cls) -> Optional[MenuItem]:
        """Build parents portal admin menu."""
        children = []
        
        portal_url = cls._safe_reverse("parents:dashboard")
        if portal_url != '#':
            children.append(MenuItem(
                label=_("Parent Portal"),
                url=portal_url,
                icon="fas fa-external-link-alt",
                permission_check=lambda u: u.is_superuser,
                order=1
            ))
        
        if not children:
            return None
        
        return MenuItem(
            label=_("Parents Portal"),
            url="#",
            icon="fas fa-child",
            children=children,
            permission_check=lambda u: u.is_superuser,
            order=9
        )
    
    @classmethod
    def _build_system_menu(cls) -> Optional[MenuItem]:
        """Build system administration submenu."""
        children = []
        
        sessions_url = cls._safe_reverse("corecode:session_list")
        if sessions_url != '#':
            children.append(MenuItem(
                label=_("Academic Sessions"),
                url=sessions_url,
                icon="fas fa-calendar",
                permission="corecode.view_academicsession",
                order=1
            ))
        
        terms_url = cls._safe_reverse("corecode:term_manage")
        if terms_url != '#':
            children.append(MenuItem(
                label=_("Academic Terms"),
                url=terms_url,
                icon="fas fa-calendar-week",
                permission="corecode.view_academicterm",
                order=2
            ))
        
        classes_url = cls._safe_reverse("corecode:class_list")
        if classes_url != '#':
            children.append(MenuItem(
                label=_("Classes"),
                url=classes_url,
                icon="fas fa-school",
                permission="corecode.view_studentclass",
                order=3
            ))
        
        config_url = cls._safe_reverse("corecode:system_config")
        if config_url != '#':
            children.append(MenuItem(
                label=_("System Config"),
                url=config_url,
                icon="fas fa-cog",
                permission="corecode.change_siteconfig",
                order=4
            ))
        
        logs_url = cls._safe_reverse("corecode:log_list")
        if logs_url != '#':
            children.append(MenuItem(
                label=_("System Logs"),
                url=logs_url,
                icon="fas fa-history",
                permission="corecode.view_systemlog",
                order=5
            ))
        
        if not children:
            return None
        
        children.sort(key=lambda x: x.order)
        
        return MenuItem(
            label=_("System"),
            url="#",
            icon="fas fa-cogs",
            children=children,
            permission_check=lambda u: u.is_staff or u.is_superuser,
            badge="Admin",
            badge_color="purple",
            order=99
        )
    
    @classmethod
    def _build_user_menu(cls) -> List[MenuItem]:
        """Build user menu (top right dropdown)."""
        menu = []
        
        profile_url = cls._safe_reverse("staffs:portal_profile")
        if profile_url == '#':
            profile_url = cls._safe_reverse("corecode:dashboard")
        
        menu.append(MenuItem(
            label=_("My Profile"),
            url=profile_url,
            icon="fas fa-user",
            order=1
        ))
        
        settings_url = cls._safe_reverse("corecode:system_config")
        if settings_url != '#':
            menu.append(MenuItem(
                label=_("Settings"),
                url=settings_url,
                icon="fas fa-sliders-h",
                permission="corecode.change_siteconfig",
                order=2
            ))
        
        logout_url = cls._safe_reverse("logout")
        if logout_url != '#':
            menu.append(MenuItem(
                label=_("Logout"),
                url=logout_url,
                icon="fas fa-sign-out-alt",
                order=3
            ))
        
        menu.sort(key=lambda x: x.order)
        return menu
    
    @classmethod
    def _build_footer_menu(cls) -> List[MenuItem]:
        """Build footer menu."""
        return [
            MenuItem(label=_("About"), url="/about/", icon="", order=1),
            MenuItem(label=_("Privacy"), url="/privacy/", icon="", order=2),
            MenuItem(label=_("Terms"), url="/terms/", icon="", order=3),
            MenuItem(label=_("Contact"), url="/contact/", icon="", order=4),
        ]
    
    @classmethod
    def get_main_menu(cls, user: User, current_path: str = "") -> List[MenuItem]:
        """Get filtered main menu for a specific user."""
        cls.initialize()
        
        filtered_menu = []
        for item in cls._main_menu:
            if item.has_permission(user):
                menu_item = MenuItem(
                    label=item.label,
                    url=item.url,
                    icon=item.icon,
                    children=[],
                    order=item.order,
                    badge=item.badge,
                    badge_color=item.badge_color,
                )
                
                for child in item.children:
                    if child.has_permission(user):
                        child_copy = MenuItem(
                            label=child.label,
                            url=child.url,
                            icon=child.icon,
                            badge=child.badge,
                            badge_color=child.badge_color,
                            order=child.order,
                        )
                        child_copy.active = child_copy.is_active(current_path)
                        menu_item.children.append(child_copy)
                
                menu_item.children.sort(key=lambda x: x.order)
                menu_item.active = menu_item.is_active(current_path)
                filtered_menu.append(menu_item)
        
        filtered_menu.sort(key=lambda x: x.order)
        return filtered_menu
    
    @classmethod
    def get_user_menu(cls, user: User, current_path: str = "") -> List[MenuItem]:
        """Get user menu for a specific user."""
        cls.initialize()
        
        filtered_menu = []
        for item in cls._user_menu:
            if item.has_permission(user):
                menu_item = MenuItem(
                    label=item.label,
                    url=item.url,
                    icon=item.icon,
                    order=item.order,
                    active=item.is_active(current_path)
                )
                filtered_menu.append(menu_item)
        
        filtered_menu.sort(key=lambda x: x.order)
        return filtered_menu
    
    @classmethod
    def get_footer_menu(cls, user: User) -> List[MenuItem]:
        """Get footer menu."""
        cls.initialize()
        return cls._footer_menu
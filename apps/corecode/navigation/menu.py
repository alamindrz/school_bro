"""
Dynamic Menu Builder - Permission-Based Navigation
GLOBAL navigation system available on ALL pages
No hardcoded roles. Menu items are shown based on user permissions.
SAFE initialization with URL existence checks.
"""

from dataclasses import dataclass
from typing import List, Optional, Callable, Dict
from django.urls import reverse, NoReverseMatch
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.conf import settings


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
    order: int = 0  # For sorting menu items
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def has_permission(self, user: User) -> bool:
        """Check if user has permission to see this menu item"""
        # Superusers see everything
        if user.is_superuser:
            return True
        
        # If there's a custom permission check function, use it
        if self.permission_check:
            try:
                result = self.permission_check(user)
                return bool(result)
            except Exception:
                return False
        
        # If there's a single permission, check it
        if self.permission:
            return user.has_perm(self.permission)
        
        # If there are children, check if any child is visible
        if self.children:
            return any(child.has_permission(user) for child in self.children)
        
        # No permission requirements - visible to all authenticated users
        return user.is_authenticated
    
    def is_active(self, current_path: str) -> bool:
        """Check if menu item is active based on current path"""
        # Exact match
        if current_path == self.url:
            return True
        
        # Starts with (for sections) - but not root
        if self.url != '/' and self.url != '#' and current_path.startswith(self.url):
            return True
        
        # Check children
        if self.children:
            for child in self.children:
                if child.is_active(current_path):
                    return True
        
        return False


class MenuRegistry:
    """
    Central menu registry - Builds dynamic menus based on permissions
    This is the SINGLE SOURCE OF TRUTH for all navigation
    """
    
    # Store menu items by position
    _main_menu: List[MenuItem] = []
    _user_menu: List[MenuItem] = []
    _footer_menu: List[MenuItem] = []
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialize all menus - called once at startup"""
        if cls._initialized:
            return
        
        # Build main navigation menu
        cls._main_menu = cls._build_main_menu()
        
        # Build user menu (top right)
        cls._user_menu = cls._build_user_menu()
        
        # Build footer menu
        cls._footer_menu = cls._build_footer_menu()
        
        cls._initialized = True
        print(f"[Navigation] Initialized with {len(cls._main_menu)} main items")
    
    @classmethod
    def _safe_reverse(cls, viewname, default='#'):
        """
        Safely reverse a URL, returning default if it fails.
        
        Args:
            viewname: URL pattern name to reverse
            default: Default URL to return if reverse fails
            
        Returns:
            Resolved URL or default
        """
        try:
            return reverse(viewname)
        except NoReverseMatch:
            return default
    
    @classmethod
    def _build_main_menu(cls) -> List[MenuItem]:
        """Build the main navigation menu."""
        menu = []
        
        # Dashboard - Always visible to authenticated users
        menu.append(MenuItem(
            label=_("Dashboard"),
            url=cls._safe_reverse("corecode:dashboard"),
            icon="fas fa-home",
            permission_check=lambda u: u.is_authenticated,
            order=1
        ))
        
        # Students Menu
        students_menu = cls._build_students_menu()
        if students_menu:
            menu.append(students_menu)
        
        # Staff Menu
        staff_menu = cls._build_staff_menu()
        if staff_menu:
            menu.append(staff_menu)
        
        # Admissions Menu
        admissions_menu = cls._build_admissions_menu()
        if admissions_menu:
            menu.append(admissions_menu)
        
        # Finance Menu
        finance_menu = cls._build_finance_menu()
        if finance_menu:
            menu.append(finance_menu)
        
        # Results Menu
        results_menu = cls._build_results_menu()
        if results_menu:
            menu.append(results_menu)
        
        # Attendance Menu
        attendance_menu = cls._build_attendance_menu()
        if attendance_menu:
            menu.append(attendance_menu)
        
        # Parents Menu (only for admin)
        parents_menu = cls._build_parents_menu()
        if parents_menu:
            menu.append(parents_menu)
        
        # System Menu (Admin only)
        system_menu = cls._build_system_menu()
        if system_menu:
            menu.append(system_menu)
        
        # Sort by order
        menu.sort(key=lambda x: x.order)
        
        return menu
    
    @classmethod
    def _build_students_menu(cls) -> Optional[MenuItem]:
        """Build students submenu."""
        children = []
        
        # All Students
        students_url = cls._safe_reverse("students:list")
        if students_url != '#':
            children.append(MenuItem(
                label=_("All Students"),
                url=students_url,
                icon="fas fa-users",
                permission="students.view_student",
                order=1
            ))
        
        # Add Student
        add_url = cls._safe_reverse("students:create")
        if add_url != '#':
            children.append(MenuItem(
                label=_("Add Student"),
                url=add_url,
                icon="fas fa-user-plus",
                permission="students.add_student",
                order=2
            ))
        
        # Promote Students
        promote_url = cls._safe_reverse("students:promotion")
        if promote_url != '#':
            children.append(MenuItem(
                label=_("Promote Students"),
                url=promote_url,
                icon="fas fa-arrow-up",
                permission="students.promote_student",
                order=3
            ))
        
        # Bulk Import
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
        
        # Sort children
        children.sort(key=lambda x: x.order)
        
        return MenuItem(
            label=_("Students"),
            url="#",
            icon="fas fa-user-graduate",
            children=children,
            permission_check=lambda u: any([
                u.has_perm("students.view_student"),
                u.has_perm("students.add_student"),
                u.has_perm("students.change_student")
            ]),
            order=2
        )
    
    @classmethod
    def _build_staff_menu(cls) -> Optional[MenuItem]:
        """Build staff submenu."""
        children = []
        
        # All Staff
        staff_url = cls._safe_reverse("staffs:list")
        if staff_url != '#':
            children.append(MenuItem(
                label=_("All Staff"),
                url=staff_url,
                icon="fas fa-users",
                permission="staffs.view_staff",
                order=1
            ))
        
        # Add Staff
        add_url = cls._safe_reverse("staffs:create")
        if add_url != '#':
            children.append(MenuItem(
                label=_("Add Staff"),
                url=add_url,
                icon="fas fa-user-plus",
                permission="staffs.add_staff",
                order=2
            ))
        
        # Attendance
        attendance_url = cls._safe_reverse("staffs:attendance")
        if attendance_url != '#':
            children.append(MenuItem(
                label=_("Attendance"),
                url=attendance_url,
                icon="fas fa-clock",
                permission="staffs.view_staffattendance",
                order=3
            ))
        
        # Leave Requests
        leave_url = cls._safe_reverse("staffs:leave_list")
        if leave_url != '#':
            children.append(MenuItem(
                label=_("Leave Requests"),
                url=leave_url,
                icon="fas fa-umbrella-beach",
                permission="staffs.view_leaverequest",
                order=4
            ))
        
        if not children:
            return None
        
        children.sort(key=lambda x: x.order)
        
        return MenuItem(
            label=_("Staff"),
            url="#",
            icon="fas fa-chalkboard-teacher",
            children=children,
            permission_check=lambda u: any([
                u.has_perm("staffs.view_staff"),
                u.has_perm("staffs.add_staff")
            ]),
            order=3
        )
    
    @classmethod
    def _build_admissions_menu(cls) -> Optional[MenuItem]:
        """Build admissions submenu."""
        children = []
        
        # Applications
        apps_url = cls._safe_reverse("admissions:list")
        if apps_url != '#':
            children.append(MenuItem(
                label=_("Applications"),
                url=apps_url,
                icon="fas fa-file-alt",
                permission="admissions.view_application",
                order=1
            ))
        
        # New Application
        new_url = cls._safe_reverse("admissions:create")
        if new_url != '#':
            children.append(MenuItem(
                label=_("New Application"),
                url=new_url,
                icon="fas fa-plus-circle",
                permission="admissions.add_application",
                order=2
            ))
        
        # Pending Review
        pending_url = cls._safe_reverse("admissions:list")
        if pending_url != '#':
            children.append(MenuItem(
                label=_("Pending Review"),
                url=f"{pending_url}?status=submitted",
                icon="fas fa-hourglass-half",
                permission="admissions.view_application",
                badge="pending",
                badge_color="yellow",
                order=3
            ))
        
        # Approved
        approved_url = cls._safe_reverse("admissions:list")
        if approved_url != '#':
            children.append(MenuItem(
                label=_("Approved"),
                url=f"{approved_url}?status=approved",
                icon="fas fa-check-circle",
                permission="admissions.view_application",
                order=4
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
        
        # Dashboard
        dashboard_url = cls._safe_reverse("finance:dashboard")
        if dashboard_url != '#':
            children.append(MenuItem(
                label=_("Dashboard"),
                url=dashboard_url,
                icon="fas fa-chart-pie",
                permission="finance.view_invoice",
                order=1
            ))
        
        # Invoices
        invoices_url = cls._safe_reverse("finance:invoice_list")
        if invoices_url != '#':
            children.append(MenuItem(
                label=_("Invoices"),
                url=invoices_url,
                icon="fas fa-file-invoice",
                permission="finance.view_invoice",
                order=2
            ))
        
        # Create Invoice
        create_url = cls._safe_reverse("finance:invoice_create")
        if create_url != '#':
            children.append(MenuItem(
                label=_("Create Invoice"),
                url=create_url,
                icon="fas fa-plus-circle",
                permission="finance.add_invoice",
                order=3
            ))
        
        # Record Payment
        payment_url = cls._safe_reverse("finance:record_payment")
        if payment_url != '#':
            children.append(MenuItem(
                label=_("Record Payment"),
                url=payment_url,
                icon="fas fa-money-bill-wave",
                permission="finance.add_payment",
                order=4
            ))
        
        # Fee Structure
        fee_url = cls._safe_reverse("finance:bulk_invoice")
        if fee_url != '#':
            children.append(MenuItem(
                label=_("Fee Structure"),
                url=fee_url,
                icon="fas fa-cubes",
                permission="finance.view_feestructure",
                order=5
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
        
        # Dashboard
        dashboard_url = cls._safe_reverse("results:dashboard")
        if dashboard_url != '#':
            children.append(MenuItem(
                label=_("Dashboard"),
                url=dashboard_url,
                icon="fas fa-chart-bar",
                permission="results.view_result",
                order=1
            ))
        
        # Result Sheets
        sheets_url = cls._safe_reverse("results:sheet_list")
        if sheets_url != '#':
            children.append(MenuItem(
                label=_("Result Sheets"),
                url=sheets_url,
                icon="fas fa-file-alt",
                permission="results.view_resultsheet",
                order=2
            ))
        
        # Create Sheet
        create_url = cls._safe_reverse("results:sheet_create")
        if create_url != '#':
            children.append(MenuItem(
                label=_("Create Sheet"),
                url=create_url,
                icon="fas fa-plus-circle",
                permission="results.add_resultsheet",
                order=3
            ))
        
        # Subjects
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
        
        # Dashboard
        dashboard_url = cls._safe_reverse("attendance:dashboard")
        if dashboard_url != '#':
            children.append(MenuItem(
                label=_("Dashboard"),
                url=dashboard_url,
                icon="fas fa-calendar-check",
                permission="attendance.view_attendanceregister",
                order=1
            ))
        
        # Registers
        registers_url = cls._safe_reverse("attendance:register_list")
        if registers_url != '#':
            children.append(MenuItem(
                label=_("Registers"),
                url=registers_url,
                icon="fas fa-clipboard-list",
                permission="attendance.view_attendanceregister",
                order=2
            ))
        
        # New Register
        new_url = cls._safe_reverse("attendance:register_create")
        if new_url != '#':
            children.append(MenuItem(
                label=_("New Register"),
                url=new_url,
                icon="fas fa-plus-circle",
                permission="attendance.add_attendanceregister",
                order=3
            ))
        
        # QR Codes
        qr_url = cls._safe_reverse("attendance:qrcodes")
        if qr_url != '#':
            children.append(MenuItem(
                label=_("QR Codes"),
                url=qr_url,
                icon="fas fa-qrcode",
                permission="attendance.view_qrcode",
                order=4
            ))
        
        # Reports
        reports_url = cls._safe_reverse("attendance:reports")
        if reports_url != '#':
            children.append(MenuItem(
                label=_("Reports"),
                url=reports_url,
                icon="fas fa-chart-line",
                permission="attendance.view_attendancereport",
                order=5
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
    def _build_parents_menu(cls) -> Optional[MenuItem]:
        """Build parents portal admin menu - with URL existence check."""
        children = []
        
        # Parent Profiles link (admin)
        try:
            parent_profile_url = reverse("admin:parents_parentprofile_changelist")
            children.append(MenuItem(
                label=_("Parent Profiles"),
                url=parent_profile_url,
                icon="fas fa-users",
                permission="parents.view_parentprofile",
                order=1
            ))
        except NoReverseMatch:
            pass
        
        # Notifications link (admin)
        try:
            notification_url = reverse("admin:parents_notification_changelist")
            children.append(MenuItem(
                label=_("Notifications"),
                url=notification_url,
                icon="fas fa-bell",
                permission="parents.view_notification",
                order=2
            ))
        except NoReverseMatch:
            pass
        
        # Messages link (admin)
        try:
            messages_url = reverse("admin:parents_message_changelist")
            children.append(MenuItem(
                label=_("Messages"),
                url=messages_url,
                icon="fas fa-envelope",
                permission="parents.view_message",
                order=3
            ))
        except NoReverseMatch:
            pass
        
        # Portal Sessions link (admin)
        try:
            sessions_url = reverse("admin:parents_portalsession_changelist")
            children.append(MenuItem(
                label=_("Portal Sessions"),
                url=sessions_url,
                icon="fas fa-clock",
                permission="parents.view_portalsession",
                order=4
            ))
        except NoReverseMatch:
            pass
        
        # Access Logs link (admin)
        try:
            logs_url = reverse("admin:parents_parentaccesslog_changelist")
            children.append(MenuItem(
                label=_("Access Logs"),
                url=logs_url,
                icon="fas fa-history",
                permission="parents.view_parentaccesslog",
                order=5
            ))
        except NoReverseMatch:
            pass
        
        # Parent Portal frontend link
        portal_url = cls._safe_reverse("parents:dashboard")
        if portal_url != '#':
            children.append(MenuItem(
                label=_("Parent Portal"),
                url=portal_url,
                icon="fas fa-external-link-alt",
                permission="parents.view_parentprofile",
                order=6
            ))
        
        if not children:
            return None
        
        children.sort(key=lambda x: x.order)
        
        return MenuItem(
            label=_("Parents Portal"),
            url="#",
            icon="fas fa-child",
            children=children,
            permission_check=lambda u: u.is_superuser,
            order=8
        )
    
    @classmethod
    def _build_system_menu(cls) -> Optional[MenuItem]:
        """Build system administration submenu."""
        children = []
        
        # Academic Sessions
        sessions_url = cls._safe_reverse("corecode:session_list")
        if sessions_url != '#':
            children.append(MenuItem(
                label=_("Academic Sessions"),
                url=sessions_url,
                icon="fas fa-calendar",
                permission="corecode.view_academicsession",
                order=1
            ))
        
        # Academic Terms
        terms_url = cls._safe_reverse("corecode:term_manage")
        if terms_url != '#':
            children.append(MenuItem(
                label=_("Academic Terms"),
                url=terms_url,
                icon="fas fa-calendar-week",
                permission="corecode.view_academicterm",
                order=2
            ))
        
        # Classes
        classes_url = cls._safe_reverse("corecode:class_list")
        if classes_url != '#':
            children.append(MenuItem(
                label=_("Classes"),
                url=classes_url,
                icon="fas fa-school",
                permission="corecode.view_studentclass",
                order=3
            ))
        
        # System Config
        config_url = cls._safe_reverse("corecode:system_config")
        if config_url != '#':
            children.append(MenuItem(
                label=_("System Config"),
                url=config_url,
                icon="fas fa-cog",
                permission="corecode.change_siteconfig",
                order=4
            ))
        
        # Audit Logs (try both audit app and corecode fallback)
        try:
            # Try audit app first
            audit_url = reverse("audit:dashboard")
            children.append(MenuItem(
                label=_("Audit Logs"),
                url=audit_url,
                icon="fas fa-history",
                permission="audit.view_auditlog",
                order=5
            ))
        except NoReverseMatch:
            # Fallback to corecode logs
            logs_url = cls._safe_reverse("corecode:log_list")
            if logs_url != '#':
                children.append(MenuItem(
                    label=_("System Logs"),
                    url=logs_url,
                    icon="fas fa-history",
                    permission="corecode.view_systemlog",
                    order=5
                ))
        
        # Notifications Admin
        try:
            notif_url = reverse("admin:notifications_notification_changelist")
            children.append(MenuItem(
                label=_("Notifications"),
                url=notif_url,
                icon="fas fa-bell",
                permission="notifications.view_notification",
                order=6
            ))
        except NoReverseMatch:
            pass
        
        if not children:
            return None
        
        system_perms = [
            "corecode.view_academicsession",
            "corecode.view_academicterm",
            "corecode.view_studentclass",
            "corecode.view_siteconfig",
            "corecode.view_systemlog",
            "audit.view_auditlog",
            "notifications.view_notification"
        ]
        
        children.sort(key=lambda x: x.order)
        
        return MenuItem(
            label=_("System"),
            url="#",
            icon="fas fa-cogs",
            children=children,
            permission_check=lambda u: u.is_staff or u.is_superuser or any(
                u.has_perm(perm) for perm in system_perms
            ),
            badge="Admin",
            badge_color="purple",
            order=99
        )
    
    @classmethod
    def _build_user_menu(cls) -> List[MenuItem]:
        """Build user menu (top right dropdown)."""
        menu = []
        
        # My Profile
        profile_url = cls._safe_reverse("staffs:profile")
        if profile_url == '#':
            profile_url = cls._safe_reverse("corecode:dashboard")
        
        menu.append(MenuItem(
            label=_("My Profile"),
            url=profile_url,
            icon="fas fa-user",
            order=1
        ))
        
        # Settings
        settings_url = cls._safe_reverse("corecode:system_config")
        if settings_url != '#':
            menu.append(MenuItem(
                label=_("Settings"),
                url=settings_url,
                icon="fas fa-sliders-h",
                permission="corecode.change_siteconfig",
                order=2
            ))
        
        # Help
        help_url = cls._safe_reverse("corecode:help")
        if help_url == '#':
            help_url = "/help/"
        
        menu.append(MenuItem(
            label=_("Help"),
            url=help_url,
            icon="fas fa-question-circle",
            order=3
        ))
        
        # Logout
        logout_url = cls._safe_reverse("logout")
        if logout_url != '#':
            menu.append(MenuItem(
                label=_("Logout"),
                url=logout_url,
                icon="fas fa-sign-out-alt",
                order=4
            ))
        
        menu.sort(key=lambda x: x.order)
        return menu
    
    @classmethod
    def _build_footer_menu(cls) -> List[MenuItem]:
        """Build footer menu (optional)."""
        return [
            MenuItem(
                label=_("About"),
                url="/about/",
                icon="",
                order=1
            ),
            MenuItem(
                label=_("Privacy Policy"),
                url="/privacy/",
                icon="",
                order=2
            ),
            MenuItem(
                label=_("Terms of Service"),
                url="/terms/",
                icon="",
                order=3
            ),
            MenuItem(
                label=_("Contact"),
                url="/contact/",
                icon="",
                order=4
            ),
        ]
    
    @classmethod
    def get_main_menu(cls, user: User, current_path: str = "") -> List[MenuItem]:
        """Get filtered main menu for a specific user."""
        cls.initialize()
        
        filtered_menu = []
        for item in cls._main_menu:
            if item.has_permission(user):
                # Clone the item to avoid modifying the original
                menu_item = MenuItem(
                    label=item.label,
                    url=item.url,
                    icon=item.icon,
                    children=[],  # Will filter children
                    order=item.order,
                    badge=item.badge,
                    badge_color=item.badge_color,
                )
                
                # Filter children
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
                
                # Sort children by order
                menu_item.children.sort(key=lambda x: x.order)
                
                # Check if this item is active
                menu_item.active = menu_item.is_active(current_path)
                
                filtered_menu.append(menu_item)
        
        # Sort main menu by order
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
        """Get footer menu (usually no permissions needed)."""
        cls.initialize()
        return cls._footer_menu
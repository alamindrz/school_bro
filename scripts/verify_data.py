#!/usr/bin/env python
"""
Django Shell Script to Verify Data Creation
Run: python manage.py shell < scripts/verify_data.py
OR: python manage.py shell -c "exec(open('scripts/verify_data.py').read())"

This script checks if data exists in the database and verifies
that templates would be able to display it.
"""

import os
import sys
from collections import Counter
from datetime import date, datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

# Import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models import Count, Sum, Avg

# Corecode
from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass, SiteConfig, SystemLog

# Students
from apps.students.models import Student, Guardian, StudentHistory

# Staff
from apps.staffs.models import Staff, SubjectAssignment, DutyAssignment, LeaveRequest, StaffAttendance

# Admissions
from apps.admissions.models import Application, ApplicationPayment

# Finance
from apps.finance.models import FeeStructure, Invoice, Payment, FeeWaiver

# Results
from apps.results.models import Subject, ResultSheet, Result, ResultComment

# Attendance
from apps.attendance.models import AttendanceRegister, AttendanceRecord, AttendanceSummary

# Parents
from apps.parents.models import ParentProfile, ChildLink, Notification as ParentNotification

# Notifications
from apps.notifications.models import Notification, NotificationTemplate

# Audit
from apps.audit.models import AuditLog

User = get_user_model()


class DataVerifier:
    """Verify that data exists and templates can access it"""
    
    def __init__(self):
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
        self.stats = {}
    
    def run(self):
        """Run all verification checks"""
        print("\n" + "="*60)
        print("🔍 DATA VERIFICATION REPORT")
        print("="*60)
        
        self.check_users()
        self.check_corecode()
        self.check_students()
        self.check_staff()
        self.check_admissions()
        self.check_finance()
        self.check_results()
        self.check_attendance()
        self.check_parents()
        self.check_notifications()
        self.check_audit()
        self.check_relationships()
        self.check_template_access()
        
        self.print_summary()
    
    def check_users(self):
        """Verify user accounts"""
        print("\n👤 USER ACCOUNTS")
        print("-" * 40)
        
        total_users = User.objects.count()
        admin_count = User.objects.filter(is_superuser=True).count()
        staff_count = User.objects.filter(is_staff=True).count()
        active_users = User.objects.filter(is_active=True).count()
        
        self.stats['users'] = {
            'total': total_users,
            'admins': admin_count,
            'staff': staff_count,
            'active': active_users
        }
        
        print(f"Total Users: {total_users}")
        print(f"  ├─ Admin Users: {admin_count}")
        print(f"  ├─ Staff Users: {staff_count}")
        print(f"  └─ Active Users: {active_users}")
        
        if total_users == 0:
            self.results['failed'].append("❌ No users found - authentication will fail")
        elif total_users < 5:
            self.results['warnings'].append("⚠️  Very few users ({})".format(total_users))
        else:
            self.results['passed'].append("✅ Users present: {}".format(total_users))
        
        # Check specific test users
        test_users = ['admin', 'teacher_1', 'student_1']
        for username in test_users:
            if User.objects.filter(username=username).exists():
                print(f"  ✅ Test user '{username}' exists")
            else:
                print(f"  ⚠️  Test user '{username}' not found")
    
    def check_corecode(self):
        """Verify corecode data"""
        print("\n🏛️  CORECODE (Foundation)")
        print("-" * 40)
        
        # Academic Sessions
        sessions = AcademicSession.objects.all()
        current_session = AcademicSession.objects.filter(is_current=True).first()
        print(f"Academic Sessions: {sessions.count()}")
        if current_session:
            print(f"  ├─ Current: {current_session.name}")
            print(f"  ├─ Start: {current_session.start_date}")
            print(f"  └─ End: {current_session.end_date}")
        
        # Academic Terms
        terms = AcademicTerm.objects.all()
        current_term = AcademicTerm.objects.filter(is_current=True).first()
        print(f"Academic Terms: {terms.count()}")
        if current_term:
            print(f"  ├─ Current: {current_term.name}")
            print(f"  ├─ Session: {current_term.session.name}")
            print(f"  └─ Date Range: {current_term.start_date} to {current_term.end_date}")
        
        # Student Classes
        classes = StudentClass.objects.all()
        active_classes = StudentClass.objects.filter(is_active=True)
        print(f"Student Classes: {classes.count()} total, {active_classes.count()} active")
        
        # List all classes with their levels
        for class_obj in classes.order_by('sort_order'):
            print(f"  ├─ {class_obj.display_name} ({class_obj.get_education_level_display()}) - {class_obj.max_students} capacity")
        
        # Site Config
        configs = SiteConfig.objects.all()
        print(f"Site Configurations: {configs.count()}")
        
        # Store stats
        self.stats['corecode'] = {
            'sessions': sessions.count(),
            'terms': terms.count(),
            'classes': classes.count(),
            'configs': configs.count()
        }
        
        if sessions.count() == 0:
            self.results['failed'].append("❌ No academic sessions - templates will show errors")
        elif sessions.count() < 2:
            self.results['warnings'].append("⚠️  Only {} academic session".format(sessions.count()))
        else:
            self.results['passed'].append("✅ Academic sessions: {}".format(sessions.count()))
        
        if classes.count() < 15:
            self.results['failed'].append("❌ Only {} classes (should be 15 for Nigerian 6-3-3-4)".format(classes.count()))
        else:
            self.results['passed'].append("✅ All {} Nigerian classes present".format(classes.count()))
    
    def check_students(self):
        """Verify student data"""
        print("\n🎓 STUDENTS")
        print("-" * 40)
        
        total_students = Student.objects.count()
        active_students = Student.objects.filter(status='active').count()
        graduated = Student.objects.filter(status='graduated').count()
        suspended = Student.objects.filter(status='suspended').count()
        
        print(f"Total Students: {total_students}")
        print(f"  ├─ Active: {active_students}")
        print(f"  ├─ Graduated: {graduated}")
        print(f"  └─ Suspended: {suspended}")
        
        # Students by class
        print("\nStudents by Class:")
        for class_obj in StudentClass.objects.filter(is_active=True).order_by('sort_order'):
            count = Student.objects.filter(current_class=class_obj, status='active').count()
            capacity = class_obj.max_students
            percentage = (count / capacity * 100) if capacity > 0 else 0
            bar = '█' * int(percentage / 10) + '░' * (10 - int(percentage / 10))
            print(f"  ├─ {class_obj.display_name:12} : {count:3}/{capacity:3} [{bar}] {percentage:.1f}%")
        
        # Guardians
        guardians = Guardian.objects.count()
        print(f"\nGuardians: {guardians}")
        
        # Student History
        history = StudentHistory.objects.count()
        print(f"Student History Records: {history}")
        
        self.stats['students'] = {
            'total': total_students,
            'active': active_students,
            'guardians': guardians,
            'history': history
        }
        
        if total_students == 0:
            self.results['failed'].append("❌ No students - student list templates will be empty")
        elif total_students < 10:
            self.results['warnings'].append("⚠️  Very few students ({})".format(total_students))
        else:
            self.results['passed'].append("✅ Students present: {}".format(total_students))
    
    def check_staff(self):
        """Verify staff data"""
        print("\n👥 STAFF")
        print("-" * 40)
        
        total_staff = Staff.objects.count()
        active_staff = Staff.objects.filter(employment_status='active').count()
        on_leave = Staff.objects.filter(employment_status='on_leave').count()
        
        print(f"Total Staff: {total_staff}")
        print(f"  ├─ Active: {active_staff}")
        print(f"  ├─ On Leave: {on_leave}")
        print(f"  └─ Other: {total_staff - active_staff - on_leave}")
        
        # Staff by category
        print("\nStaff by Category:")
        from apps.staffs.constants import StaffCategory
        for cat_code, cat_label in StaffCategory.CHOICES:
            count = Staff.objects.filter(staff_category=cat_code).count()
            if count > 0:
                print(f"  ├─ {cat_label}: {count}")
        
        # Subject Assignments
        assignments = SubjectAssignment.objects.count()
        print(f"\nSubject Assignments: {assignments}")
        
        # Duty Assignments
        duties = DutyAssignment.objects.filter(is_active=True).count()
        print(f"Active Duty Assignments: {duties}")
        
        # Leave Requests
        leaves = LeaveRequest.objects.count()
        pending_leaves = LeaveRequest.objects.filter(status='pending').count()
        print(f"Leave Requests: {leaves} (Pending: {pending_leaves})")
        
        # Staff Attendance
        today = date.today()
        today_attendance = StaffAttendance.objects.filter(date=today).count()
        print(f"Today's Staff Attendance: {today_attendance}")
        
        self.stats['staff'] = {
            'total': total_staff,
            'active': active_staff,
            'assignments': assignments,
            'leaves': leaves
        }
        
        if total_staff == 0:
            self.results['failed'].append("❌ No staff - staff templates will be empty")
        elif total_staff < 5:
            self.results['warnings'].append("⚠️  Very few staff ({})".format(total_staff))
        else:
            self.results['passed'].append("✅ Staff present: {}".format(total_staff))
    
    def check_admissions(self):
        """Verify admissions data"""
        print("\n📋 ADMISSIONS")
        print("-" * 40)
        
        total_apps = Application.objects.count()
        print(f"Total Applications: {total_apps}")
        
        # Applications by status
        from apps.admissions.constants import ApplicationStatus
        print("\nApplications by Status:")
        for status_code, status_label in ApplicationStatus.CHOICES:
            count = Application.objects.filter(status=status_code).count()
            if count > 0:
                print(f"  ├─ {status_label}: {count}")
        
        # Applications with payments
        paid_apps = ApplicationPayment.objects.filter(status='completed').count()
        print(f"\nPaid Applications: {paid_apps}")
        
        self.stats['admissions'] = {
            'total': total_apps,
            'paid': paid_apps
        }
        
        if total_apps == 0:
            self.results['warnings'].append("⚠️  No applications - admissions templates will show empty states")
        else:
            self.results['passed'].append("✅ Applications present: {}".format(total_apps))
    
    def check_finance(self):
        """Verify finance data"""
        print("\n💰 FINANCE"
        "-" * 40)
        
        # Fee Structures
        fee_structures = FeeStructure.objects.count()
        print(f"Fee Structures: {fee_structures}")
        
        # Invoices
        total_invoices = Invoice.objects.count()
        paid_invoices = Invoice.objects.filter(status='paid').count()
        pending_invoices = Invoice.objects.filter(status__in=['pending', 'partial']).count()
        overdue_invoices = Invoice.objects.filter(status='overdue').count()
        
        print(f"Invoices: {total_invoices}")
        print(f"  ├─ Paid: {paid_invoices}")
        print(f"  ├─ Pending/Partial: {pending_invoices}")
        print(f"  └─ Overdue: {overdue_invoices}")
        
        # Total amounts
        total_invoiced = Invoice.objects.aggregate(total=models.Sum('total'))['total'] or 0
        total_collected = Invoice.objects.aggregate(total=models.Sum('amount_paid'))['total'] or 0
        total_outstanding = Invoice.objects.aggregate(total=models.Sum('balance'))['total'] or 0
        
        print(f"\nFinancial Summary:")
        print(f"  ├─ Total Invoiced: ₦{total_invoiced:,.2f}")
        print(f"  ├─ Total Collected: ₦{total_collected:,.2f}")
        print(f"  └─ Outstanding: ₦{total_outstanding:,.2f}")
        
        # Payments
        payments = Payment.objects.count()
        print(f"\nPayments Recorded: {payments}")
        
        self.stats['finance'] = {
            'invoices': total_invoices,
            'payments': payments,
            'total_collected': float(total_collected)
        }
        
        if total_invoices == 0:
            self.results['warnings'].append("⚠️  No invoices - finance templates will show empty states")
        else:
            self.results['passed'].append("✅ Invoices present: {}".format(total_invoices))
    
    def check_results(self):
        """Verify results data"""
        print("\n📊 RESULTS"
        "-" * 40)
        
        # Subjects
        subjects = Subject.objects.count()
        print(f"Subjects: {subjects}")
        
        # Result Sheets
        sheets = ResultSheet.objects.count()
        published_sheets = ResultSheet.objects.filter(status='published').count()
        print(f"Result Sheets: {sheets} (Published: {published_sheets})")
        
        # Individual Results
        results = Result.objects.count()
        print(f"Individual Results: {results}")
        
        # Results by grade
        if results > 0:
            print("\nGrade Distribution:")
            for grade in ['A1', 'B2', 'B3', 'C4', 'C5', 'C6', 'D7', 'E8', 'F9']:
                count = Result.objects.filter(grade=grade).count()
                if count > 0:
                    percentage = (count / results * 100)
                    print(f"  ├─ {grade}: {count} ({percentage:.1f}%)")
        
        self.stats['results'] = {
            'subjects': subjects,
            'sheets': sheets,
            'results': results
        }
        
        if results == 0:
            self.results['warnings'].append("⚠️  No results - results templates will show empty states")
        else:
            self.results['passed'].append("✅ Results present: {}".format(results))
    
    def check_attendance(self):
        """Verify attendance data"""
        print("\n📅 ATTENDANCE"
        "-" * 40)
        
        # Attendance Registers
        registers = AttendanceRegister.objects.count()
        today_registers = AttendanceRegister.objects.filter(date=date.today()).count()
        print(f"Attendance Registers: {registers}")
        print(f"  └─ Today's Registers: {today_registers}")
        
        # Attendance Records
        records = AttendanceRecord.objects.count()
        print(f"Attendance Records: {records}")
        
        # Today's attendance summary
        today = date.today()
        today_records = AttendanceRecord.objects.filter(register__date=today)
        present_today = today_records.filter(status='present').count()
        absent_today = today_records.filter(status='absent').count()
        late_today = today_records.filter(status='late').count()
        
        if today_records.exists():
            print(f"\nToday's Attendance:")
            print(f"  ├─ Present: {present_today}")
            print(f"  ├─ Absent: {absent_today}")
            print(f"  └─ Late: {late_today}")
        
        # Attendance by class today
        if today_records.exists():
            print("\nAttendance by Class Today:")
            for class_obj in StudentClass.objects.filter(is_active=True):
                class_records = today_records.filter(register__student_class=class_obj)
                if class_records.exists():
                    present = class_records.filter(status='present').count()
                    total = class_records.count()
                    percentage = (present / total * 100) if total > 0 else 0
                    print(f"  ├─ {class_obj.display_name:12}: {present}/{total} ({percentage:.1f}%)")
        
        self.stats['attendance'] = {
            'registers': registers,
            'records': records
        }
        
        if records == 0:
            self.results['warnings'].append("⚠️  No attendance records - attendance templates will show empty states")
        else:
            self.results['passed'].append("✅ Attendance records present: {}".format(records))
    
    def check_parents(self):
        """Verify parent portal data"""
        print("\n👪 PARENT PORTAL"
        "-" * 40)
        
        # Parent Profiles
        profiles = ParentProfile.objects.count()
        active_profiles = ParentProfile.objects.filter(access_status='active').count()
        print(f"Parent Profiles: {profiles} (Active: {active_profiles})")
        
        # Child Links
        links = ChildLink.objects.count()
        print(f"Parent-Child Links: {links}")
        
        # Average children per parent
        if profiles > 0:
            avg_children = links / profiles
            print(f"Average Children per Parent: {avg_children:.1f}")
        
        self.stats['parents'] = {
            'profiles': profiles,
            'links': links
        }
        
        if profiles == 0:
            self.results['warnings'].append("⚠️  No parent profiles - parent portal templates will be empty")
        else:
            self.results['passed'].append("✅ Parent profiles present: {}".format(profiles))
    
    def check_notifications(self):
        """Verify notifications data"""
        print("\n🔔 NOTIFICATIONS"
        "-" * 40)
        
        # Notifications
        notifications = Notification.objects.count()
        unread = Notification.objects.filter(status='pending').count()
        print(f"Notifications: {notifications} (Unread: {unread})")
        
        # Notification Templates
        templates = NotificationTemplate.objects.count()
        print(f"Notification Templates: {templates}")
        
        self.stats['notifications'] = {
            'total': notifications,
            'templates': templates
        }
    
    def check_audit(self):
        """Verify audit logs"""
        print("\n📋 AUDIT LOGS"
        "-" * 40)
        
        logs = AuditLog.objects.count()
        print(f"Audit Log Entries: {logs}")
        
        # Recent activity
        last_24h = AuditLog.objects.filter(timestamp__gte=timezone.now() - timedelta(days=1)).count()
        print(f"Last 24 Hours: {last_24h}")
        
        self.stats['audit'] = logs
    
    def check_relationships(self):
        """Verify data relationships"""
        print("\n🔗 DATA RELATIONSHIPS"
        "-" * 40)
        
        # Students with guardians
        students_with_guardians = Student.objects.filter(guardians__isnull=False).distinct().count()
        total_students = Student.objects.count()
        if total_students > 0:
            percentage = (students_with_guardians / total_students * 100)
            print(f"Students with Guardians: {students_with_guardians}/{total_students} ({percentage:.1f}%)")
            if students_with_guardians == 0:
                self.results['warnings'].append("⚠️  No students have guardians - parent portal won't work")
        
        # Students with parent profiles
        students_with_parents = ChildLink.objects.values('student_id').distinct().count()
        print(f"Students with Parent Portal Access: {students_with_parents}")
        
        # Students with invoices
        students_with_invoices = Invoice.objects.values('student_id').distinct().count()
        print(f"Students with Invoices: {students_with_invoices}")
        
        # Students with attendance
        students_with_attendance = AttendanceRecord.objects.values('student_id').distinct().count()
        print(f"Students with Attendance Records: {students_with_attendance}")
        
        # Students with results
        students_with_results = Result.objects.values('student_id').distinct().count()
        print(f"Students with Results: {students_with_results}")
    
    def check_template_access(self):
        """Verify that templates can access the data"""
        print("\n🎨 TEMPLATE ACCESS VERIFICATION"
        "-" * 40)
        
        checks = [
            ("Student List", 'students:list', Student.objects.exists()),
            ("Student Detail", 'students:detail', Student.objects.exists()),
            ("Staff List", 'staffs:list', Staff.objects.exists()),
            ("Staff Detail", 'staffs:detail', Staff.objects.exists()),
            ("Applications List", 'admissions:list', Application.objects.exists()),
            ("Invoices List", 'finance:invoice_list', Invoice.objects.exists()),
            ("Result Sheets", 'results:sheet_list', ResultSheet.objects.exists()),
            ("Attendance Dashboard", 'attendance:dashboard', AttendanceRegister.objects.exists()),
            ("Parent Dashboard", 'parents:dashboard', ParentProfile.objects.exists()),
            ("Notifications", 'notifications:list', Notification.objects.exists()),
        ]
        
        print("\nTemplate Data Availability:")
        for name, url_name, has_data in checks:
            status = "✅" if has_data else "⚠️"
            print(f"  {status} {name}: {'Data exists' if has_data else 'No data'}")
            if not has_data and name not in ['Parent Dashboard', 'Notifications']:
                self.results['warnings'].append(f"⚠️  No data for {name} template")
    
    def print_summary(self):
        """Print final summary"""
        print("\n" + "="*60)
        print("📊 FINAL VERIFICATION SUMMARY")
        print("="*60)
        
        print(f"\n✅ PASSED: {len(self.results['passed'])}")
        for item in self.results['passed']:
            print(f"  {item}")
        
        if self.results['warnings']:
            print(f"\n⚠️  WARNINGS: {len(self.results['warnings'])}")
            for item in self.results['warnings']:
                print(f"  {item}")
        
        if self.results['failed']:
            print(f"\n❌ FAILED: {len(self.results['failed'])}")
            for item in self.results['failed']:
                print(f"  {item}")
        
        print("\n" + "="*60)
        print("📈 STATISTICS SUMMARY")
        print("="*60)
        
        print(f"\nUsers: {self.stats.get('users', {}).get('total', 0)}")
        print(f"Academic Sessions: {self.stats.get('corecode', {}).get('sessions', 0)}")
        print(f"Classes: {self.stats.get('corecode', {}).get('classes', 0)}")
        print(f"Students: {self.stats.get('students', {}).get('total', 0)}")
        print(f"Staff: {self.stats.get('staff', {}).get('total', 0)}")
        print(f"Applications: {self.stats.get('admissions', {}).get('total', 0)}")
        print(f"Invoices: {self.stats.get('finance', {}).get('invoices', 0)}")
        print(f"Payments: {self.stats.get('finance', {}).get('payments', 0)}")
        print(f"Results: {self.stats.get('results', {}).get('results', 0)}")
        print(f"Attendance Records: {self.stats.get('attendance', {}).get('records', 0)}")
        print(f"Parent Profiles: {self.stats.get('parents', {}).get('profiles', 0)}")
        
        # Final verdict
        print("\n" + "="*60)
        if len(self.results['failed']) == 0:
            print("✅✅✅ SYSTEM IS READY - Templates should display data! ✅✅✅")
        else:
            print("⚠️⚠️⚠️ SYSTEM HAS ISSUES - Fix failed checks above ⚠️⚠️⚠️")
        print("="*60)


if __name__ == "__main__":
    verifier = DataVerifier()
    verifier.run()
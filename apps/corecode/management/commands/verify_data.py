from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum

# Import all models
from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass
from apps.students.models import Student, Guardian
from apps.staffs.models import Staff
from apps.admissions.models import Application
from apps.finance.models import Invoice, Payment
from apps.results.models import Result, ResultSheet
from apps.attendance.models import AttendanceRecord, AttendanceRegister
from apps.parents.models import ParentProfile, ChildLink

User = get_user_model()


class Command(BaseCommand):
    help = 'Verify data exists in the system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('🔍 DATA VERIFICATION REPORT'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        # Users
        user_count = User.objects.count()
        self.stdout.write(f'\n👤 Users: {user_count}')
        
        # Corecode
        session_count = AcademicSession.objects.count()
        term_count = AcademicTerm.objects.count()
        class_count = StudentClass.objects.count()
        self.stdout.write(f'\n🏛️  Corecode:')
        self.stdout.write(f'  ├─ Sessions: {session_count}')
        self.stdout.write(f'  ├─ Terms: {term_count}')
        self.stdout.write(f'  └─ Classes: {class_count}')
        
        # Students
        student_count = Student.objects.count()
        active_students = Student.objects.filter(status='active').count()
        guardian_count = Guardian.objects.count()
        self.stdout.write(f'\n🎓 Students:')
        self.stdout.write(f'  ├─ Total: {student_count}')
        self.stdout.write(f'  ├─ Active: {active_students}')
        self.stdout.write(f'  └─ Guardians: {guardian_count}')
        
        # Staff
        staff_count = Staff.objects.count()
        self.stdout.write(f'\n👥 Staff: {staff_count}')
        
        # Admissions
        app_count = Application.objects.count()
        self.stdout.write(f'\n📋 Applications: {app_count}')
        
        # Finance
        invoice_count = Invoice.objects.count()
        payment_count = Payment.objects.count()
        self.stdout.write(f'\n💰 Finance:')
        self.stdout.write(f'  ├─ Invoices: {invoice_count}')
        self.stdout.write(f'  └─ Payments: {payment_count}')
        
        # Results
        result_count = Result.objects.count()
        sheet_count = ResultSheet.objects.count()
        self.stdout.write(f'\n📊 Results:')
        self.stdout.write(f'  ├─ Result Sheets: {sheet_count}')
        self.stdout.write(f'  └─ Individual Results: {result_count}')
        
        # Attendance
        register_count = AttendanceRegister.objects.count()
        record_count = AttendanceRecord.objects.count()
        self.stdout.write(f'\n📅 Attendance:')
        self.stdout.write(f'  ├─ Registers: {register_count}')
        self.stdout.write(f'  └─ Records: {record_count}')
        
        # Parents
        parent_count = ParentProfile.objects.count()
        child_link_count = ChildLink.objects.count()
        self.stdout.write(f'\n👪 Parents:')
        self.stdout.write(f'  ├─ Profiles: {parent_count}')
        self.stdout.write(f'  └─ Child Links: {child_link_count}')
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        if student_count > 0:
            self.stdout.write(self.style.SUCCESS('✅✅✅ DATA EXISTS - Templates should work! ✅✅✅'))
        else:
            self.stdout.write(self.style.WARNING('⚠️⚠️⚠️ NO DATA FOUND - Run data generation first ⚠️⚠️⚠️'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
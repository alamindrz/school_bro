#!/usr/bin/env python
"""
Initial Data Generation Script for DETs Toolkit
Creates comprehensive test data including:
- Academic Sessions and Terms
- Nigerian 6-3-3-4 Classes
- Subjects (Nigerian curriculum)
- Staff members (all categories)
- Students with guardians
- Parent portal accounts
- Fee structures
- Invoices and payments
- Attendance records
- Result sheets with grades
- Applications
- Notifications
- Audit logs

Run: python manage.py shell < scripts/generate_initial_data.py
OR: python manage.py runscript generate_initial_data (if django-extensions installed)
"""

import os
import sys
import django
import random
from datetime import date, timedelta, datetime
from decimal import Decimal
from faker import Faker
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import transaction

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

# Import models after Django setup
from apps.corecode.models import (
    AcademicSession, AcademicTerm, StudentClass, SiteConfig, SystemLog
)
from apps.corecode.constants import (
    NigerianClassLevel, EducationLevel, TermType, SiteConfigKey
)
from apps.corecode.services import StudentClassService, SiteConfigService

from apps.students.models import Student, Guardian, StudentHistory
from apps.students.constants import StudentStatus, StudentCreationMethod, GuardianRelationship
from apps.students.services import StudentService, AdmissionNumberService

from apps.staffs.models import (
    Staff, SubjectAssignment, DutyAssignment, LeaveRequest,
    StaffAttendance, Qualification, WorkExperience, PerformanceEvaluation
)
from apps.staffs.constants import (
    StaffType, StaffCategory, EmploymentStatus, EmploymentType,
    ShiftType, QualificationType, LeaveType, DutyPost
)
from apps.staffs.services import StaffService, AssignmentService

from apps.admissions.models import Application, ApplicationPayment, ApplicationDocument
from apps.admissions.constants import ApplicationStatus, ApplicationType, PaymentStatus
from apps.admissions.services import ApplicationService, PaymentService

from apps.finance.models import FeeStructure, Invoice, Payment, FeeWaiver
from apps.finance.constants import FeeType, FeeTerm, InvoiceStatus, PaymentMethod
from apps.finance.services import InvoiceService, PaymentService as FinancePaymentService

from apps.results.models import Subject, ResultSheet, Result, ResultComment
from apps.results.constants import SubjectType, ResultStatus, GradeSystem
from apps.results.services import ResultService

from apps.attendance.models import AttendanceRegister, AttendanceRecord, AttendanceSummary
from apps.attendance.constants import AttendanceStatus, SessionType
from apps.attendance.services import AttendanceService

from apps.parents.models import ParentProfile, ChildLink, Notification as ParentNotification
from apps.parents.services import PortalService

from apps.notifications.models import Notification, NotificationTemplate, NotificationPreference
from apps.notifications.constants import NotificationType, NotificationChannel, NotificationPriority
from apps.notifications.services import NotificationService

from apps.audit.models import AuditLog
from apps.audit.services import AuditService

# Initialize Faker
fake = Faker('en_NG')  # Nigerian locale
User = get_user_model()

# Configuration
NUM_STUDENTS = 50
NUM_STAFF = 20
NUM_APPLICATIONS = 30
YEARS_OF_DATA = 2
CURRENT_YEAR = date.today().year


class DataGenerator:
    """Main data generator class"""
    
    def __init__(self):
        self.admin_user = None
        self.staff_users = []
        self.parent_users = []
        self.student_users = []
        self.classes = []
        self.subjects = []
        self.sessions = []
        self.terms = []
        self.students = []
        self.staff_members = []
        self.guardians = []
        self.parent_profiles = []
        
    @transaction.atomic
    def run(self):
        """Execute all data generation steps"""
        print("\n🚀 Starting initial data generation...\n")
        
        self.create_admin_user()
        self.create_groups_and_permissions()
        self.create_academic_structure()
        self.create_nigerian_classes()
        self.create_subjects()
        self.create_staff()
        self.create_students()
        self.create_parent_profiles()
        self.create_applications()
        self.create_fee_structures()
        self.create_invoices()
        self.create_attendance()
        self.create_results()
        self.create_notifications()
        
        print("\n✅ Initial data generation complete!\n")
        self.print_summary()
    
    def create_admin_user(self):
        """Create admin superuser"""
        print("Creating admin user...")
        
        if not User.objects.filter(username='admin').exists():
            import os, secrets, string
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
            if not password:
                alphabet = string.ascii_letters + string.digits + string.punctuation
                password = ''.join(secrets.choice(alphabet) for _ in range(16))
            self.admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@school.edu.ng',
                password=password,
                first_name='System',
                last_name='Administrator'
            )
            if os.environ.get('DJANGO_SUPERUSER_PASSWORD'):
                print("  Admin user created (password from DJANGO_SUPERUSER_PASSWORD)")
            else:
                print(f"  Admin user created (admin / {password})")
                print("  WARNING: Save this password now - it will not be shown again.")
        else:
            self.admin_user = User.objects.get(username='admin')
            print("  Admin user already exists")
    
    def create_groups_and_permissions(self):
        """Create user groups and assign permissions"""
        print("\nCreating user groups...")
        
        groups = {
            'Administrators': ['add', 'change', 'delete', 'view'],
            'Teachers': ['view'],
            'Parents': ['view'],
            'Students': ['view'],
            'Bursars': ['view', 'add', 'change'],
            'Admissions Officers': ['view', 'add', 'change'],
        }
        
        for group_name in groups.keys():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                print(f"  ✅ Created group: {group_name}")
            else:
                print(f"  ✅ Group already exists: {group_name}")
    
    def create_academic_structure(self):
        """Create academic sessions and terms for past, current, and future years"""
        print("\nCreating academic sessions and terms...")
        
        for year_offset in range(-1, 2):  # Past year, current year, next year
            year = CURRENT_YEAR + year_offset
            session_name = f"{year}/{year+1}"
            session_code = f"{year}{year+1}"
            
            session, created = AcademicSession.objects.get_or_create(
                name=session_name,
                defaults={
                    'code': session_code,
                    'start_date': date(year, 9, 1),  # Nigerian academic year starts in September
                    'end_date': date(year+1, 8, 31),
                    'is_current': (year_offset == 0)  # Only current year is current
                }
            )
            
            if created:
                print(f"  ✅ Created session: {session_name}")
                
                # Create terms for this session
                for term_num in [1, 2, 3]:
                    term_start = date(year, 9 + (term_num-1)*4, 1)  # Rough term spacing
                    term_end = date(year, 12 + (term_num-1)*4, 20) if term_num < 3 else date(year+1, 7, 15)
                    
                    term = AcademicTerm.objects.create(
                        session=session,
                        term=term_num,
                        name=f"{dict(TermType.CHOICES)[term_num]} {session_name}",
                        start_date=term_start,
                        end_date=term_end,
                        is_current=(year_offset == 0 and term_num == 1)  # First term of current year is current
                    )
                    print(f"    ✅ Created term: {term.name}")
                    
                    if year_offset == 0:
                        self.terms.append(term)
            else:
                print(f"  ✅ Session already exists: {session_name}")
            
            self.sessions.append(session)
    
    def create_nigerian_classes(self):
        """Create all Nigerian 6-3-3-4 classes"""
        print("\nCreating Nigerian 6-3-3-4 classes...")
        
        # Check if classes already exist
        if StudentClass.objects.count() >= 15:
            self.classes = list(StudentClass.objects.all().order_by('sort_order'))
            print(f"  ✅ {len(self.classes)} classes already exist")
            return
        
        class_definitions = [
            # Nursery (3 years)
            ('NUR1', 'Nursery 1', EducationLevel.NURSERY, 25, 1),
            ('NUR2', 'Nursery 2', EducationLevel.NURSERY, 25, 2),
            ('NUR3', 'Nursery 3', EducationLevel.NURSERY, 25, 3),
            
            # Primary (6 years)
            ('PRI1', 'Primary 1', EducationLevel.PRIMARY, 40, 4),
            ('PRI2', 'Primary 2', EducationLevel.PRIMARY, 40, 5),
            ('PRI3', 'Primary 3', EducationLevel.PRIMARY, 40, 6),
            ('PRI4', 'Primary 4', EducationLevel.PRIMARY, 40, 7),
            ('PRI5', 'Primary 5', EducationLevel.PRIMARY, 40, 8),
            ('PRI6', 'Primary 6', EducationLevel.PRIMARY, 40, 9),
            
            # Junior Secondary (3 years)
            ('JSS1', 'JSS 1', EducationLevel.JSS, 45, 10),
            ('JSS2', 'JSS 2', EducationLevel.JSS, 45, 11),
            ('JSS3', 'JSS 3', EducationLevel.JSS, 45, 12),
            
            # Senior Secondary (3 years)
            ('SS1', 'SS 1', EducationLevel.SSS, 45, 13),
            ('SS2', 'SS 2', EducationLevel.SSS, 45, 14),
            ('SS3', 'SS 3', EducationLevel.SSS, 45, 15),
        ]
        
        for name, display_name, level, max_students, sort_order in class_definitions:
            class_obj, created = StudentClass.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'education_level': level,
                    'max_students': max_students,
                    'sort_order': sort_order,
                    'is_active': True
                }
            )
            self.classes.append(class_obj)
            if created:
                print(f"  ✅ Created class: {display_name}")
        
        print(f"  ✅ Total classes: {len(self.classes)}")
    
    def create_subjects(self):
        """Create Nigerian curriculum subjects"""
        print("\nCreating subjects...")
        
        # Core subjects offered in all classes
        core_subjects = [
            ('ENG', 'English Language', SubjectType.CORE, True),
            ('MTH', 'Mathematics', SubjectType.CORE, True),
            ('CIV', 'Civic Education', SubjectType.CORE, True),
            ('BIO', 'Biology', SubjectType.CORE, True),
            ('CHM', 'Chemistry', SubjectType.CORE, True),
            ('PHY', 'Physics', SubjectType.CORE, True),
            ('LIT', 'Literature in English', SubjectType.CORE, True),
            ('GOV', 'Government', SubjectType.CORE, True),
            ('ECO', 'Economics', SubjectType.CORE, True),
            ('GEO', 'Geography', SubjectType.CORE, True),
        ]
        
        # Elective subjects
        elective_subjects = [
            ('FUR', 'Further Mathematics', SubjectType.ELECTIVE, False),
            ('ACC', 'Accounting', SubjectType.ELECTIVE, False),
            ('COM', 'Commerce', SubjectType.ELECTIVE, False),
            ('HIS', 'History', SubjectType.ELECTIVE, False),
            ('IRS', 'Islamic Studies', SubjectType.ELECTIVE, False),
            ('CRS', 'Christian Religious Studies', SubjectType.ELECTIVE, False),
            ('FRE', 'French', SubjectType.ELECTIVE, False),
            ('YOR', 'Yoruba', SubjectType.ELECTIVE, False),
            ('HAU', 'Hausa', SubjectType.ELECTIVE, False),
            ('IGB', 'Igbo', SubjectType.ELECTIVE, False),
        ]
        
        # Vocational subjects
        vocational_subjects = [
            ('AGR', 'Agriculture', SubjectType.VOCATIONAL, False),
            ('FOO', 'Food and Nutrition', SubjectType.VOCATIONAL, False),
            ('TEX', 'Textile', SubjectType.VOCATIONAL, False),
            ('WOO', 'Woodwork', SubjectType.VOCATIONAL, False),
            ('MET', 'Metalwork', SubjectType.VOCATIONAL, False),
            ('ELE', 'Electronics', SubjectType.VOCATIONAL, False),
            ('TEC', 'Technical Drawing', SubjectType.VOCATIONAL, False),
            ('COM', 'Computer Studies', SubjectType.VOCATIONAL, False),
        ]
        
        all_subjects = core_subjects + elective_subjects + vocational_subjects
        
        for code, name, subj_type, is_core in all_subjects:
            subject, created = Subject.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'subject_type': subj_type,
                    'is_nigerian_core': is_core,
                    'is_active': True
                }
            )
            
            # Add to appropriate classes
            if subj_type == SubjectType.CORE:
                subject.offered_in_classes.set(self.classes)
            elif subj_type == SubjectType.ELECTIVE:
                # Electives for secondary classes
                secondary_classes = [c for c in self.classes if c.education_level in [EducationLevel.JSS, EducationLevel.SSS]]
                subject.offered_in_classes.set(secondary_classes)
            else:
                # Vocational for senior secondary
                sss_classes = [c for c in self.classes if c.education_level == EducationLevel.SSS]
                subject.offered_in_classes.set(sss_classes)
            
            self.subjects.append(subject)
            
            if created:
                print(f"  ✅ Created subject: {name} ({code})")
        
        print(f"  ✅ Total subjects: {len(self.subjects)}")
    
    def create_staff(self):
        """Create staff members of all categories"""
        print("\nCreating staff members...")
        
        # Create teaching staff
        teaching_staff_count = NUM_STAFF // 2
        for i in range(teaching_staff_count):
            gender = random.choice(['M', 'F'])
            first_name = fake.first_name_male() if gender == 'M' else fake.first_name_female()
            last_name = fake.last_name()
            email = f"{first_name.lower()}.{last_name.lower()}@school.edu.ng"
            
            # Create user account
            username = f"teacher_{i+1}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_staff': True
                }
            )
            if created:
                user.set_password('teacher123')
                user.save()
                self.staff_users.append(user)
            
            # Determine staff type
            if i < 2:
                staff_type = StaffType.PRINCIPAL if i == 0 else StaffType.VICE_PRINCIPAL_1
            elif i < 5:
                staff_type = StaffType.HOD
            else:
                staff_type = StaffType.SUBJECT_TEACHER
            
            # Create staff record
            staff = Staff.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                date_of_birth=fake.date_of_birth(minimum_age=25, maximum_age=60),
                email=email,
                phone=fake.phone_number()[:15],
                address=fake.address(),
                city=fake.city(),
                state_of_origin=random.choice([
                    'Lagos', 'Abuja', 'Kano', 'Rivers', 'Oyo', 'Kaduna'
                ]),
                staff_type=staff_type,
                employment_status=EmploymentStatus.ACTIVE,
                employment_type=EmploymentType.PERMANENT,
                shift=ShiftType.FIXED,
                date_employed=fake.date_between(start_date='-10y', end_date='-1y'),
                department=random.choice(['Science', 'Arts', 'Commercial', 'Technical']),
                highest_qualification=random.choice([
                    QualificationType.PHD, QualificationType.MASTERS, QualificationType.DEGREE
                ]),
                emergency_contact_name=fake.name(),
                emergency_contact_phone=fake.phone_number()[:15],
                emergency_contact_relationship='Spouse',
                created_by=self.admin_user
            )
            
            self.staff_members.append(staff)
            print(f"  ✅ Created {staff.get_staff_type_display()}: {staff.get_full_name}")
        
        # Create non-teaching staff
        non_teaching_types = [
            StaffType.ADMIN_OFFICER, StaffType.ACCOUNTANT, StaffType.SECRETARY,
            StaffType.LIBRARIAN, StaffType.NURSE, StaffType.SECURITY,
            StaffType.CLEANER, StaffType.DRIVER, StaffType.KITCHEN_STAFF,
            StaffType.GATE_MAN, StaffType.GROUNDSKEEPER, StaffType.ICT_TECHNICIAN
        ]
        
        for i in range(NUM_STAFF - teaching_staff_count):
            staff_type = random.choice(non_teaching_types)
            gender = random.choice(['M', 'F'])
            first_name = fake.first_name_male() if gender == 'M' else fake.first_name_female()
            last_name = fake.last_name()
            email = f"{first_name.lower()}.{last_name.lower()}@staff.school.edu.ng"
            
            # Create user account
            username = f"staff_{teaching_staff_count + i + 1}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_staff': True
                }
            )
            if created:
                user.set_password('staff123')
                user.save()
                self.staff_users.append(user)
            
            staff = Staff.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                date_of_birth=fake.date_of_birth(minimum_age=20, maximum_age=55),
                email=email,
                phone=fake.phone_number()[:15],
                address=fake.address(),
                city=fake.city(),
                state_of_origin=random.choice(['Lagos', 'Ogun', 'Oyo', 'Kwara']),
                staff_type=staff_type,
                employment_status=EmploymentStatus.ACTIVE,
                employment_type=random.choice([EmploymentType.PERMANENT, EmploymentType.CONTRACT]),
                shift=random.choice([ShiftType.FIXED, ShiftType.MORNING, ShiftType.AFTERNOON]),
                date_employed=fake.date_between(start_date='-5y', end_date='-1m'),
                department='Administration' if staff_type in [StaffType.ADMIN_OFFICER, StaffType.ACCOUNTANT] else 'Support',
                highest_qualification=random.choice([
                    QualificationType.DIPLOMA, QualificationType.CERTIFICATE, QualificationType.DEGREE
                ]),
                emergency_contact_name=fake.name(),
                emergency_contact_phone=fake.phone_number()[:15],
                emergency_contact_relationship=random.choice(['Spouse', 'Parent', 'Sibling']),
                created_by=self.admin_user
            )
            
            self.staff_members.append(staff)
            print(f"  ✅ Created {staff.get_staff_type_display()}: {staff.get_full_name}")
        
        print(f"  ✅ Total staff: {len(self.staff_members)}")
        
        # Create subject assignments for teachers
        self.create_subject_assignments()
        
        # Create duty assignments
        self.create_duty_assignments()
    
    def create_subject_assignments(self):
        """Assign subjects to teaching staff"""
        print("\nCreating subject assignments...")
        
        teaching_staff = [s for s in self.staff_members if s.staff_category == StaffCategory.ACADEMIC]
        
        for staff in teaching_staff:
            # Assign 2-4 subjects
            num_subjects = random.randint(2, 4)
            assigned_subjects = random.sample(self.subjects, min(num_subjects, len(self.subjects)))
            
            for subject in assigned_subjects:
                # Choose random class that offers this subject
                classes_offering = subject.offered_in_classes.all()
                if classes_offering:
                    student_class = random.choice(classes_offering)
                    
                    AssignmentService.assign_subject(
                        staff_id=staff.id,
                        subject_id=subject.id,
                        class_id=student_class.id,
                        session_id=self.sessions[-1].id,  # Current session
                        periods_per_week=random.randint(3, 8),
                        is_form_master=random.choice([True, False]) if random.random() < 0.2 else False,
                        assigned_by_id=self.admin_user.id
                    )
            
            print(f"  ✅ Assigned {num_subjects} subjects to {staff.get_full_name}")
    
    def create_duty_assignments(self):
        """Create duty assignments for staff"""
        print("\nCreating duty assignments...")
        
        # Sports master
        sports_master = random.choice([s for s in self.staff_members if s.staff_category == StaffCategory.ACADEMIC])
        AssignmentService.assign_duty(
            staff_id=sports_master.id,
            duty_post=DutyPost.SPORTS_COORDINATOR,
            session_id=self.sessions[-1].id,
            assigned_by_id=self.admin_user.id
        )
        print(f"  ✅ Assigned Sports Master to {sports_master.get_full_name}")
        
        # Club patrons
        clubs = ['Debate Club', 'Press Club', 'Science Club', 'Math Club', 'Drama Club', 'JETS Club']
        for club in clubs:
            patron = random.choice([s for s in self.staff_members if s.staff_category == StaffCategory.ACADEMIC])
            AssignmentService.assign_duty(
                staff_id=patron.id,
                duty_post=DutyPost.CLUB_PATRON,
                session_id=self.sessions[-1].id,
                club_name=club,
                assigned_by_id=self.admin_user.id
            )
        print(f"  ✅ Assigned {len(clubs)} club patrons")
        
        # House masters
        houses = ['Red House', 'Blue House', 'Green House', 'Yellow House']
        for house in houses:
            housemaster = random.choice(self.staff_members)
            AssignmentService.assign_duty(
                staff_id=housemaster.id,
                duty_post=DutyPost.HOUSEMASTER,
                session_id=self.sessions[-1].id,
                house_name=house,
                assigned_by_id=self.admin_user.id
            )
        print(f"  ✅ Assigned {len(houses)} house masters")
        
    def create_students(self):
        """Create students across all classes"""
        print("\nCreating students...")
        
        current_session = AcademicSession.objects.filter(is_current=True).first()
        
        for i in range(NUM_STUDENTS):
            # Distribute students across classes
            student_class = random.choice(self.classes)
            
            gender = random.choice(['M', 'F'])
            first_name = fake.first_name_male() if gender == 'M' else fake.first_name_female()
            last_name = fake.last_name()
            
            # Calculate date of birth based on class
            base_age = {
                EducationLevel.NURSERY: 4,
                EducationLevel.PRIMARY: 9,
                EducationLevel.JSS: 13,
                EducationLevel.SSS: 16,
            }.get(student_class.education_level, 10)
            
            age_variance = random.randint(-1, 1)
            age = base_age + age_variance
            dob = date.today() - timedelta(days=age*365 + random.randint(0, 365))
            
            email = f"{first_name.lower()}.{last_name.lower()}@student.edu.ng"
            
            # Create user account
            username = f"student_{i+1}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                }
            )
            if created:
                user.set_password('student123')
                user.save()
                self.student_users.append(user)
            
            # Generate admission number
            admission_number = AdmissionNumberService.generate_admission_number(
                class_name=student_class.name,
                session_code=current_session.code if current_session else '2024'
            )
            
            # Create student
            student = Student.objects.create(
                admission_number=admission_number,
                user=user,
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                date_of_birth=dob,
                email=email,
                phone=fake.phone_number()[:15],
                address=fake.address(),
                city=fake.city(),
                state_of_origin=random.choice(['Lagos', 'Abuja', 'Kano', 'Rivers', 'Oyo']),
                current_class=student_class,
                enrollment_date=fake.date_between(start_date='-3y', end_date='-1m'),
                enrollment_session=current_session,
                status=StudentStatus.ACTIVE,
                created_via=StudentCreationMethod.MANUAL,
                created_by=self.admin_user
            )
            
            self.students.append(student)
            
            # Create guardians
            self.create_guardians_for_student(student)
            
            if (i + 1) % 10 == 0:
                print(f"  ✅ Created {i + 1} students...")
        
        print(f"  ✅ Total students created: {len(self.students)}")
    
    def create_guardians_for_student(self, student):
        """Create 1-2 guardians for a student"""
        num_guardians = random.randint(1, 2)
        
        for j in range(num_guardians):
            is_primary = (j == 0)
            gender = 'F' if j == 0 and random.random() < 0.7 else 'M'  # Mothers more likely primary
            first_name = fake.first_name_female() if gender == 'F' else fake.first_name_male()
            last_name = student.last_name  # Same last name
            relationship = GuardianRelationship.MOTHER if gender == 'F' else GuardianRelationship.FATHER
            
            guardian = Guardian.objects.create(
                student=student,
                first_name=first_name,
                last_name=last_name,
                relationship=relationship,
                email=fake.email(),
                phone=fake.phone_number()[:15],
                address=fake.address(),
                occupation=fake.job(),
                is_primary=is_primary,
                is_emergency_contact=True
            )
            
            self.guardians.append(guardian)
    
    def create_parent_profiles(self):
        """Create parent portal profiles and link to students"""
        print("\nCreating parent portal profiles...")
        
        for guardian in self.guardians:
            # Create parent profile
            parent_profile, created = ParentProfile.objects.get_or_create(
                guardian_id=guardian.id,
                defaults={
                    'first_name': guardian.first_name,
                    'last_name': guardian.last_name,
                    'email': guardian.email,
                    'phone': guardian.phone,
                    'access_status': 'active'
                }
            )
            
            self.parent_profiles.append(parent_profile)
            
            # Link to student
            ChildLink.objects.get_or_create(
                parent=parent_profile,
                student_id=guardian.student.id,
                defaults={
                    'student_name': guardian.student.get_full_name,
                    'student_class': guardian.student.current_class.display_name,
                    'relationship': guardian.relationship,
                    'is_primary': guardian.is_primary
                }
            )
            
            if created:
                print(f"  ✅ Created parent profile for {guardian.get_full_name}")
    
    def create_applications(self):
        """Create applications for admissions"""
        print("\nCreating applications...")
        
        current_session = AcademicSession.objects.filter(is_current=True).first()
        
        for i in range(NUM_APPLICATIONS):
            status = random.choice([
                ApplicationStatus.DRAFT, ApplicationStatus.SUBMITTED,
                ApplicationStatus.UNDER_REVIEW, ApplicationStatus.APPROVED,
                ApplicationStatus.REJECTED, ApplicationStatus.ENROLLED
            ])
            
            gender = random.choice(['M', 'F'])
            first_name = fake.first_name_male() if gender == 'M' else fake.first_name_female()
            last_name = fake.last_name()
            
            application = Application.objects.create(
                application_number=f"APP-{CURRENT_YEAR}-{i+1:04d}",
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                date_of_birth=fake.date_of_birth(minimum_age=5, maximum_age=18),
                email=fake.email(),
                phone=fake.phone_number()[:15],
                address=fake.address(),
                city=fake.city(),
                state_of_origin=random.choice(['Lagos', 'Abuja', 'Kano']),
                applying_for_class=random.choice(self.classes),
                applying_for_session=current_session,
                application_type=random.choice([ApplicationType.NEW, ApplicationType.TRANSFER]),
                guardian_first_name=fake.first_name(),
                guardian_last_name=last_name,
                guardian_relationship=random.choice(['father', 'mother', 'guardian']),
                guardian_phone=fake.phone_number()[:15],
                status=status,
                created_by=self.admin_user
            )
            
            # Create payment for submitted applications
            if status in [ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW, ApplicationStatus.APPROVED]:
                ApplicationPayment.objects.create(
                    application=application,
                    amount=Decimal('5000.00'),
                    status=PaymentStatus.COMPLETED,
                    transaction_date=timezone.now()
                )
            
            if status == ApplicationStatus.ENROLLED:
                # Enroll as student
                student_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'date_of_birth': application.date_of_birth.isoformat(),
                    'gender': gender,
                    'current_class_id': application.applying_for_class.id,
                    'email': application.email,
                    'phone': application.phone,
                    'address': application.address,
                    'city': application.city,
                    'state_of_origin': application.state_of_origin,
                    'created_via': StudentCreationMethod.ADMISSION,
                    'created_by_id': self.admin_user.id
                }
                
                try:
                    student = StudentService.create_from_admission(student_data)
                    application.enrolled_student_id = student.id
                    application.enrolled_at = timezone.now()
                    application.save()
                    print(f"    ✅ Enrolled applicant {application.application_number}")
                except Exception as e:
                    print(f"    ❌ Failed to enroll: {e}")
            
            if (i + 1) % 10 == 0:
                print(f"  ✅ Created {i + 1} applications...")
    
    def create_fee_structures(self):
        """Create fee structures for classes"""
        print("\nCreating fee structures...")
        
        # Tuition fees per term
        for class_obj in self.classes:
            base_fee = {
                EducationLevel.NURSERY: 50000,
                EducationLevel.PRIMARY: 75000,
                EducationLevel.JSS: 100000,
                EducationLevel.SSS: 125000,
            }.get(class_obj.education_level, 50000)
            
            # Tuition
            FeeStructure.objects.get_or_create(
                student_class=class_obj,
                fee_type=FeeType.TUITION,
                term=FeeTerm.PER_TERM,
                defaults={
                    'amount': base_fee,
                    'description': f'Tuition fee per term',
                    'is_active': True,
                    'created_by': self.admin_user
                }
            )
            
            # Development levy (one-time per session)
            FeeStructure.objects.get_or_create(
                student_class=class_obj,
                fee_type=FeeType.DEVELOPMENT,
                term=FeeTerm.PER_SESSION,
                defaults={
                    'amount': base_fee * 0.2,
                    'description': 'Development levy',
                    'is_active': True,
                    'created_by': self.admin_user
                }
            )
            
            # Library fee
            FeeStructure.objects.get_or_create(
                student_class=class_obj,
                fee_type=FeeType.LIBRARY,
                term=FeeTerm.PER_TERM,
                defaults={
                    'amount': base_fee * 0.05,
                    'description': 'Library fee',
                    'is_active': True,
                    'created_by': self.admin_user
                }
            )
            
            # Sports fee
            FeeStructure.objects.get_or_create(
                student_class=class_obj,
                fee_type=FeeType.SPORTS,
                term=FeeTerm.PER_TERM,
                defaults={
                    'amount': base_fee * 0.03,
                    'description': 'Sports fee',
                    'is_active': True,
                    'created_by': self.admin_user
                }
            )
            
            print(f"  ✅ Created fee structure for {class_obj.display_name}")
    
    def create_invoices(self):
        """Create invoices for students"""
        print("\nCreating invoices...")
        
        current_session = AcademicSession.objects.filter(is_current=True).first()
        terms = AcademicTerm.objects.filter(session=current_session)
        
        for student in self.students:
            # Create invoices for current term
            current_term = terms.filter(is_current=True).first()
            
            if current_term:
                fee_structures = FeeStructure.objects.filter(
                    student_class=student.current_class,
                    is_active=True
                )
                
                for fee in fee_structures:
                    # Skip if not applicable this term
                    if fee.term == FeeTerm.PER_TERM:
                        term = current_term
                    elif fee.term == FeeTerm.PER_SESSION:
                        term = None
                    else:
                        continue
                    
                    try:
                        InvoiceService.create_invoice(
                            student_id=student.id,
                            student_name=student.get_full_name,
                            class_id=student.current_class.id,
                            fee_type=fee.fee_type,
                            amount=fee.amount,
                            description=fee.description,
                            session_id=current_session.id,
                            term_id=term.id if term else None,
                            due_date=(date.today() + timedelta(days=30)).isoformat(),
                            created_by_id=self.admin_user.id
                        )
                    except Exception as e:
                        print(f"    ❌ Failed to create invoice for {student.get_full_name}: {e}")
            
            if (self.students.index(student) + 1) % 10 == 0:
                print(f"  ✅ Created invoices for {self.students.index(student) + 1} students...")
    
    def create_attendance(self):
        """Create attendance records for the past month"""
        print("\nCreating attendance records...")
        
        current_session = AcademicSession.objects.filter(is_current=True).first()
        
        # Create attendance for last 30 days
        for days_ago in range(1, 31):
            record_date = date.today() - timedelta(days=days_ago)
            
            # Skip weekends
            if record_date.weekday() >= 5:  # Saturday and Sunday
                continue
            
            for class_obj in self.classes:
                # Get or create register
                register, created = AttendanceRegister.objects.get_or_create(
                    student_class=class_obj,
                    date=record_date,
                    session_type=random.choice([SessionType.MORNING, SessionType.AFTERNOON]),
                    defaults={
                        'academic_session': current_session,
                        'is_closed': True
                    }
                )
                
                # Get students in this class
                students = Student.objects.filter(current_class=class_obj, status=StudentStatus.ACTIVE)
                
                for student in students:
                    # Random attendance status
                    status = random.choices(
                        [AttendanceStatus.PRESENT, AttendanceStatus.ABSENT, AttendanceStatus.LATE],
                        weights=[85, 10, 5]
                    )[0]
                    
                    try:
                        AttendanceRecord.objects.create(
                            register=register,
                            student_id=student.id,
                            student_name=student.get_full_name,
                            status=status,
                            check_in_time=timezone.now().time() if status != AttendanceStatus.ABSENT else None
                        )
                    except Exception:
                        pass  # Skip duplicates
            
            if days_ago % 10 == 0:
                print(f"  ✅ Created attendance for day {record_date}")
    
    def create_results(self):
        """Create result sheets and results"""
        print("\nCreating results...")
        
        current_session = AcademicSession.objects.filter(is_current=True).first()
        current_term = AcademicTerm.objects.filter(is_current=True).first()
        
        if not current_term:
            print("  ❌ No current term found")
            return
        
        for class_obj in self.classes:
            # Get subjects for this class
            subjects = Subject.objects.filter(offered_in_classes=class_obj)
            
            if not subjects.exists():
                continue
            
            # Create result sheet
            sheet, created = ResultSheet.objects.get_or_create(
                student_class=class_obj,
                academic_session=current_session,
                academic_term=current_term,
                defaults={
                    'status': ResultStatus.PUBLISHED,
                    'created_by': self.admin_user
                }
            )
            
            if created:
                # Add subjects
                sheet.subjects.set(subjects)
            
            # Get students in this class
            students = Student.objects.filter(current_class=class_obj, status=StudentStatus.ACTIVE)
            
            for student in students:
                for subject in subjects:
                    # Generate scores
                    ca1 = random.randint(15, 20)
                    ca2 = random.randint(15, 20)
                    ca3 = random.randint(15, 20)
                    exam = random.randint(30, 60)
                    
                    total = ca1 + ca2 + ca3 + exam
                    
                    # Determine grade
                    if total >= 75:
                        grade = GradeSystem.A1
                    elif total >= 70:
                        grade = GradeSystem.B2
                    elif total >= 65:
                        grade = GradeSystem.B3
                    elif total >= 60:
                        grade = GradeSystem.C4
                    elif total >= 55:
                        grade = GradeSystem.C5
                    elif total >= 50:
                        grade = GradeSystem.C6
                    elif total >= 45:
                        grade = GradeSystem.D7
                    elif total >= 40:
                        grade = GradeSystem.E8
                    else:
                        grade = GradeSystem.F9
                    
                    try:
                        Result.objects.create(
                            result_sheet=sheet,
                            subject=subject,
                            student_id=student.id,
                            student_name=student.get_full_name,
                            ca1_score=ca1,
                            ca2_score=ca2,
                            ca3_score=ca3,
                            exam_score=exam,
                            total_score=total,
                            grade=grade,
                            entered_by=self.admin_user
                        )
                    except Exception:
                        pass  # Skip duplicates
            
            print(f"  ✅ Created results for {class_obj.display_name}")
    
    def create_notifications(self):
        """Create sample notifications"""
        print("\nCreating notifications...")
        
        # Notifications for parents
        for parent in self.parent_profiles[:10]:
            NotificationService.send_notification(
                notification_type=random.choice([
                    NotificationType.PAYMENT_RECEIPT,
                    NotificationType.RESULT_PUBLISHED,
                    NotificationType.EVENT_REMINDER,
                    NotificationType.GENERAL_ANNOUNCEMENT
                ]),
                title=fake.sentence(),
                message=fake.paragraph(),
                recipient_type='parent',
                recipient_id=parent.id,
                created_by_id=self.admin_user.id
            )
        
        # Notifications for staff
        for staff in self.staff_members[:10]:
            if staff.user:
                NotificationService.send_notification(
                    notification_type=random.choice([
                        NotificationType.LEAVE_APPROVED,
                        NotificationType.PERFORMANCE_REVIEW,
                        NotificationType.GENERAL_ANNOUNCEMENT
                    ]),
                    title=fake.sentence(),
                    message=fake.paragraph(),
                    recipient_type='staff',
                    recipient_id=staff.id,
                    created_by_id=self.admin_user.id
                )
        
        print(f"  ✅ Created notifications")
    
    def print_summary(self):
        """Print summary of created data"""
        print("\n" + "="*50)
        print("DATA GENERATION SUMMARY")
        print("="*50)
        print(f"Academic Sessions: {AcademicSession.objects.count()}")
        print(f"Academic Terms: {AcademicTerm.objects.count()}")
        print(f"Classes: {StudentClass.objects.count()}")
        print(f"Subjects: {Subject.objects.count()}")
        print(f"Staff Members: {Staff.objects.count()}")
        print(f"Students: {Student.objects.count()}")
        print(f"Guardians: {Guardian.objects.count()}")
        print(f"Parent Profiles: {ParentProfile.objects.count()}")
        print(f"Applications: {Application.objects.count()}")
        print(f"Invoices: {Invoice.objects.count()}")
        print(f"Attendance Records: {AttendanceRecord.objects.count()}")
        print(f"Result Sheets: {ResultSheet.objects.count()}")
        print(f"Results: {Result.objects.count()}")
        print(f"Notifications: {Notification.objects.count()}")
        print("="*50)
        
        # Login credentials
        print("\n🔑 LOGIN CREDENTIALS:")
        print("-"*30)
        print("Admin: admin@school.edu.ng / admin123")
        print("Teachers: teacher_1@school.edu.ng / teacher123 (up to teacher_10)")
        print("Students: student_1@student.edu.ng / student123 (up to student_50)")
        print("Staff: staff_11@staff.school.edu.ng / staff123")
        print("\n⚠️  Change passwords after first login!")
        print("="*50)


if __name__ == "__main__":
    generator = DataGenerator()
    
    # Ask for confirmation
    print("\n⚠️  This will create test data in your database.")
    print(f"Estimated data:")
    print(f"  - {NUM_STUDENTS} students")
    print(f"  - {NUM_STAFF} staff members")
    print(f"  - {NUM_APPLICATIONS} applications")
    print(f"  - All Nigerian 6-3-3-4 classes")
    print(f"  - Multiple academic sessions and terms")
    
    response = input("\nContinue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        generator.run()
    else:
        print("Data generation cancelled.")    
    
    
"""
Management command to create staff, students, and parents
Run: python manage.py create_people [--staff=10] [--students=50] [--with-parents]

FIXED: Unique email generation to prevent IntegrityError
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.utils import timezone
from datetime import date, timedelta
import random
import sys

# Corecode imports
from apps.corecode.models import StudentClass, AcademicSession
from apps.corecode.constants import EducationLevel

# Students imports
from apps.students.models import Student, Guardian
from apps.students.constants import StudentStatus, GuardianRelationship, StudentCreationMethod
from apps.students.services.admission_number import AdmissionNumberService

# Staff imports
from apps.staffs.models import Staff
from apps.staffs.constants import (
    StaffType, StaffCategory, EmploymentStatus, EmploymentType,
    ShiftType, QualificationType, DutyPost
)

# Parents imports
from apps.parents.models import ParentProfile, ChildLink

User = get_user_model()


class Command(BaseCommand):
    help = 'Create staff, students, and parents with proper relationships'

    def add_arguments(self, parser):
        # Staff options
        parser.add_argument('--staff', type=int, default=10, help='Number of staff to create')
        parser.add_argument('--teaching-staff', type=int, help='Number of teaching staff (defaults to 60% of total)')
        parser.add_argument('--admin-staff', type=int, help='Number of admin staff')
        parser.add_argument('--support-staff', type=int, help='Number of support staff')
        
        # Student options
        parser.add_argument('--students', type=int, default=50, help='Number of students to create')
        parser.add_argument('--with-parents', action='store_true', help='Create parent portal accounts')
        parser.add_argument('--guardians-per-student', type=int, default=2, help='Number of guardians per student (1-3)')
        
        # Class distribution
        parser.add_argument('--balance-classes', action='store_true', help='Distribute students evenly across classes')
        parser.add_argument('--specific-class', type=str, help='Create students only in specific class (e.g., "SS1")')
        
        # Authentication
        parser.add_argument('--create-users', action='store_true', help='Create Django user accounts')
        parser.add_argument('--password', type=str, default='password123', help='Default password for created users')
        
        # Other options
        parser.add_argument('--dry-run', action='store_true', help='Show what would be created without actually creating')
        parser.add_argument('--verbose', action='store_true', help='Show detailed output')
        parser.add_argument('--skip-on-error', action='store_true', help='Skip records that cause errors and continue')

    def __init__(self):
        super().__init__()
        self.used_emails = set()
        self.used_usernames = set()

    @transaction.atomic
    def handle(self, *args, **options):
        self.verbose = options.get('verbose', False)
        self.dry_run = options.get('dry_run', False)
        self.skip_on_error = options.get('skip_on_error', False)
        
        # Reset tracking sets
        self.used_emails = set(email for email in Staff.objects.values_list('email', flat=True) if email)
        self.used_emails.update(Student.objects.values_list('email', flat=True))
        self.used_emails.update(User.objects.values_list('email', flat=True))
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('👥 CREATING PEOPLE'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        # Check if we have required data
        self.check_prerequisites()
        
        # Calculate staff distribution
        staff_counts = self.calculate_staff_counts(options)
        
        # Create staff
        if staff_counts['total'] > 0:
            self.create_staff(staff_counts, options)
        
        # Create students
        if options['students'] > 0:
            self.create_students(options)
        
        # Create parent portal accounts if requested
        if options['with_parents']:
            self.create_parent_portals()
        
        # Print summary
        self.print_summary()
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN - No data was actually created'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ All people created successfully!'))

    def check_prerequisites(self):
        """Check if required data exists"""
        self.stdout.write('🔍 Checking prerequisites...')
        
        # Check classes
        if not StudentClass.objects.filter(is_active=True).exists():
            raise CommandError(
                'No classes found. Please run "python manage.py init_school" first.'
            )
        
        # Check academic session
        if not AcademicSession.objects.filter(is_current=True).exists():
            self.stdout.write(self.style.WARNING(
                '  ⚠️  No current academic session found. Students will be created without session.'
            ))
        
        self.stdout.write(self.style.SUCCESS('  ✅ Prerequisites met'))

    def calculate_staff_counts(self, options):
        """Calculate staff distribution by category"""
        total_staff = options['staff']
        
        # If specific counts provided, use them
        teaching = options.get('teaching_staff')
        admin = options.get('admin_staff')
        support = options.get('support_staff')
        
        if teaching is not None or admin is not None or support is not None:
            teaching = teaching or 0
            admin = admin or 0
            support = support or 0
            total = teaching + admin + support
            
            if total != total_staff:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  Specified counts total {total} but --staff={total_staff}. Adjusting...'
                ))
                # Adjust to match total
                if teaching > 0:
                    teaching += total_staff - total
                elif admin > 0:
                    admin += total_staff - total
                else:
                    support += total_staff - total
        else:
            # Default distribution: 60% teaching, 20% admin, 20% support
            teaching = int(total_staff * 0.6)
            admin = int(total_staff * 0.2)
            support = total_staff - teaching - admin
        
        return {
            'total': total_staff,
            'teaching': teaching,
            'admin': admin,
            'support': support
        }

    def create_staff(self, counts, options):
        """Create staff members"""
        self.stdout.write('\n👥 Creating staff members...')
        
        if self.dry_run:
            self.stdout.write(f'  Would create {counts["total"]} staff members:')
            self.stdout.write(f'    • Teaching: {counts["teaching"]}')
            self.stdout.write(f'    • Admin: {counts["admin"]}')
            self.stdout.write(f'    • Support: {counts["support"]}')
            return
        
        # Get or create default password
        password = options['password']
        
        # Teaching staff
        teaching_success = 0
        for i in range(counts['teaching']):
            try:
                self.create_teaching_staff(i, password)
                teaching_success += 1
            except IntegrityError as e:
                self.handle_creation_error(f"teaching staff #{i+1}", e)
        
        # Admin staff
        admin_success = 0
        for i in range(counts['admin']):
            try:
                self.create_admin_staff(i, password)
                admin_success += 1
            except IntegrityError as e:
                self.handle_creation_error(f"admin staff #{i+1}", e)
        
        # Support staff
        support_success = 0
        for i in range(counts['support']):
            try:
                self.create_support_staff(i, password)
                support_success += 1
            except IntegrityError as e:
                self.handle_creation_error(f"support staff #{i+1}", e)
        
        total_created = teaching_success + admin_success + support_success
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {total_created} staff members'))

    def handle_creation_error(self, item_type, error):
        """Handle creation errors"""
        if self.skip_on_error:
            self.stdout.write(self.style.WARNING(f'    ⚠️  Skipping {item_type}: {str(error)}'))
        else:
            raise error

    def generate_unique_email(self, base_email, prefix=''):
        """Generate a unique email address"""
        if base_email not in self.used_emails:
            self.used_emails.add(base_email)
            return base_email
        
        counter = 1
        while True:
            name_part, domain = base_email.split('@')
            new_email = f"{name_part}{counter}@{domain}"
            if new_email not in self.used_emails:
                self.used_emails.add(new_email)
                return new_email
            counter += 1

    def generate_unique_username(self, base_username):
        """Generate a unique username"""
        if base_username not in self.used_usernames and not User.objects.filter(username=base_username).exists():
            self.used_usernames.add(base_username)
            return base_username
        
        counter = 1
        while True:
            new_username = f"{base_username}{counter}"
            if new_username not in self.used_usernames and not User.objects.filter(username=new_username).exists():
                self.used_usernames.add(new_username)
                return new_username
            counter += 1

    def create_teaching_staff(self, index, password):
        """Create a teaching staff member"""
        gender = random.choice(['M', 'F'])
        
        if gender == 'M':
            first_name = self.get_random_name('male')
            last_name = self.get_random_name('last')
        else:
            first_name = self.get_random_name('female')
            last_name = self.get_random_name('last')
        
        # Generate unique email
        base_email = f"{first_name.lower()}.{last_name.lower()}@school.edu.ng"
        email = self.generate_unique_email(base_email)
        
        username = self.generate_unique_username(f"teacher_{index+1}")
        
        # Create user account if requested
        user = None
        if password:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
        
        # Determine staff type
        if index < 2:
            staff_type = StaffType.PRINCIPAL if index == 0 else StaffType.VICE_PRINCIPAL_1
        elif index < 5:
            staff_type = StaffType.HOD
        else:
            staff_type = random.choice([
                StaffType.SUBJECT_TEACHER,
                StaffType.CLASS_TEACHER,
                StaffType.FORM_MASTER
            ])
        
        # Create staff
        staff = Staff.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=self.random_date(25, 60),
            email=email,
            phone=self.random_phone(),
            address=self.random_address(),
            city=random.choice(['Lagos', 'Abuja', 'Ibadan', 'Kano', 'Port Harcourt']),
            state_of_origin=random.choice(['Lagos', 'Oyo', 'Kano', 'Rivers', 'Abuja']),
            staff_type=staff_type,
            employment_status=EmploymentStatus.ACTIVE,
            employment_type=EmploymentType.PERMANENT,
            shift=ShiftType.FIXED,
            date_employed=self.random_date(1, 10, direction='past'),
            department=random.choice(['Science', 'Arts', 'Commercial', 'Mathematics']),
            highest_qualification=random.choice([
                QualificationType.PHD,
                QualificationType.MASTERS,
                QualificationType.DEGREE,
                QualificationType.PGDE
            ]),
            emergency_contact_name=f"{self.get_random_name('male')} {self.get_random_name('last')}",
            emergency_contact_phone=self.random_phone(),
            emergency_contact_relationship=random.choice(['Spouse', 'Parent', 'Sibling'])
        )
        
        if self.verbose:
            self.stdout.write(f'    ✅ Created teacher: {staff.get_full_name} ({staff.get_staff_type_display()})')
        
        return staff

    def create_admin_staff(self, index, password):
        """Create an administrative staff member"""
        gender = random.choice(['M', 'F'])
        
        if gender == 'M':
            first_name = self.get_random_name('male')
            last_name = self.get_random_name('last')
        else:
            first_name = self.get_random_name('female')
            last_name = self.get_random_name('last')
        
        # Generate unique email
        base_email = f"{first_name.lower()}.{last_name.lower()}@admin.school.edu.ng"
        email = self.generate_unique_email(base_email)
        
        username = self.generate_unique_username(f"admin_{index+1}")
        
        # Create user account if requested
        user = None
        if password:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
        
        staff_types = [
            StaffType.ADMIN_OFFICER,
            StaffType.ADMISSIONS_OFFICER,
            StaffType.ACCOUNTANT,
            StaffType.BURSAR,
            StaffType.SECRETARY,
            StaffType.EXAM_OFFICER,
            StaffType.GUIDANCE_COUNSELOR
        ]
        
        staff = Staff.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=self.random_date(22, 55),
            email=email,
            phone=self.random_phone(),
            address=self.random_address(),
            city='Lagos',
            state_of_origin=random.choice(['Lagos', 'Ogun', 'Oyo', 'Kwara']),
            staff_type=random.choice(staff_types),
            employment_status=EmploymentStatus.ACTIVE,
            employment_type=random.choice([EmploymentType.PERMANENT, EmploymentType.CONTRACT]),
            shift=ShiftType.FIXED,
            date_employed=self.random_date(1, 8, direction='past'),
            department='Administration',
            highest_qualification=random.choice([
                QualificationType.DEGREE,
                QualificationType.MASTERS,
                QualificationType.DIPLOMA
            ]),
            emergency_contact_name=f"{self.get_random_name('male')} {self.get_random_name('last')}",
            emergency_contact_phone=self.random_phone(),
            emergency_contact_relationship=random.choice(['Spouse', 'Parent'])
        )
        
        if self.verbose:
            self.stdout.write(f'    ✅ Created admin: {staff.get_full_name} ({staff.get_staff_type_display()})')
        
        return staff

    def create_support_staff(self, index, password):
        """Create a support staff member"""
        gender = random.choice(['M', 'F'])
        
        if gender == 'M':
            first_name = self.get_random_name('male')
            last_name = self.get_random_name('last')
        else:
            first_name = self.get_random_name('female')
            last_name = self.get_random_name('last')
        
        # Generate unique email
        base_email = f"{first_name.lower()}.{last_name.lower()}@staff.school.edu.ng"
        email = self.generate_unique_email(base_email)
        
        username = self.generate_unique_username(f"support_{index+1}")
        
        # Create user account if requested
        user = None
        if password:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
        
        staff_types = [
            StaffType.LIBRARIAN,
            StaffType.LAB_TECHNICIAN,
            StaffType.ICT_TECHNICIAN,
            StaffType.NURSE,
            StaffType.SECURITY,
            StaffType.CLEANER,
            StaffType.GATE_MAN,
            StaffType.DRIVER,
            StaffType.KITCHEN_STAFF,
            StaffType.GROUNDSKEEPER
        ]
        
        staff = Staff.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=self.random_date(18, 50),
            email=email,
            phone=self.random_phone(),
            address=self.random_address(),
            city='Lagos',
            state_of_origin=random.choice(['Lagos', 'Ogun', 'Oyo', 'Kwara']),
            staff_type=random.choice(staff_types),
            employment_status=EmploymentStatus.ACTIVE,
            employment_type=random.choice([EmploymentType.PERMANENT, EmploymentType.CONTRACT, EmploymentType.PART_TIME]),
            shift=random.choice([ShiftType.MORNING, ShiftType.AFTERNOON, ShiftType.NIGHT]),
            date_employed=self.random_date(1, 5, direction='past'),
            department='Support Services',
            highest_qualification=random.choice([
                QualificationType.DIPLOMA,
                QualificationType.CERTIFICATE,
                QualificationType.DEGREE
            ]),
            emergency_contact_name=f"{self.get_random_name('male')} {self.get_random_name('last')}",
            emergency_contact_phone=self.random_phone(),
            emergency_contact_relationship=random.choice(['Spouse', 'Parent', 'Sibling'])
        )
        
        if self.verbose:
            self.stdout.write(f'    ✅ Created support: {staff.get_full_name} ({staff.get_staff_type_display()})')
        
        return staff

    def create_students(self, options):
        """Create students"""
        self.stdout.write('\n🎓 Creating students...')
        
        num_students = options['students']
        guardians_per_student = min(options['guardians_per_student'], 3)
        create_users = options['create_users']
        password = options['password']
        
        # Get classes
        if options['specific_class']:
            classes = StudentClass.objects.filter(name=options['specific_class'], is_active=True)
            if not classes.exists():
                raise CommandError(f"Class '{options['specific_class']}' not found")
        else:
            classes = StudentClass.objects.filter(is_active=True)
        
        class_list = list(classes)
        
        if options['balance_classes']:
            # Distribute students evenly
            students_per_class = num_students // len(class_list)
            remainder = num_students % len(class_list)
            class_counts = {cls: students_per_class + (1 if i < remainder else 0) 
                           for i, cls in enumerate(class_list)}
        else:
            # Random distribution
            class_counts = {cls: 0 for cls in class_list}
            for _ in range(num_students):
                cls = random.choice(class_list)
                class_counts[cls] += 1
        
        if self.dry_run:
            self.stdout.write(f'  Would create {num_students} students:')
            for cls, count in class_counts.items():
                if count > 0:
                    self.stdout.write(f'    • {cls.display_name}: {count} students')
            return
        
        total_created = 0
        current_session = AcademicSession.objects.filter(is_current=True).first()
        
        for student_class, count in class_counts.items():
            for i in range(count):
                try:
                    student = self.create_single_student(
                        student_class=student_class,
                        session=current_session,
                        guardians_count=guardians_per_student,
                        create_user=create_users,
                        password=password
                    )
                    total_created += 1
                    
                    if self.verbose and total_created % 10 == 0:
                        self.stdout.write(f'    ✅ Created {total_created} students...')
                except IntegrityError as e:
                    self.handle_creation_error(f"student #{total_created+1}", e)
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {total_created} students'))

    def create_single_student(self, student_class, session=None, guardians_count=2, create_user=False, password=None):
        """Create a single student with guardians"""
        gender = random.choice(['M', 'F'])
        
        if gender == 'M':
            first_name = self.get_random_name('male')
            last_name = self.get_random_name('last')
        else:
            first_name = self.get_random_name('female')
            last_name = self.get_random_name('last')
        
        # Calculate age based on class
        age_map = {
            EducationLevel.NURSERY: random.randint(3, 5),
            EducationLevel.PRIMARY: random.randint(6, 11),
            EducationLevel.JSS: random.randint(12, 14),
            EducationLevel.SSS: random.randint(15, 17),
        }
        age = age_map.get(student_class.education_level, 10)
        dob = date.today() - timedelta(days=age*365 + random.randint(0, 365))
        
        # Generate admission number
        try:
            session_code = session.code if session else str(date.today().year)
            admission_number = AdmissionNumberService.generate_admission_number(
                class_name=student_class.name,
                session_code=session_code
            )
        except Exception as e:
            # Fallback if service fails
            self.stderr.write(self.style.WARNING(f"Admission number generation failed: {e}"))
            last_student = Student.objects.order_by('-id').first()
            next_id = (last_student.id + 1) if last_student else 1
            admission_number = f"{date.today().year}/{student_class.name}/{next_id:03d}"
        
        # Generate unique email
        base_email = f"{first_name.lower()}.{last_name.lower()}@student.edu.ng"
        email = self.generate_unique_email(base_email)
        
        # Create user if requested
        user = None
        if create_user:
            username = self.generate_unique_username(f"student_{first_name.lower()}")
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
        
        # Create student
        student = Student.objects.create(
            user=user,
            admission_number=admission_number,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=dob,
            email=email,
            phone=self.random_phone(),
            address=self.random_address(),
            city=random.choice(['Lagos', 'Abuja', 'Ibadan', 'Kano', 'Port Harcourt']),
            state_of_origin=random.choice(['Lagos', 'Oyo', 'Kano', 'Rivers', 'Abuja', 'Enugu']),
            current_class=student_class,
            enrollment_date=date.today() - timedelta(days=random.randint(30, 365)),
            enrollment_session=session,
            status=StudentStatus.ACTIVE,
            created_via=StudentCreationMethod.MANUAL
        )
        
        # Create guardians
        self.create_guardians_for_student(student, guardians_count)
        
        return student

    def create_guardians_for_student(self, student, count=2):
        """Create guardians for a student"""
        guardians = []
        
        # Always create at least one primary guardian
        primary_created = False
        
        for i in range(count):
            # First guardian is usually primary and opposite gender of student
            if i == 0:
                is_primary = True
                primary_created = True
                # Mother for male students, father for female students (60% of time)
                if student.gender == 'M':
                    gender = 'F' if random.random() < 0.6 else 'M'
                else:
                    gender = 'M' if random.random() < 0.6 else 'F'
            else:
                is_primary = False
                gender = random.choice(['M', 'F'])
            
            # Determine relationship
            if gender == 'M':
                relationship = random.choice([
                    GuardianRelationship.FATHER,
                    GuardianRelationship.GUARDIAN,
                    GuardianRelationship.SIBLING
                ])
                first_name = self.get_random_name('male')
            else:
                relationship = random.choice([
                    GuardianRelationship.MOTHER,
                    GuardianRelationship.GUARDIAN,
                    GuardianRelationship.SIBLING
                ])
                first_name = self.get_random_name('female')
            
            last_name = student.last_name if relationship in [GuardianRelationship.FATHER, GuardianRelationship.MOTHER] else self.get_random_name('last')
            
            # Generate unique email for guardian
            base_email = f"{first_name.lower()}.{last_name.lower()}@parent.com"
            email = self.generate_unique_email(base_email)
            
            guardian = Guardian.objects.create(
                student=student,
                first_name=first_name,
                last_name=last_name,
                relationship=relationship,
                email=email,
                phone=self.random_phone(),
                address=student.address,
                occupation=random.choice(['Teacher', 'Engineer', 'Doctor', 'Business', 'Civil Servant']),
                is_primary=is_primary,
                is_emergency_contact=True
            )
            
            guardians.append(guardian)
        
        # If no primary guardian was created, make the first one primary
        if not primary_created and guardians:
            guardians[0].is_primary = True
            guardians[0].save()
        
        return guardians

    def create_parent_portals(self):
        """Create parent portal accounts for guardians"""
        self.stdout.write('\n👪 Creating parent portal accounts...')
        
        guardians = Guardian.objects.filter(is_primary=True)
        total = guardians.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('  ⚠️  No guardians found to create parent portals'))
            return
        
        if self.dry_run:
            self.stdout.write(f'  Would create {total} parent portal accounts')
            return
        
        created = 0
        for guardian in guardians:
            try:
                # Check if parent profile already exists
                if ParentProfile.objects.filter(guardian_id=guardian.id).exists():
                    continue
                
                # Ensure guardian has email
                if not guardian.email:
                    guardian.email = self.generate_unique_email(f"{guardian.first_name.lower()}.{guardian.last_name.lower()}@parent.com")
                    guardian.save()
                
                # Create parent profile
                profile = ParentProfile.objects.create(
                    guardian_id=guardian.id,
                    first_name=guardian.first_name,
                    last_name=guardian.last_name,
                    email=guardian.email,
                    phone=guardian.phone,
                    access_status='active'
                )
                
                # Link to student
                ChildLink.objects.create(
                    parent=profile,
                    student_id=guardian.student.id,
                    student_name=guardian.student.get_full_name,
                    student_class=guardian.student.current_class.display_name,
                    relationship=guardian.relationship,
                    is_primary=guardian.is_primary
                )
                
                created += 1
                
                if self.verbose and created % 10 == 0:
                    self.stdout.write(f'    ✅ Created {created} parent portals...')
                    
            except IntegrityError as e:
                self.handle_creation_error(f"parent portal for {guardian.get_full_name}", e)
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {created} parent portal accounts'))

    def print_summary(self):
        """Print summary of created data"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 CREATION SUMMARY'))
        self.stdout.write('='*60)
        
        # Staff
        staff_count = Staff.objects.count()
        self.stdout.write(f'\n👥 Staff: {staff_count}')
        if staff_count > 0:
            self.stdout.write(f'  • Teaching: {Staff.objects.filter(staff_category=StaffCategory.ACADEMIC).count()}')
            self.stdout.write(f'  • Admin: {Staff.objects.filter(staff_category=StaffCategory.ADMIN).count()}')
            self.stdout.write(f'  • Support: {Staff.objects.exclude(staff_category__in=[StaffCategory.ACADEMIC, StaffCategory.ADMIN]).count()}')
        
        # Students
        student_count = Student.objects.count()
        self.stdout.write(f'\n🎓 Students: {student_count}')
        if student_count > 0:
            self.stdout.write(f'  • Male: {Student.objects.filter(gender="M").count()}')
            self.stdout.write(f'  • Female: {Student.objects.filter(gender="F").count()}')
            
            # Students by class
            self.stdout.write(f'  • By Class:')
            for class_obj in StudentClass.objects.filter(is_active=True).order_by('sort_order')[:5]:
                count = Student.objects.filter(current_class=class_obj).count()
                if count > 0:
                    self.stdout.write(f'    - {class_obj.display_name}: {count}')
        
        # Guardians
        guardian_count = Guardian.objects.count()
        self.stdout.write(f'\n👥 Guardians: {guardian_count}')
        
        # Parent portals
        parent_count = ParentProfile.objects.count()
        self.stdout.write(f'\n👪 Parent Portals: {parent_count}')
        if parent_count > 0:
            links = ChildLink.objects.count()
            self.stdout.write(f'  • Child Links: {links}')
            self.stdout.write(f'  • Avg Children per Parent: {links/parent_count:.1f}')

    # Helper methods for random data generation
    def get_random_name(self, name_type='male'):
        """Get random Nigerian name"""
        names = {
            'male': ['Olufemi', 'Adebayo', 'Chinedu', 'Emeka', 'Ibrahim', 'Musa', 'Tunde', 'Segun', 'Femi', 'Kayode', 'Johnson', 'Michael', 'Peter', 'James', 'John'],
            'female': ['Funke', 'Adaeze', 'Ngozi', 'Aisha', 'Fatima', 'Bisi', 'Folake', 'Titilayo', 'Chiamaka', 'Zainab', 'Mary', 'Patience', 'Gift', 'Blessing', 'Esther'],
            'last': ['Okafor', 'Okonkwo', 'Bello', 'Abubakar', 'Adeyemi', 'Ogunleye', 'Eze', 'Nwosu', 'Mohammed', 'Yusuf', 'Adamu', 'Ibrahim', 'Olawale', 'Adebayo', 'Okoro']
        }
        return random.choice(names.get(name_type, names['male']))

    def random_phone(self):
        """Generate random Nigerian phone number"""
        prefixes = ['080', '081', '090', '070', '091']
        number = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        return random.choice(prefixes) + number

    def random_address(self):
        """Generate random Nigerian address"""
        streets = ['Allen Avenue', 'Adeniran Ogunsanya', 'Broad Street', 'Marina', 'Isaac John', 'Awolowo Road', 'Falomo', 'Ahmadu Bello Way']
        areas = ['Ikeja', 'Surulere', 'Victoria Island', 'Lekki', 'Yaba', 'Garki', 'Wuse', 'Maitama']
        return f"{random.randint(1, 50)} {random.choice(streets)}, {random.choice(areas)}"

    def random_date(self, min_age, max_age, direction='past'):
        """Generate random date"""
        if direction == 'past':
            days_ago = random.randint(min_age*365, max_age*365)
            return date.today() - timedelta(days=days_ago)
        else:
            days_ahead = random.randint(min_age*365, max_age*365)
            return date.today() + timedelta(days=days_ahead)
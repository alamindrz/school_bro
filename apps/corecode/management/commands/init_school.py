"""
Management command to initialize school data
Run: python manage.py init_school [--with-test-data] [--create-admin] [--num-students=50]
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from datetime import date, timedelta
import random

# Corecode imports
from apps.corecode.services import StudentClassService, SiteConfigService, AcademicSessionService, AcademicTermService
from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass
from apps.corecode.constants import EducationLevel, SiteConfigKey

# Results imports
from apps.results.models import Subject
from apps.results.constants import SubjectType

# Finance imports
from apps.finance.models import FeeStructure
from apps.finance.constants import FeeType, FeeTerm

# Students imports (for test data)
from apps.students.models import Student, Guardian
from apps.students.constants import StudentStatus, GuardianRelationship
from apps.students.services.admission_number import AdmissionNumberService

# Staff imports (for test data)
from apps.staffs.models import Staff
from apps.staffs.constants import StaffType, EmploymentStatus

# Parents imports (for test data)
from apps.parents.models import ParentProfile, ChildLink

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize school with Nigerian 6-3-3-4 structure and default data'

    def add_arguments(self, parser):
        # Admin user options
        parser.add_argument('--create-admin', action='store_true', help='Create admin user')
        parser.add_argument('--admin-email', type=str, default='admin@school.edu.ng', help='Admin email')
        parser.add_argument('--admin-password', type=str, default='admin123', help='Admin password')
        parser.add_argument('--admin-username', type=str, default='admin', help='Admin username')
        
        # Test data options
        parser.add_argument('--with-test-data', action='store_true', help='Generate test data')
        parser.add_argument('--num-students', type=int, default=50, help='Number of test students to create')
        parser.add_argument('--num-staff', type=int, default=20, help='Number of test staff to create')
        parser.add_argument('--current-session', type=str, help='Set current session (e.g., "2024/2025")')
        
        # Force overwrite options
        parser.add_argument('--force', action='store_true', help='Force overwrite existing data')

    @transaction.atomic
    def handle(self, *args, **options):
        # Store options as instance variables for access in other methods
        self.force = options.get('force', False)
        self.current_session_name = options.get('current_session')
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('🚀 SCHOOL INITIALIZATION STARTING'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        # Step 1: Create Nigerian 6-3-3-4 classes
        self.create_classes()
        
        # Step 2: Initialize site configurations
        self.create_site_configs()
        
        # Step 3: Create Nigerian curriculum subjects
        self.create_subjects()
        
        # Step 4: Create academic sessions and terms
        self.create_academic_structure()
        
        # Step 5: Create default fee structures
        self.create_fee_structures()
        
        # Step 6: Create admin user if requested
        if options['create_admin']:
            self.create_admin_user(
                email=options['admin_email'],
                password=options['admin_password'],
                username=options['admin_username']
            )
        
        # Step 7: Generate test data if requested
        if options.get('with_test_data'):
            self.generate_test_data(
                num_students=options['num_students'],
                num_staff=options['num_staff']
            )
        
        self.print_summary()
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('✅ SCHOOL INITIALIZATION COMPLETE'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

    def create_classes(self):
        """Create all Nigerian 6-3-3-4 classes"""
        self.stdout.write('\n📚 Creating Nigerian 6-3-3-4 classes...')
        
        # Check if classes already exist
        existing_count = StudentClass.objects.count()
        if existing_count >= 15 and not self.force:
            self.stdout.write(self.style.WARNING(f'  ⏩ {existing_count} classes already exist. Use --force to recreate.'))
            return
        
        if existing_count > 0 and self.force:
            self.stdout.write('  ⚠️  Deleting existing classes...')
            StudentClass.objects.all().delete()
        
        classes = StudentClassService.bulk_create_nigerian_classes()
        
        # Display created classes by level
        levels = {
            EducationLevel.NURSERY: [],
            EducationLevel.PRIMARY: [],
            EducationLevel.JSS: [],
            EducationLevel.SSS: [],
        }
        
        for cls in classes:
            levels[cls.education_level].append(cls.display_name)
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {len(classes)} classes:'))
        for level, class_list in levels.items():
            if class_list:
                self.stdout.write(f'     • {level.title()}: {", ".join(class_list)}')

    def create_site_configs(self):
        """Initialize site configurations"""
        self.stdout.write('\n⚙️  Initializing site configurations...')
        
        configs = SiteConfigService.initialize_default_configs()
        
        # Set additional defaults
        from apps.corecode.models import SiteConfig
        SiteConfig.objects.update_or_create(
            key=SiteConfigKey.COMPANY_NAME,
            defaults={'value': 'DETs Toolkit School', 'description': 'School name'}
        )
        SiteConfig.objects.update_or_create(
            key=SiteConfigKey.PASS_MARK,
            defaults={'value': '40', 'description': 'Minimum pass mark'}
        )
        SiteConfig.objects.update_or_create(
            key=SiteConfigKey.DISTINCTION_MARK,
            defaults={'value': '70', 'description': 'Minimum distinction mark'}
        )
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Initialized {len(configs) + 3} configurations'))

    def create_subjects(self):
        """Create Nigerian curriculum subjects"""
        self.stdout.write('\n📖 Creating Nigerian curriculum subjects...')
        
        # Check if subjects already exist
        if Subject.objects.exists() and not self.force:
            self.stdout.write(self.style.WARNING(f'  ⏩ Subjects already exist. Use --force to recreate.'))
            return
        
        if Subject.objects.exists() and self.force:
            self.stdout.write('  ⚠️  Deleting existing subjects...')
            Subject.objects.all().delete()
        
        # Core subjects (offered in all classes)
        core_subjects = [
            {'name': 'English Language', 'code': 'ENG', 'type': SubjectType.CORE, 'core': True},
            {'name': 'Mathematics', 'code': 'MTH', 'type': SubjectType.CORE, 'core': True},
            {'name': 'Civic Education', 'code': 'CIV', 'type': SubjectType.CORE, 'core': True},
            {'name': 'Biology', 'code': 'BIO', 'type': SubjectType.CORE, 'core': True},
            {'name': 'Chemistry', 'code': 'CHM', 'type': SubjectType.CORE, 'core': True},
            {'name': 'Physics', 'code': 'PHY', 'type': SubjectType.CORE, 'core': True},
            {'name': 'Literature in English', 'code': 'LIT', 'type': SubjectType.CORE, 'core': True},
            {'name': 'Government', 'code': 'GOV', 'type': SubjectType.CORE, 'core': True},
            {'name': 'Economics', 'code': 'ECO', 'type': SubjectType.CORE, 'core': True},
            {'name': 'Geography', 'code': 'GEO', 'type': SubjectType.CORE, 'core': True},
        ]
        
        # Elective subjects (for secondary)
        elective_subjects = [
            {'name': 'Further Mathematics', 'code': 'FUR', 'type': SubjectType.ELECTIVE, 'core': False},
            {'name': 'Accounting', 'code': 'ACC', 'type': SubjectType.ELECTIVE, 'core': False},
            {'name': 'Commerce', 'code': 'COM', 'type': SubjectType.ELECTIVE, 'core': False},
            {'name': 'History', 'code': 'HIS', 'type': SubjectType.ELECTIVE, 'core': False},
            {'name': 'Islamic Studies', 'code': 'IRS', 'type': SubjectType.ELECTIVE, 'core': False},
            {'name': 'Christian Religious Studies', 'code': 'CRS', 'type': SubjectType.ELECTIVE, 'core': False},
            {'name': 'French', 'code': 'FRE', 'type': SubjectType.ELECTIVE, 'core': False},
            {'name': 'Arabic', 'code': 'ARB', 'type': SubjectType.ELECTIVE, 'core': False},
        ]
        
        # Vocational subjects
        vocational_subjects = [
            {'name': 'Agriculture', 'code': 'AGR', 'type': SubjectType.VOCATIONAL, 'core': False},
            {'name': 'Food and Nutrition', 'code': 'FDN', 'type': SubjectType.VOCATIONAL, 'core': False},
            {'name': 'Technical Drawing', 'code': 'TDR', 'type': SubjectType.VOCATIONAL, 'core': False},
            {'name': 'Computer Studies', 'code': 'CSC', 'type': SubjectType.VOCATIONAL, 'core': False},
            {'name': 'Woodwork', 'code': 'WDW', 'type': SubjectType.VOCATIONAL, 'core': False},
            {'name': 'Metalwork', 'code': 'MTW', 'type': SubjectType.VOCATIONAL, 'core': False},
            {'name': 'Electronics', 'code': 'ELE', 'type': SubjectType.VOCATIONAL, 'core': False},
            {'name': 'Auto Mechanics', 'code': 'AUM', 'type': SubjectType.VOCATIONAL, 'core': False},
        ]
        
        all_subjects = core_subjects + elective_subjects + vocational_subjects
        
        created_count = 0
        for subject_data in all_subjects:
            subject, created = Subject.objects.get_or_create(
                code=subject_data['code'],
                defaults={
                    'name': subject_data['name'],
                    'subject_type': subject_data['type'],
                    'is_nigerian_core': subject_data['core'],
                    'is_active': True
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {created_count} subjects'))
        self.stdout.write(f'     • Core: {len(core_subjects)}')
        self.stdout.write(f'     • Elective: {len(elective_subjects)}')
        self.stdout.write(f'     • Vocational: {len(vocational_subjects)}')

    def create_academic_structure(self):
        """Create academic sessions and terms"""
        self.stdout.write('\n📅 Creating academic sessions and terms...')
        
        current_year = date.today().year
        
        # Create past 2 years, current year, and next year
        for year_offset in range(-1, 2):  # -1, 0, 1
            year = current_year + year_offset
            session_name = f"{year}/{year+1}"
            session_code = f"{year}{year+1}"
            
            # Check if session exists
            session, created = AcademicSession.objects.get_or_create(
                name=session_name,
                defaults={
                    'code': session_code,
                    'start_date': date(year, 9, 1),  # Nigerian academic year starts September
                    'end_date': date(year+1, 8, 31),
                    'is_current': (session_name == self.current_session_name) or (year_offset == 0 and not self.current_session_name)
                }
            )
            
            if created:
                # Create three terms for the session
                term_length = (session.end_date - session.start_date).days // 3
                
                for term_num in range(1, 4):
                    term_start = session.start_date + timedelta(days=term_length * (term_num - 1))
                    term_end = session.start_date + timedelta(days=term_length * term_num - 1)
                    if term_num == 3:
                        term_end = session.end_date
                    
                    AcademicTerm.objects.create(
                        session=session,
                        term=term_num,
                        name=f"{dict({1:'First',2:'Second',3:'Third'})[term_num]} Term {session_name}",
                        start_date=term_start,
                        end_date=term_end,
                        is_current=(year_offset == 0 and term_num == 1)  # First term of current year is current
                    )
                
                self.stdout.write(f'  ✅ Created session: {session_name} with 3 terms')
            else:
                self.stdout.write(f'  ⏩ Session already exists: {session_name}')

    def create_fee_structures(self):
        """Create default fee structures for all classes"""
        self.stdout.write('\n💰 Creating default fee structures...')
        
        classes = StudentClass.objects.filter(is_active=True)
        current_session = AcademicSession.objects.filter(is_current=True).first()
        
        if not current_session:
            self.stdout.write(self.style.WARNING('  ⚠️  No current session found. Skipping fee structures.'))
            return
        
        fee_configs = [
            # (fee_type, term_type, base_amount_multiplier, description)
            (FeeType.TUITION, FeeTerm.PER_TERM, 1.0, 'Tuition fee per term'),
            (FeeType.DEVELOPMENT, FeeTerm.PER_SESSION, 0.2, 'Development levy'),
            (FeeType.LIBRARY, FeeTerm.PER_TERM, 0.05, 'Library fee'),
            (FeeType.SPORTS, FeeTerm.PER_TERM, 0.03, 'Sports fee'),
            (FeeType.ICT, FeeTerm.PER_TERM, 0.04, 'ICT fee'),
            (FeeType.EXAM, FeeTerm.PER_TERM, 0.1, 'Examination fee'),
        ]
        
        # Base amounts by education level
        base_amounts = {
            EducationLevel.NURSERY: 50000,
            EducationLevel.PRIMARY: 75000,
            EducationLevel.JSS: 100000,
            EducationLevel.SSS: 125000,
        }
        
        created_count = 0
        for class_obj in classes:
            base = base_amounts.get(class_obj.education_level, 50000)
            
            for fee_type, term_type, multiplier, description in fee_configs:
                amount = int(base * multiplier)
                
                fee, created = FeeStructure.objects.get_or_create(
                    student_class=class_obj,
                    fee_type=fee_type,
                    term=term_type,
                    academic_session=current_session,
                    defaults={
                        'amount': amount,
                        'description': description,
                        'is_active': True
                    }
                )
                if created:
                    created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {created_count} fee structures'))

    def create_admin_user(self, email, password, username):
        """Create admin superuser"""
        self.stdout.write('\n👤 Creating admin user...')
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'  ⏩ Admin user {username} already exists'))
            return
        
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            first_name='System',
            last_name='Administrator'
        )
        self.stdout.write(self.style.SUCCESS(f'  ✅ Admin user created:'))
        self.stdout.write(f'     • Username: {username}')
        self.stdout.write(f'     • Email: {email}')
        self.stdout.write(f'     • Password: {password}')

    def generate_test_data(self, num_students=50, num_staff=20):
        """Generate test data for development"""
        self.stdout.write('\n🧪 Generating test data...')
        
        try:
            from faker import Faker
            fake = Faker('en_NG')
        except ImportError:
            self.stdout.write(self.style.ERROR('  ❌ Faker not installed. Install with: pip install faker'))
            return
        
        current_session = AcademicSession.objects.filter(is_current=True).first()
        classes = list(StudentClass.objects.filter(is_active=True))
        
        if not classes:
            self.stdout.write(self.style.ERROR('  ❌ No classes found. Run initialization first.'))
            return
        
        # Create test staff
        self.stdout.write(f'\n  Creating {num_staff} test staff members...')
        staff_types = [t[0] for t in StaffType.CHOICES if t[0] not in [StaffType.PRINCIPAL]]
        
        for i in range(num_staff):
            gender = random.choice(['M', 'F'])
            first_name = fake.first_name_male() if gender == 'M' else fake.first_name_female()
            last_name = fake.last_name()
            
            staff = Staff.objects.create(
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                email=fake.email(),
                phone=fake.phone_number()[:15],
                address=fake.address(),
                city=fake.city(),
                state_of_origin=random.choice(['Lagos', 'Abuja', 'Kano', 'Rivers']),
                staff_type=random.choice(staff_types),
                employment_status=EmploymentStatus.ACTIVE,
                date_employed=fake.date_between(start_date='-5y', end_date='-1m'),
                emergency_contact_name=fake.name(),
                emergency_contact_phone=fake.phone_number()[:15],
                emergency_contact_relationship=random.choice(['Spouse', 'Parent', 'Sibling'])
            )
            
            if (i + 1) % 10 == 0:
                self.stdout.write(f'     ✅ Created {i + 1} staff members...')
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {num_staff} staff members'))
        
        # Create test students
        self.stdout.write(f'\n  Creating {num_students} test students...')
        
        for i in range(num_students):
            gender = random.choice(['M', 'F'])
            first_name = fake.first_name_male() if gender == 'M' else fake.first_name_female()
            last_name = fake.last_name()
            student_class = random.choice(classes)
            
            # Generate admission number
            try:
                admission_number = AdmissionNumberService.generate_admission_number(
                    class_name=student_class.name,
                    session_code=current_session.code if current_session else str(date.today().year)
                )
            except:
                admission_number = f"{date.today().year}/{student_class.name}/{i+1:03d}"
                        # Calculate date of birth based on class
            age_map = {
                EducationLevel.NURSERY: random.randint(3, 5),
                EducationLevel.PRIMARY: random.randint(6, 11),
                EducationLevel.JSS: random.randint(12, 14),
                EducationLevel.SSS: random.randint(15, 17),
            }
            age = age_map.get(student_class.education_level, 10)
            dob = date.today() - timedelta(days=age*365 + random.randint(0, 365))
            
            student = Student.objects.create(
                admission_number=admission_number,
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                date_of_birth=dob,
                email=fake.email(),
                phone=fake.phone_number()[:15],
                address=fake.address(),
                city=fake.city(),
                state_of_origin=random.choice(['Lagos', 'Abuja', 'Kano', 'Rivers', 'Oyo']),
                current_class=student_class,
                enrollment_date=fake.date_between(start_date='-3y', end_date='-1m'),
                enrollment_session=current_session,
                status=StudentStatus.ACTIVE
            )
            
            # Create guardian
            guardian_gender = random.choice(['M', 'F'])
            guardian_first = fake.first_name_male() if guardian_gender == 'M' else fake.first_name_female()
            guardian_rel = GuardianRelationship.FATHER if guardian_gender == 'M' else GuardianRelationship.MOTHER
            
            Guardian.objects.create(
                student=student,
                first_name=guardian_first,
                last_name=last_name,
                relationship=guardian_rel,
                email=fake.email(),
                phone=fake.phone_number()[:15],
                is_primary=True,
                is_emergency_contact=True
            )
            
            if (i + 1) % 10 == 0:
                self.stdout.write(f'     ✅ Created {i + 1} students...')
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {num_students} students with guardians'))

    def print_summary(self):
        """Print initialization summary"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 INITIALIZATION SUMMARY'))
        self.stdout.write('='*60)
        
        # Corecode
        self.stdout.write(f'\n🏛️  Corecode:')
        self.stdout.write(f'  • Classes: {StudentClass.objects.count()}')
        self.stdout.write(f'  • Sessions: {AcademicSession.objects.count()}')
        self.stdout.write(f'  • Terms: {AcademicTerm.objects.count()}')
        
        # Subjects
        self.stdout.write(f'\n📖 Subjects:')
        self.stdout.write(f'  • Total: {Subject.objects.count()}')
        
        # Finance
        self.stdout.write(f'\n💰 Finance:')
        self.stdout.write(f'  • Fee Structures: {FeeStructure.objects.count()}')
        
        # Test data (if generated)
        if Student.objects.exists():
            self.stdout.write(f'\n🎓 Students: {Student.objects.count()}')
            self.stdout.write(f'👥 Guardians: {Guardian.objects.count()}')
        
        if Staff.objects.exists():
            self.stdout.write(f'👤 Staff: {Staff.objects.count()}')
        
        if ParentProfile.objects.exists():
            self.stdout.write(f'👪 Parent Profiles: {ParentProfile.objects.count()}')

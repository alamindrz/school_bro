"""
Management command to initialize the entire school system
Run: python manage.py init_system
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta, datetime
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize complete school system with all required data'

    def add_arguments(self, parser):
        parser.add_argument('--staff-password', type=str, default='staff123', help='Default password for staff')
        parser.add_argument('--parent-password', type=str, default='parent123', help='Default password for parents')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🚀 Initializing School System...\n'))
        
        staff_password = options['staff_password']
        parent_password = options['parent_password']
        
        # Step 1: Create superuser
        self.create_superuser()
        
        # Step 2: Create academic sessions and terms
        self.create_academic_structure()
        
        # Step 3: Create classes with streams
        self.create_classes()
        
        # Step 4: Create subjects
        self.create_subjects()
        
        # Step 5: Create timetable base data (SchoolDays, PeriodTypes, TimetablePeriods)
        self.create_timetable_base_data()
        
        # Step 6: Create staff
        self.create_staff(staff_password)
        
        # Step 7: Create students and parents
        self.create_students_and_parents(parent_password)
        
        # Step 8: Create admissions period
        self.create_admissions_period()
        
        # Step 9: Create fee structures
        self.create_fee_structures()
        
        self.stdout.write(self.style.SUCCESS('\n✅ System initialization complete!\n'))
    
    def create_superuser(self):
        self.stdout.write('Creating superuser...')
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@school.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write(self.style.SUCCESS('  ✅ Superuser created (admin/admin123)'))
        else:
            self.stdout.write('  ⏩ Superuser already exists')
    
    def create_academic_structure(self):
        from apps.corecode.models import AcademicSession, AcademicTerm
        
        self.stdout.write('\nCreating academic sessions and terms...')
        
        current_year = date.today().year
        sessions = []
        
        for year_offset in range(-1, 2):  # -1, 0, 1
            year = current_year + year_offset
            session_name = f"{year}/{year+1}"
            session_code = f"{year}{year+1}"
            is_current = (year_offset == 0)
            
            session, created = AcademicSession.objects.get_or_create(
                name=session_name,
                defaults={
                    'code': session_code,
                    'start_date': date(year, 9, 1),
                    'end_date': date(year+1, 8, 31),
                    'is_current': is_current
                }
            )
            sessions.append(session)
            self.stdout.write(f'  {"✅ Created" if created else "⏩ Exists"} session: {session_name}')
        
        # Create terms for each session
        for session in sessions:
            term_length = (session.end_date - session.start_date).days // 3
            
            for term_num in range(1, 4):
                term_start = session.start_date + timedelta(days=term_length * (term_num - 1))
                term_end = session.start_date + timedelta(days=term_length * term_num - 1)
                if term_num == 3:
                    term_end = session.end_date
                
                term_name = f"{['First', 'Second', 'Third'][term_num-1]} Term {session.name}"
                is_current = (session.is_current and term_num == 1)
                
                term, created = AcademicTerm.objects.get_or_create(
                    session=session,
                    term=term_num,
                    defaults={
                        'name': term_name,
                        'start_date': term_start,
                        'end_date': term_end,
                        'is_current': is_current
                    }
                )
                if created:
                    self.stdout.write(f'    ✅ Created term: {term_name}')
    
    def create_classes(self):
        from apps.corecode.models import StudentClass
        from apps.corecode.constants import EducationLevel, NigerianClassLevel
        
        self.stdout.write('\nCreating classes with streams...')
        
        # Define classes with streams
        class_definitions = [
            # Nursery (3 years)
            (NigerianClassLevel.NURSERY_1, 'Nursery 1', EducationLevel.NURSERY, 25),
            (NigerianClassLevel.NURSERY_2, 'Nursery 2', EducationLevel.NURSERY, 25),
            (NigerianClassLevel.NURSERY_3, 'Nursery 3', EducationLevel.NURSERY, 25),
            # Primary (6 years)
            (NigerianClassLevel.PRIMARY_1, 'Primary 1', EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_2, 'Primary 2', EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_3, 'Primary 3', EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_4, 'Primary 4', EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_5, 'Primary 5', EducationLevel.PRIMARY, 40),
            (NigerianClassLevel.PRIMARY_6, 'Primary 6', EducationLevel.PRIMARY, 40),
            # Junior Secondary (3 years) - with streams A, B
            (NigerianClassLevel.JSS_1, 'JSS 1', EducationLevel.JSS, 45),
            (NigerianClassLevel.JSS_2, 'JSS 2', EducationLevel.JSS, 45),
            (NigerianClassLevel.JSS_3, 'JSS 3', EducationLevel.JSS, 45),
            # Senior Secondary (3 years) - with streams A, B, C
            (NigerianClassLevel.SS_1, 'SS 1', EducationLevel.SSS, 45),
            (NigerianClassLevel.SS_2, 'SS 2', EducationLevel.SSS, 45),
            (NigerianClassLevel.SS_3, 'SS 3', EducationLevel.SSS, 45),
        ]
        
        # Streams for secondary classes
        streams = ['A', 'B', 'C']
        secondary_levels = [NigerianClassLevel.JSS_1, NigerianClassLevel.JSS_2, NigerianClassLevel.JSS_3,
                            NigerianClassLevel.SS_1, NigerianClassLevel.SS_2, NigerianClassLevel.SS_3]
        
        order = 0
        for name, display_base, level, max_students in class_definitions:
            if name in secondary_levels:
                # Create multiple streams
                for stream in streams:
                    stream_name = f"{name}{stream}"
                    stream_display = f"{display_base} {stream}"
                    class_obj, created = StudentClass.objects.get_or_create(
                        name=name,
                        stream=stream,
                        defaults={
                            'display_name': stream_display,
                            'education_level': level,
                            'max_students': max_students,
                            'sort_order': order,
                            'is_active': True
                        }
                    )
                    if created:
                        self.stdout.write(f'  ✅ Created class: {stream_display}')
                    order += 1
            else:
                # Create single class without stream
                class_obj, created = StudentClass.objects.get_or_create(
                    name=name,
                    stream='',
                    defaults={
                        'display_name': display_base,
                        'education_level': level,
                        'max_students': max_students,
                        'sort_order': order,
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(f'  ✅ Created class: {display_base}')
                order += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {StudentClass.objects.count()} classes'))
    
    def create_subjects(self):
        from apps.corecode.models import Subject, StudentClass
        
        self.stdout.write('\nCreating subjects...')
        
        subjects_data = [
            # Core Subjects
            {'name': 'English Language', 'code': 'ENG', 'type': 'core', 'core': True},
            {'name': 'Mathematics', 'code': 'MTH', 'type': 'core', 'core': True},
            {'name': 'Civic Education', 'code': 'CIV', 'type': 'core', 'core': True},
            {'name': 'Biology', 'code': 'BIO', 'type': 'core', 'core': True},
            {'name': 'Chemistry', 'code': 'CHM', 'type': 'core', 'core': True},
            {'name': 'Physics', 'code': 'PHY', 'type': 'core', 'core': True},
            {'name': 'Literature in English', 'code': 'LIT', 'type': 'core', 'core': True},
            {'name': 'Government', 'code': 'GOV', 'type': 'core', 'core': True},
            {'name': 'Economics', 'code': 'ECO', 'type': 'core', 'core': True},
            {'name': 'Geography', 'code': 'GEO', 'type': 'core', 'core': True},
            # Elective Subjects
            {'name': 'Further Mathematics', 'code': 'FUR', 'type': 'elective', 'core': False},
            {'name': 'Accounting', 'code': 'ACC', 'type': 'elective', 'core': False},
            {'name': 'Commerce', 'code': 'COM', 'type': 'elective', 'core': False},
            {'name': 'History', 'code': 'HIS', 'type': 'elective', 'core': False},
            {'name': 'Islamic Studies', 'code': 'IRS', 'type': 'elective', 'core': False},
            {'name': 'Christian Religious Studies', 'code': 'CRS', 'type': 'elective', 'core': False},
            {'name': 'French', 'code': 'FRE', 'type': 'elective', 'core': False},
            # Vocational Subjects
            {'name': 'Agriculture', 'code': 'AGR', 'type': 'vocational', 'core': False},
            {'name': 'Computer Studies', 'code': 'CSC', 'type': 'vocational', 'core': False},
            {'name': 'Technical Drawing', 'code': 'TDR', 'type': 'vocational', 'core': False},
            {'name': 'Food and Nutrition', 'code': 'FDN', 'type': 'vocational', 'core': False},
        ]
        
        # Get all secondary classes for subject offering
        secondary_classes = StudentClass.objects.filter(
            education_level__in=['jss', 'sss']
        )
        
        created_count = 0
        for subject_data in subjects_data:
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
                # Add to all secondary classes
                subject.offered_in_classes.add(*secondary_classes)
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {created_count} subjects'))
    
    def create_timetable_base_data(self):
        from apps.timetable.models import SchoolDay, PeriodType, TimetablePeriod
        from datetime import time
        
        self.stdout.write('\nCreating timetable base data...')
        
        # Create School Days
        days_data = [
            {'day_number': 1, 'name': 'Monday', 'order': 1, 'is_active': True},
            {'day_number': 2, 'name': 'Tuesday', 'order': 2, 'is_active': True},
            {'day_number': 3, 'name': 'Wednesday', 'order': 3, 'is_active': True},
            {'day_number': 4, 'name': 'Thursday', 'order': 4, 'is_active': True},
            {'day_number': 5, 'name': 'Friday', 'order': 5, 'is_active': True, 'is_friday': True},
        ]
        
        for day_data in days_data:
            day, created = SchoolDay.objects.get_or_create(
                day_number=day_data['day_number'],
                defaults=day_data
            )
            if created:
                self.stdout.write(f'  ✅ Created day: {day.name}')
        
        # Create Period Types
        teaching_type, created = PeriodType.objects.get_or_create(
            code='teaching',
            defaults={
                'name': 'Teaching Period',
                'is_teaching': True,
                'duration_minutes': 40,
                'color': '#3b82f6'
            }
        )
        if created:
            self.stdout.write('  ✅ Created period type: Teaching')
        
        break_type, created = PeriodType.objects.get_or_create(
            code='break',
            defaults={
                'name': 'Break Period',
                'is_teaching': False,
                'duration_minutes': 30,
                'color': '#f59e0b',
                'is_break': True,
                'break_duration_minutes': 30
            }
        )
        if created:
            self.stdout.write('  ✅ Created period type: Break')
        
        # Create Timetable Periods
        periods_data = [
            {'display_name': 'Period 1', 'order': 1, 'start': time(8, 0), 'end': time(8, 40), 'type': teaching_type},
            {'display_name': 'Period 2', 'order': 2, 'start': time(8, 40), 'end': time(9, 20), 'type': teaching_type},
            {'display_name': 'Period 3', 'order': 3, 'start': time(9, 20), 'end': time(10, 0), 'type': teaching_type},
            {'display_name': 'Morning Break', 'order': 4, 'start': time(10, 0), 'end': time(10, 30), 'type': break_type},
            {'display_name': 'Period 4', 'order': 5, 'start': time(10, 30), 'end': time(11, 10), 'type': teaching_type},
            {'display_name': 'Period 5', 'order': 6, 'start': time(11, 10), 'end': time(11, 50), 'type': teaching_type},
            {'display_name': 'Period 6', 'order': 7, 'start': time(11, 50), 'end': time(12, 30), 'type': teaching_type},
            {'display_name': 'Lunch Break', 'order': 8, 'start': time(12, 30), 'end': time(13, 30), 'type': break_type},
            {'display_name': 'Period 7', 'order': 9, 'start': time(13, 30), 'end': time(14, 10), 'type': teaching_type},
            {'display_name': 'Period 8', 'order': 10, 'start': time(14, 10), 'end': time(14, 50), 'type': teaching_type},
        ]
        
        for p_data in periods_data:
            period, created = TimetablePeriod.objects.get_or_create(
                display_name=p_data['display_name'],
                defaults={
                    'order': p_data['order'],
                    'start_time': p_data['start'],
                    'end_time': p_data['end'],
                    'period_type': p_data['type']
                }
            )
            if created:
                self.stdout.write(f'  ✅ Created period: {period.display_name}')
        
        self.stdout.write(self.style.SUCCESS('  ✅ Timetable base data complete'))
    
    def create_staff(self, password):
        from apps.staffs.models import Staff
        from apps.staffs.services.invite import StaffInviteService
        from apps.staffs.constants import StaffType
        
        self.stdout.write('\nCreating staff members...')
        
        staff_data = [
            {'first_name': 'John', 'last_name': 'Principal', 'email': 'principal@school.com', 'staff_type': StaffType.PRINCIPAL, 'department': 'Administration'},
            {'first_name': 'Mary', 'last_name': 'Vice', 'email': 'viceprincipal@school.com', 'staff_type': StaffType.VICE_PRINCIPAL_1, 'department': 'Administration'},
            {'first_name': 'James', 'last_name': 'Bursar', 'email': 'bursar@school.com', 'staff_type': StaffType.BURSAR, 'department': 'Finance'},
            {'first_name': 'Sarah', 'last_name': 'Admissions', 'email': 'admissions@school.com', 'staff_type': StaffType.ADMISSIONS_OFFICER, 'department': 'Admissions'},
            {'first_name': 'Peter', 'last_name': 'Maths', 'email': 'maths@school.com', 'staff_type': StaffType.SUBJECT_TEACHER, 'department': 'Mathematics'},
            {'first_name': 'Grace', 'last_name': 'English', 'email': 'english@school.com', 'staff_type': StaffType.SUBJECT_TEACHER, 'department': 'English'},
            {'first_name': 'David', 'last_name': 'Science', 'email': 'science@school.com', 'staff_type': StaffType.HOD, 'department': 'Science'},
        ]
        
        created_count = 0
        for data in staff_data:
            if not Staff.objects.filter(email=data['email']).exists():
                staff = Staff.objects.create(
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    email=data['email'],
                    phone=f"080{random.randint(10000000, 99999999)}",
                    gender='M' if data['first_name'] in ['John', 'James', 'Peter', 'David'] else 'F',
                    date_of_birth=date(random.randint(1970, 1985), random.randint(1, 12), random.randint(1, 28)),
                    state_of_origin='Lagos',
                    staff_type=data['staff_type'],
                    date_employed=date(random.randint(2010, 2020), 1, 1),
                    emergency_contact_name='Emergency Contact',
                    emergency_contact_phone=f"080{random.randint(10000000, 99999999)}",
                    emergency_contact_relationship='Spouse',
                    department=data.get('department', 'General')
                )
                # Create user account
                staff.create_user_account(password)
                created_count += 1
                # FIXED: Use get_staff_type_display() method instead of attribute
                self.stdout.write(f'  ✅ Created staff: {staff.get_full_name} ({staff.get_staff_type_display()})')
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {created_count} staff members'))
    
    def create_students_and_parents(self, parent_password):
        from apps.students.models import Student, Guardian
        from apps.parents.models import ParentProfile, ChildLink
        from apps.corecode.models import StudentClass, AcademicSession
        from apps.students.services.admission_number import AdmissionNumberService
        from apps.students.constants import GuardianRelationship
        
        self.stdout.write('\nCreating students and parents...')
        
        current_session = AcademicSession.objects.filter(is_current=True).first()
        classes = list(StudentClass.objects.filter(is_active=True))
        
        if not classes:
            self.stdout.write('  ⚠️ No classes found, skipping student creation')
            return
        
        first_names_male = ['Chinedu', 'Olufemi', 'Adebayo', 'Emeka', 'Ibrahim', 'Musa', 'Tunde', 'Segun', 'Femi', 'Kayode']
        first_names_female = ['Funke', 'Adaeze', 'Ngozi', 'Aisha', 'Fatima', 'Bisi', 'Folake', 'Titilayo', 'Chiamaka', 'Zainab']
        last_names = ['Okafor', 'Bello', 'Adeyemi', 'Eze', 'Nwosu', 'Mohammed', 'Yusuf', 'Ibrahim', 'Olawale', 'Okoro']
        
        # Create 30 students
        for i in range(30):
            gender = random.choice(['M', 'F'])
            first_name = random.choice(first_names_male if gender == 'M' else first_names_female)
            last_name = random.choice(last_names)
            student_class = random.choice(classes)
            
            # Calculate age based on class level
            from apps.corecode.constants import EducationLevel
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
                session_code = current_session.code if current_session else str(date.today().year)
                admission_number = AdmissionNumberService.generate_admission_number(
                    class_name=student_class.name,
                    session_code=session_code
                )
            except Exception as e:
                self.stderr.write(self.style.WARNING(f"Admission number generation failed: {e}"))
                admission_number = f"{date.today().year}/{student_class.name}/{i+1:03d}"
            
            # Create student
            student = Student.objects.create(
                admission_number=admission_number,
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                date_of_birth=dob,
                email=f"{first_name.lower()}.{last_name.lower()}@student.com",
                phone=f"080{random.randint(10000000, 99999999)}",
                address=f"{random.randint(1, 50)} School Road",
                city='Lagos',
                state_of_origin=random.choice(['Lagos', 'Oyo', 'Kano', 'Rivers', 'Abuja']),
                current_class=student_class,
                enrollment_date=date.today() - timedelta(days=random.randint(30, 365)),
                enrollment_session=current_session,
                status='active'
            )
            
            # Create guardian (parent)
            guardian_gender = random.choice(['M', 'F'])
            guardian_first = random.choice(first_names_male if guardian_gender == 'M' else first_names_female)
            guardian_last = last_name  # Same last name as student
            guardian_rel = GuardianRelationship.FATHER if guardian_gender == 'M' else GuardianRelationship.MOTHER
            guardian_email = f"{guardian_first.lower()}.{guardian_last.lower()}@parent.com"
            
            guardian = Guardian.objects.create(
                student=student,
                first_name=guardian_first,
                last_name=guardian_last,
                relationship=guardian_rel,
                email=guardian_email,
                phone=f"080{random.randint(10000000, 99999999)}",
                is_primary=True,
                is_emergency_contact=True
            )
            
            # Create parent profile for portal access
            parent, created = ParentProfile.objects.get_or_create(
                email=guardian_email,
                defaults={
                    'first_name': guardian_first,
                    'last_name': guardian_last,
                    'phone': guardian.phone,
                    'guardian_id': guardian.id,
                    'access_status': 'active'
                }
            )
            
            # Create child link
            if created:
                ChildLink.objects.create(
                    parent=parent,
                    student_id=student.id,
                    student_name=student.get_full_name,
                    student_class=student_class.display_name,
                    relationship=guardian_rel,
                    is_primary=True
                )
                
                # Create user account for parent
                from django.contrib.auth import get_user_model
                User = get_user_model()
                username = f"parent_{guardian_first.lower()}"
                if not User.objects.filter(username=username).exists():
                    User.objects.create_user(
                        username=username,
                        email=guardian_email,
                        password=parent_password,
                        first_name=guardian_first,
                        last_name=guardian_last
                    )
            
            if (i + 1) % 10 == 0:
                self.stdout.write(f'  ✅ Created {i + 1} students...')
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {Student.objects.count()} students and {Guardian.objects.count()} guardians'))
    
    def create_admissions_period(self):
        from apps.admissions.models import AdmissionsPeriod
        from apps.corecode.models import AcademicSession
        
        self.stdout.write('\nCreating admissions period...')
        
        current_session = AcademicSession.objects.filter(is_current=True).first()
        if current_session:
            period, created = AdmissionsPeriod.objects.get_or_create(
                name='Regular Admission',
                defaults={
                    'academic_session': current_session,
                    'start_date': timezone.now(),
                    'end_date': timezone.now() + timedelta(days=90),
                    'application_fee': 5000,
                    'is_active': True,
                    'max_applications': 500
                }
            )
            if created:
                self.stdout.write(f'  ✅ Created admissions period: {period.name}')
            else:
                self.stdout.write('  ⏩ Admissions period already exists')
    
    def create_fee_structures(self):
        from apps.finance.models import FeeStructure
        from apps.corecode.models import StudentClass, AcademicSession
        from apps.finance.constants import FeeType, FeeTerm
        
        self.stdout.write('\nCreating fee structures...')
        
        current_session = AcademicSession.objects.filter(is_current=True).first()
        if not current_session:
            self.stdout.write('  ⚠️ No current session, skipping fee structures')
            return
        
        classes = StudentClass.objects.filter(is_active=True)
        
        fee_configs = [
            (FeeType.TUITION, FeeTerm.PER_TERM, 1.0, 'Tuition fee per term'),
            (FeeType.DEVELOPMENT, FeeTerm.PER_SESSION, 0.2, 'Development levy'),
            (FeeType.LIBRARY, FeeTerm.PER_TERM, 0.05, 'Library fee'),
            (FeeType.SPORTS, FeeTerm.PER_TERM, 0.03, 'Sports fee'),
            (FeeType.ICT, FeeTerm.PER_TERM, 0.04, 'ICT fee'),
        ]
        
        base_amounts = {
            'nursery': 50000,
            'primary': 75000,
            'jss': 100000,
            'sss': 125000,
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
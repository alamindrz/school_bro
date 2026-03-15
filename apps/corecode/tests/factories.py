"""
Complete Student Views Test Suite
DEPENDS ON: students/views/staff.py, students/forms.py, corecode/tests/factories.py
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.utils import timezone
from datetime import date, timedelta
import json
import io
import csv

from apps.corecode.tests.factories import (
    UserFactory, AcademicSessionFactory, StudentClassFactory,
    create_current_academic_session, create_complete_school_setup
)
from apps.students.models import Student, Guardian, StudentHistory
from apps.students.constants import StudentStatus, StudentCreationMethod
from apps.students.tests.factories import (
    StudentFactory, GuardianFactory, StudentHistoryFactory
)
from apps.students.services.user_integration import StudentUserService
from apps.corecode.models import SystemLog

User = get_user_model()


class StudentViewTestBase(TestCase):
    """Base class for all student view tests"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data once for all tests"""
        # Create complete school setup
        cls.school_setup = create_complete_school_setup()
        cls.admin_user = cls.school_setup['admin_user']
        cls.session = cls.school_setup['session']
        cls.terms = cls.school_setup['terms']
        
        # Get or create classes
        from apps.corecode.models import StudentClass
        cls.ss1_class, _ = StudentClass.objects.get_or_create(
            name='SS1',
            defaults={
                'display_name': 'SS 1',
                'education_level': 'sss',
                'max_students': 45,
                'sort_order': 13,
                'is_active': True
            }
        )
        cls.ss2_class, _ = StudentClass.objects.get_or_create(
            name='SS2',
            defaults={
                'display_name': 'SS 2',
                'education_level': 'sss',
                'max_students': 45,
                'sort_order': 14,
                'is_active': True
            }
        )
        
        # Create test student
        cls.student = StudentFactory(
            current_class=cls.ss1_class,
            enrollment_session=cls.session,
            created_by=cls.admin_user
        )
    
    def setUp(self):
        """Set up before each test"""
        # Create staff user with permissions
        self.staff_user = UserFactory(username='staffuser')
        self.staff_user.set_password('testpass123')
        self.staff_user.save()
        
        # Add all student permissions
        content_type = ContentType.objects.get_for_model(Student)
        permissions = Permission.objects.filter(content_type=content_type)
        self.staff_user.user_permissions.add(*permissions)
        
        # Add guardian permissions
        guardian_ct = ContentType.objects.get_for_model(Guardian)
        guardian_perms = Permission.objects.filter(content_type=guardian_ct)
        self.staff_user.user_permissions.add(*guardian_perms)
        
        # Login
        self.client = Client()
        self.client.login(username='staffuser', password='testpass123')


class StudentListViewTest(StudentViewTestBase):
    """Test StudentListView - COMPLETE"""
    
    def test_view_url_exists(self):
        """Test URL resolves correctly"""
        response = self.client.get(reverse('students:list'))
        self.assertEqual(response.status_code, 200)
    
    def test_view_uses_correct_template(self):
        """Test correct template is used"""
        response = self.client.get(reverse('students:list'))
        self.assertTemplateUsed(response, 'students/pages/student_list.html')
    
    def test_pagination(self):
        """Test pagination works correctly"""
        # Create 30 students
        students = StudentFactory.create_batch(30)
        
        response = self.client.get(reverse('students:list'))
        self.assertEqual(len(response.context['students']), 25)  # Default paginate_by
        self.assertEqual(response.context['total_count'], 31)  # Including cls.student
        
        response = self.client.get(reverse('students:list') + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['students']), 6)  # Remaining 6
    
    def test_search_by_name(self):
        """Test search by student name"""
        student = StudentFactory(
            first_name='UniqueSearchName',
            last_name='UniqueLastName'
        )
        
        response = self.client.get(reverse('students:list'), {'q': 'UniqueSearchName'})
        self.assertContains(response, student.admission_number)
        
        response = self.client.get(reverse('students:list'), {'q': 'UniqueLastName'})
        self.assertContains(response, student.admission_number)
    
    def test_search_by_admission_number(self):
        """Test search by admission number"""
        student = StudentFactory(admission_number='2024/SS1/999')
        
        response = self.client.get(reverse('students:list'), {'q': '2024/SS1/999'})
        self.assertContains(response, student.admission_number)
    
    def test_filter_by_class(self):
        """Test filtering by class"""
        other_class = StudentClassFactory(name='JSS1', display_name='JSS 1')
        student1 = StudentFactory(current_class=self.ss1_class)
        student2 = StudentFactory(current_class=other_class)
        
        response = self.client.get(
            reverse('students:list'),
            {'class_id': self.ss1_class.id}
        )
        
        self.assertContains(response, student1.admission_number)
        self.assertNotContains(response, student2.admission_number)
    
    def test_filter_by_status(self):
        """Test filtering by status"""
        active_student = StudentFactory(status=StudentStatus.ACTIVE)
        graduated_student = StudentFactory(status=StudentStatus.GRADUATED)
        
        response = self.client.get(
            reverse('students:list'),
            {'status': StudentStatus.GRADUATED}
        )
        
        self.assertContains(response, graduated_student.admission_number)
        self.assertNotContains(response, active_student.admission_number)
    
    def test_filter_by_gender(self):
        """Test filtering by gender"""
        male_student = StudentFactory(gender='M')
        female_student = StudentFactory(gender='F')
        
        response = self.client.get(reverse('students:list'), {'gender': 'M'})
        self.assertContains(response, male_student.admission_number)
        self.assertNotContains(response, female_student.admission_number)
    
    def test_filter_by_session(self):
        """Test filtering by enrollment session"""
        other_session = AcademicSessionFactory(name='2023/2024', code='202324')
        student1 = StudentFactory(enrollment_session=self.session)
        student2 = StudentFactory(enrollment_session=other_session)
        
        response = self.client.get(
            reverse('students:list'),
            {'session_id': self.session.id}
        )
        
        self.assertContains(response, student1.admission_number)
        self.assertNotContains(response, student2.admission_number)
    
    def test_combined_filters(self):
        """Test multiple filters working together"""
        # Student that should appear
        student = StudentFactory(
            first_name='Target',
            current_class=self.ss1_class,
            status=StudentStatus.ACTIVE,
            gender='M',
            enrollment_session=self.session
        )
        
        # Student that should NOT appear (wrong class)
        StudentFactory(
            first_name='Target',
            current_class=self.ss2_class,
            status=StudentStatus.ACTIVE,
            gender='M'
        )
        
        response = self.client.get(reverse('students:list'), {
            'q': 'Target',
            'class_id': self.ss1_class.id,
            'status': StudentStatus.ACTIVE,
            'gender': 'M',
            'session_id': self.session.id
        })
        
        self.assertContains(response, student.admission_number)
        self.assertEqual(len(response.context['students']), 1)
    
    def test_permission_required(self):
        """Test permission requirement"""
        # Create user without permissions
        user_no_perm = UserFactory(username='noperm')
        user_no_perm.set_password('testpass123')
        user_no_perm.save()
        
        client = Client()
        client.login(username='noperm', password='testpass123')
        
        response = client.get(reverse('students:list'))
        self.assertEqual(response.status_code, 403)
    
    def test_empty_search(self):
        """Test empty search returns all students"""
        response = self.client.get(reverse('students:list'), {'q': ''})
        self.assertEqual(response.status_code, 200)
        self.assertTrue('students' in response.context)


class StudentCreateViewTest(StudentViewTestBase):
    """Test StudentCreateView - COMPLETE"""
    
    def test_view_url_exists(self):
        """Test URL resolves correctly"""
        response = self.client.get(reverse('students:create'))
        self.assertEqual(response.status_code, 200)
    
    def test_view_uses_correct_template(self):
        """Test correct template is used"""
        response = self.client.get(reverse('students:create'))
        self.assertTemplateUsed(response, 'students/pages/student_form.html')
    
    def test_create_student_minimal_data(self):
        """Test creating student with minimal required data"""
        form_data = {
            'first_name': 'Minimal',
            'last_name': 'Student',
            'gender': 'M',
            'date_of_birth': (date.today() - timedelta(days=15*365)).isoformat(),
            'email': 'minimal@school.edu',
            'confirm_email': 'minimal@school.edu',
            'phone': '08012345678',
            'current_class': self.ss1_class.id,
            'create_user_account': False,
        }
        
        response = self.client.post(reverse('students:create'), form_data)
        
        # Should redirect to list
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('students:list'))
        
        # Check student was created
        student = Student.objects.get(email='minimal@school.edu')
        self.assertIsNotNone(student.admission_number)
        self.assertEqual(student.created_via, StudentCreationMethod.MANUAL)
        self.assertEqual(student.created_by, self.staff_user)
        
        # Check success message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn('created successfully', str(messages[0]))
    
    def test_create_student_with_user_account(self):
        """Test creating student with automatic user account creation"""
        form_data = {
            'first_name': 'Portal',
            'last_name': 'User',
            'gender': 'F',
            'date_of_birth': (date.today() - timedelta(days=15*365)).isoformat(),
            'email': 'portal.user@school.edu',
            'confirm_email': 'portal.user@school.edu',
            'phone': '08123456789',
            'current_class': self.ss1_class.id,
            'create_user_account': True,
            'send_welcome_email': True,
        }
        
        response = self.client.post(reverse('students:create'), form_data)
        
        self.assertEqual(response.status_code, 302)
        
        # Check student and user account
        student = Student.objects.get(email='portal.user@school.edu')
        self.assertIsNotNone(student.user)
        
        # Check welcome email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Welcome', mail.outbox[0].subject)
        self.assertIn(student.email, mail.outbox[0].to)
    
    def test_create_student_no_active_session(self):
        """Test student creation fails with no active session"""
        # Set no current session
        AcademicSession.objects.update(is_current=False)
        
        form_data = {
            'first_name': 'No',
            'last_name': 'Session',
            'gender': 'M',
            'date_of_birth': (date.today() - timedelta(days=15*365)).isoformat(),
            'email': 'no.session@school.edu',
            'confirm_email': 'no.session@school.edu',
            'phone': '08012345678',
            'current_class': self.ss1_class.id,
        }
        
        response = self.client.post(reverse('students:create'), form_data)
        
        # Form should be invalid
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No active academic session')
    
    def test_create_student_duplicate_email(self):
        """Test duplicate email validation"""
        # Create existing student
        StudentFactory(email='existing@school.edu')
        
        form_data = {
            'first_name': 'Duplicate',
            'last_name': 'Email',
            'gender': 'M',
            'date_of_birth': (date.today() - timedelta(days=15*365)).isoformat(),
            'email': 'existing@school.edu',
            'confirm_email': 'existing@school.edu',
            'phone': '08012345678',
            'current_class': self.ss1_class.id,
        }
        
        response = self.client.post(reverse('students:create'), form_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
    
    def test_create_student_invalid_age(self):
        """Test age validation"""
        form_data = {
            'first_name': 'Too',
            'last_name': 'Young',
            'gender': 'M',
            'date_of_birth': (date.today() - timedelta(days=1*365)).isoformat(),  # 1 year old
            'email': 'too.young@school.edu',
            'confirm_email': 'too.young@school.edu',
            'phone': '08012345678',
            'current_class': self.ss1_class.id,
        }
        
        response = self.client.post(reverse('students:create'), form_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'at least 2 years')
    
    def test_create_student_audit_log(self):
        """Test audit log is created"""
        form_data = {
            'first_name': 'Audit',
            'last_name': 'Log',
            'gender': 'M',
            'date_of_birth': (date.today() - timedelta(days=15*365)).isoformat(),
            'email': 'audit.log@school.edu',
            'confirm_email': 'audit.log@school.edu',
            'phone': '08012345678',
            'current_class': self.ss1_class.id,
        }
        
        self.client.post(reverse('students:create'), form_data)
        
        student = Student.objects.get(email='audit.log@school.edu')
        
        # Check system log
        log = SystemLog.objects.filter(
            app_label=SystemLog.AppLabel.STUDENTS,
            model_name='Student',
            object_id=str(student.id)
        ).first()
        
        self.assertIsNotNone(log)
        self.assertEqual(log.action, SystemLog.ActionType.CREATE)
        self.assertEqual(log.user, self.staff_user)


class StudentUpdateViewTest(StudentViewTestBase):
    """Test StudentUpdateView - COMPLETE"""
    
    def test_view_url_exists(self):
        """Test URL resolves correctly"""
        response = self.client.get(
            reverse('students:edit', kwargs={'pk': self.student.pk})
        )
        self.assertEqual(response.status_code, 200)
    
    def test_update_student_success(self):
        """Test successful student update"""
        form_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'middle_name': 'Middle',
            'email': self.student.email,  # Keep same email
            'confirm_email': self.student.email,
            'phone': '09012345678',  # New phone
            'address': '456 New Address',
            'city': 'Abuja',
            'state_of_origin': 'FCT',
            'blood_group': 'A+',
            'medical_notes': 'Updated medical notes',
            'has_special_needs': False,
            'current_class': self.student.current_class.id,
            'date_of_birth': self.student.date_of_birth.isoformat(),
            'gender': self.student.gender,
        }
        
        response = self.client.post(
            reverse('students:edit', kwargs={'pk': self.student.pk}),
            form_data
        )
        
        # Should redirect to detail
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse('students:detail', kwargs={'pk': self.student.pk})
        )
        
        # Check student was updated
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, 'Updated')
        self.assertEqual(self.student.phone, '09012345678')
        self.assertEqual(self.student.city, 'Abuja')
        
        # Check audit log
        log = SystemLog.objects.filter(
            app_label=SystemLog.AppLabel.STUDENTS,
            model_name='Student',
            object_id=str(self.student.id),
            action=SystemLog.ActionType.UPDATE
        ).order_by('-timestamp').first()
        
        self.assertIsNotNone(log)
        self.assertIn('phone', log.changes.get('changed_fields', []))
    
    def test_update_student_cannot_change_admission_number(self):
        """Test admission number is read-only"""
        form_data = {
            'first_name': self.student.first_name,
            'last_name': self.student.last_name,
            'gender': self.student.gender,
            'date_of_birth': self.student.date_of_birth.isoformat(),
            'email': self.student.email,
            'confirm_email': self.student.email,
            'phone': self.student.phone,
            'current_class': self.student.current_class.id,
            'admission_number': '9999/SS1/999',  # Attempt to change
        }
        
        response = self.client.post(
            reverse('students:edit', kwargs={'pk': self.student.pk}),
            form_data
        )
        
        self.student.refresh_from_db()
        self.assertNotEqual(self.student.admission_number, '9999/SS1/999')
    
    def test_update_student_404(self):
        """Test 404 for non-existent student"""
        response = self.client.get(
            reverse('students:edit', kwargs={'pk': 99999})
        )
        self.assertEqual(response.status_code, 404)


class StudentDetailViewTest(StudentViewTestBase):
    """Test StudentDetailView - COMPLETE"""
    
    def test_view_url_exists(self):
        """Test URL resolves correctly"""
        response = self.client.get(
            reverse('students:detail', kwargs={'pk': self.student.pk})
        )
        self.assertEqual(response.status_code, 200)
    
    def test_view_displays_all_student_info(self):
        """Test all student information is displayed"""
        response = self.client.get(
            reverse('students:detail', kwargs={'pk': self.student.pk})
        )
        
        self.assertContains(response, self.student.get_full_name)
        self.assertContains(response, self.student.admission_number)
        self.assertContains(response, self.student.current_class.display_name)
        self.assertContains(response, self.student.email or '')
        self.assertContains(response, self.student.phone or '')
        self.assertContains(response, self.student.get_status_display())
    
    def test_view_displays_guardians(self):
        """Test guardians are displayed"""
        guardian = GuardianFactory(student=self.student)
        
        response = self.client.get(
            reverse('students:detail', kwargs={'pk': self.student.pk})
        )
        
        self.assertContains(response, guardian.get_full_name)
        self.assertContains(response, guardian.get_relationship_display())
        self.assertContains(response, guardian.phone)
    
    def test_view_displays_timeline(self):
        """Test student history timeline is displayed"""
        # Create history entries
        history1 = StudentHistoryFactory(
            student=self.student,
            action='ENROLLED',
            performed_by=self.admin_user
        )
        history2 = StudentHistoryFactory(
            student=self.student,
            action='PROMOTED',
            performed_by=self.admin_user
        )
        
        response = self.client.get(
            reverse('students:detail', kwargs={'pk': self.student.pk})
        )
        
        self.assertContains(response, 'ENROLLED')
        self.assertContains(response, 'PROMOTED')
        self.assertContains(response, self.admin_user.get_full_name() or 'admin')
    
    def test_view_has_status_update_button(self):
        """Test status update button appears"""
        response = self.client.get(
            reverse('students:detail', kwargs={'pk': self.student.pk})
        )
        
        self.assertContains(response, 'Change Status')
        self.assertContains(
            response,
            reverse('students:status_update', kwargs={'pk': self.student.pk})
        )
    
    def test_view_has_add_guardian_button(self):
        """Test add guardian button appears"""
        response = self.client.get(
            reverse('students:detail', kwargs={'pk': self.student.pk})
        )
        
        self.assertContains(response, 'Add Guardian')
        self.assertContains(
            response,
            reverse('students:guardian_create', kwargs={'student_id': self.student.pk})
        )
    
    def test_view_404_invalid_id(self):
        """Test 404 for invalid student ID"""
        response = self.client.get(
            reverse('students:detail', kwargs={'pk': 99999})
        )
        self.assertEqual(response.status_code, 404)


class StudentStatusUpdateViewTest(StudentViewTestBase):
    """Test StudentStatusUpdateView - COMPLETE"""
    
    def test_view_url_exists(self):
        """Test URL resolves correctly"""
        response = self.client.get(
            reverse('students:status_update', kwargs={'pk': self.student.pk})
        )
        self.assertEqual(response.status_code, 200)
    
    def test_update_status_success(self):
        """Test successful status update"""
        form_data = {
            'status': StudentStatus.GRADUATED,
            'reason': 'Completed secondary education successfully',
            'notify_guardian': False,
        }
        
        response = self.client.post(
            reverse('students:status_update', kwargs={'pk': self.student.pk}),
            form_data
        )
        
        # Should redirect to detail
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse('students:detail', kwargs={'pk': self.student.pk})
        )
        
        # Check status updated
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, StudentStatus.GRADUATED)
        
        # Check history created
        history = StudentHistory.objects.filter(
            student=self.student,
            action__contains='STATUS_CHANGE'
        ).first()
        
        self.assertIsNotNone(history)
        self.assertIn('Completed secondary education', history.notes)
        self.assertEqual(history.performed_by, self.staff_user)
    
    def test_update_status_invalid_transition(self):
        """Test invalid status transition"""
        # First graduate
        self.student.status = StudentStatus.GRADUATED
        self.student.save()
        
        form_data = {
            'status': StudentStatus.ACTIVE,  # Invalid - terminal state
            'reason': 'Try to reactivate',
        }
        
        response = self.client.post(
            reverse('students:status_update', kwargs={'pk': self.student.pk}),
            form_data
        )
        
        self.assertEqual(response.status_code, 200)  # Form re-displayed
        self.assertContains(response, 'Cannot transition')
        
        # Status should not change
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, StudentStatus.GRADUATED)
    
    def test_update_status_same_status(self):
        """Test updating to same status (should be valid)"""
        form_data = {
            'status': StudentStatus.ACTIVE,
            'reason': 'Still active',
        }
        
        response = self.client.post(
            reverse('students:status_update', kwargs={'pk': self.student.pk}),
            form_data
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Status should remain active
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, StudentStatus.ACTIVE)
    
    def test_update_status_notify_guardian(self):
        """Test guardian notification on status change"""
        # Add guardian with email
        GuardianFactory(student=self.student, email='parent@family.com')
        
        form_data = {
            'status': StudentStatus.SUSPENDED,
            'reason': 'Academic probation',
            'notify_guardian': True,
        }
        
        response = self.client.post(
            reverse('students:status_update', kwargs={'pk': self.student.pk}),
            form_data
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Status Update', mail.outbox[0].subject)
        self.assertIn('parent@family.com', mail.outbox[0].to)


class GuardianCreateViewTest(StudentViewTestBase):
    """Test GuardianCreateView - COMPLETE"""
    
    def test_view_url_exists(self):
        """Test URL resolves correctly"""
        response = self.client.get(
            reverse('students:guardian_create', kwargs={'student_id': self.student.pk})
        )
        self.assertEqual(response.status_code, 200)
    
    def test_add_guardian_success(self):
        """Test successful guardian addition"""
        form_data = {
            'first_name': 'Test',
            'last_name': 'Guardian',
            'relationship': 'father',
            'email': 'test.guardian@family.com',
            'phone': '08012345678',
            'alternate_phone': '08123456789',
            'address': '123 Guardian Street',
            'occupation': 'Engineer',
            'employer': 'Tech Corp',
            'is_primary': True,
            'is_emergency_contact': True,
        }
        
        response = self.client.post(
            reverse('students:guardian_create', kwargs={'student_id': self.student.pk}),
            form_data
        )
        
        # Should redirect to student detail
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse('students:detail', kwargs={'pk': self.student.pk})
        )
        
        # Check guardian created
        guardian = Guardian.objects.get(email='test.guardian@family.com')
        self.assertEqual(guardian.student, self.student)
        self.assertTrue(guardian.is_primary)
        
        # Check success message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn('added successfully', str(messages[0]))
    
    def test_add_guardian_with_portal_account(self):
        """Test adding guardian with portal account creation"""
        form_data = {
            'first_name': 'Portal',
            'last_name': 'Parent',
            'relationship': 'mother',
            'email': 'portal.parent@family.com',
            'phone': '08012345678',
            'is_primary': True,
            'create_portal_account': True,
        }
        
        response = self.client.post(
            reverse('students:guardian_create', kwargs={'student_id': self.student.pk}),
            form_data
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Check portal account was created
        guardian = Guardian.objects.get(email='portal.parent@family.com')
        
        # Verify user account exists
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(email=guardian.email).first()
        self.assertIsNotNone(user)
        
        # Check welcome email
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Parent Portal Access', mail.outbox[0].subject)
    
    def test_add_guardian_limit_exceeded(self):
        """Test guardian limit validation"""
        # Add 5 guardians (max)
        for i in range(5):
            GuardianFactory(student=self.student)
        
        form_data = {
            'first_name': 'Extra',
            'last_name': 'Guardian',
            'relationship': 'guardian',
            'email': 'extra@family.com',
            'phone': '08012345678',
            'is_primary': False,
        }
        
        response = self.client.post(
            reverse('students:guardian_create', kwargs={'student_id': self.student.pk}),
            form_data
        )
        
        self.assertEqual(response.status_code, 200)  # Form re-displayed
        self.assertContains(response, 'Maximum 5 guardians allowed')
    
    def test_add_primary_guardian_limit(self):
        """Test primary guardian limit validation"""
        # Add 2 primary guardians (max)
        GuardianFactory(student=self.student, is_primary=True)
        GuardianFactory(student=self.student, is_primary=True)
        
        form_data = {
            'first_name': 'Extra',
            'last_name': 'Primary',
            'relationship': 'father',
            'email': 'extra.primary@family.com',
            'phone': '08012345678',
            'is_primary': True,  # Would be 3rd primary
        }
        
        response = self.client.post(
            reverse('students:guardian_create', kwargs={'student_id': self.student.pk}),
            form_data
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Maximum 2 primary guardians allowed')
    
    def test_add_guardian_404_invalid_student(self):
        """Test 404 for invalid student ID"""
        response = self.client.get(
            reverse('students:guardian_create', kwargs={'student_id': 99999})
        )
        self.assertEqual(response.status_code, 404)


class StudentGenerateUserViewTest(StudentViewTestBase):
    """Test StudentGenerateUserView"""
    
    def test_generate_user_account_success(self):
        """Test generating user account for existing student"""
        student = StudentFactory(
            email='generate.user@school.edu',
            user=None
        )
        
        response = self.client.post(
            reverse('students:generate_user', kwargs={'pk': student.pk})
        )
        
        # Should redirect to detail
        self.assertEqual(response.status_code, 302)
        
        # Check user was created
        student.refresh_from_db()
        self.assertIsNotNone(student.user)
        self.assertEqual(student.user.email, student.email)
        
        # Check welcome email
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Welcome', mail.outbox[0].subject)
    
    def test_generate_user_already_exists(self):
        """Test generating user for student that already has user"""
        # Student already has user (from factory)
        response = self.client.post(
            reverse('students:generate_user', kwargs={'pk': self.student.pk})
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Should show error message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn('already has user', str(messages[0]).lower())
    
    def test_generate_user_no_email(self):
        """Test generating user for student without email"""
        student = StudentFactory(email='', user=None)
        
        response = self.client.post(
            reverse('students:generate_user', kwargs={'pk': student.pk})
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Should show error message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn('email address required', str(messages[0]).lower())
    
    def test_require_post_only(self):
        """Test view only accepts POST requests"""
        response = self.client.get(
            reverse('students:generate_user', kwargs={'pk': self.student.pk})
        )
        self.assertEqual(response.status_code, 405)  # Method not allowed


class StudentAjaxViewTest(StudentViewTestBase):
    """Test StudentAjaxView - AJAX endpoints"""
    
    def test_search_students_ajax(self):
        """Test AJAX student search"""
        student = StudentFactory(
            first_name='AjaxSearch',
            admission_number='2024/AJAX/001'
        )
        
        response = self.client.get(
            reverse('students:ajax'),
            {'action': 'search', 'q': 'AjaxSearch'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('students', data)
        self.assertTrue(len(data['students']) > 0)
        
        # Find our student
        found = any(s['admission_number'] == student.admission_number for s in data['students'])
        self.assertTrue(found)
    
    def test_class_students_ajax(self):
        """Test AJAX class students listing"""
        # Create students in class
        students = StudentFactory.create_batch(3, current_class=self.ss1_class)
        
        response = self.client.get(
            reverse('students:ajax'),
            {'action': 'class_students', 'class_id': self.ss1_class.id}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('students', data)
        self.assertEqual(len(data['students']), 3)
    
    def test_student_counts_ajax(self):
        """Test AJAX student counts by class"""
        # Create some students in different classes
        StudentFactory.create_batch(2, current_class=self.ss1_class)
        StudentFactory.create_batch(3, current_class=self.ss2_class)
        
        response = self.client.get(
            reverse('students:ajax'),
            {'action': 'counts'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('class_counts', data)
        
        # Find our classes in counts
        ss1_count = next(
            (c['student_count'] for c in data['class_counts'] 
             if c['class_id'] == self.ss1_class.id),
            0
        )
        self.assertEqual(ss1_count, 2)
    
    def test_ajax_invalid_action(self):
        """Test AJAX with invalid action"""
        response = self.client.get(
            reverse('students:ajax'),
            {'action': 'invalid_action'}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_ajax_permission_required(self):
        """Test AJAX endpoint requires permission"""
        # Create user without permission
        user_no_perm = UserFactory(username='ajaxnoperm')
        user_no_perm.set_password('testpass123')
        user_no_perm.save()
        
        client = Client()
        client.login(username='ajaxnoperm', password='testpass123')
        
        response = client.get(
            reverse('students:ajax'),
            {'action': 'search', 'q': 'test'}
        )
        
        self.assertEqual(response.status_code, 403)


class StudentBulkImportViewTest(StudentViewTestBase):
    """Test StudentBulkImportView"""
    
    def setUp(self):
        super().setUp()
        
        # Ensure classes exist
        from apps.corecode.models import StudentClass
        StudentClass.objects.get_or_create(
            name='SS1',
            defaults={
                'display_name': 'SS 1',
                'education_level': 'sss',
                'max_students': 45,
                'sort_order': 13,
                'is_active': True
            }
        )
    
    def test_bulk_import_valid_csv(self):
        """Test bulk import with valid CSV"""
        # Create CSV content
        csv_content = io.StringIO()
        writer = csv.writer(csv_content)
        writer.writerow(['first_name', 'last_name', 'date_of_birth', 'gender', 'current_class', 'email', 'phone'])
        writer.writerow(['Bulk1', 'Import1', '2008-01-15', 'M', 'SS1', 'bulk1@school.edu', '08012345678'])
        writer.writerow(['Bulk2', 'Import2', '2008-02-20', 'F', 'SS1', 'bulk2@school.edu', '08123456789'])
        
        csv_file = SimpleUploadedFile(
            "bulk_import.csv",
            csv_content.getvalue().encode('utf-8'),
            content_type="text/csv"
        )
        
        form_data = {
            'create_user_accounts': False,
            'send_welcome_emails': False,
        }
        
        response = self.client.post(
            reverse('students:bulk_import'),
            {**form_data, 'csv_file': csv_file}
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Check students were created
        self.assertTrue(Student.objects.filter(email='bulk1@school.edu').exists())
        self.assertTrue(Student.objects.filter(email='bulk2@school.edu').exists())
        
        # Check success message
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('Successfully imported' in str(m) for m in messages))
    
    def test_bulk_import_with_user_accounts(self):
        """Test bulk import with user account creation"""
        csv_content = io.StringIO()
        writer = csv.writer(csv_content)
        writer.writerow(['first_name', 'last_name', 'date_of_birth', 'gender', 'current_class', 'email', 'phone'])
        writer.writerow(['User1', 'Account1', '2008-01-15', 'M', 'SS1', 'user1@school.edu', '08012345678'])
        
        csv_file = SimpleUploadedFile(
            "bulk_with_users.csv",
            csv_content.getvalue().encode('utf-8'),
            content_type="text/csv"
        )
        
        form_data = {
            'create_user_accounts': True,
            'send_welcome_emails': False,
        }
        
        response = self.client.post(
            reverse('students:bulk_import'),
            {**form_data, 'csv_file': csv_file}
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Check user account was created
        student = Student.objects.get(email='user1@school.edu')
        self.assertIsNotNone(student.user)
    
    def test_bulk_import_invalid_csv_missing_columns(self):
        """Test bulk import with missing required columns"""
        csv_content = io.StringIO()
        writer = csv.writer(csv_content)
        writer.writerow(['first_name', 'last_name'])  # Missing required columns
        
        csv_file = SimpleUploadedFile(
            "invalid.csv",
            csv_content.getvalue().encode('utf-8'),
            content_type="text/csv"
        )
        
        response = self.client.post(
            reverse('students:bulk_import'),
            {'csv_file': csv_file}
        )
        
        self.assertEqual(response.status_code, 200)  # Form re-displayed
        self.assertContains(response, 'Missing required columns')
    
    def test_bulk_import_invalid_file_type(self):
        """Test bulk import with non-CSV file"""
        txt_file = SimpleUploadedFile(
            "students.txt",
            b"not a csv",
            content_type="text/plain"
        )
        
        response = self.client.post(
            reverse('students:bulk_import'),
            {'csv_file': txt_file}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CSV format')
    
    
    def test_bulk_import_partial_failures(self):
        """Test bulk import with some invalid rows"""
        csv_content = io.StringIO()
        writer = csv.writer(csv_content)
        writer.writerow(['first_name', 'last_name', 'date_of_birth', 'gender', 'current_class', 'email', 'phone'])
        writer.writerow(['Valid', 'Student', '2008-01-15', 'M', 'SS1', 'valid@school.edu', '08012345678'])
        writer.writerow(['Invalid', 'Student', 'invalid-date', 'M', 'SS1', 'invalid@school.edu', '08012345678'])  # Invalid date
        
        csv_file = SimpleUploadedFile(
            "partial_fail.csv",
            csv_content.getvalue().encode('utf-8'),
            content_type="text/csv"
        )
        
        response = self.client.post(
            reverse('students:bulk_import'),
            {'csv_file': csv_file}
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Valid student should be created
        self.assertTrue(Student.objects.filter(email='valid@school.edu').exists())
        # Invalid student should not be created
        self.assertFalse(Student.objects.filter(email='invalid@school.edu').exists())
        
        # Should show warning with error count
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('errors' in str(m).lower() for m in messages))
    
    def test_bulk_import_permission_required(self):
        """Test bulk import requires specific permission"""
        # Remove bulk import permission
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename='bulk_import_students')
        self.staff_user.user_permissions.remove(perm)
        
        csv_content = io.StringIO()
        writer = csv.writer(csv_content)
        writer.writerow(['first_name', 'last_name', 'date_of_birth', 'gender', 'current_class', 'email', 'phone'])
        writer.writerow(['Test', 'Student', '2008-01-15', 'M', 'SS1', 'test@school.edu', '08012345678'])
        
        csv_file = SimpleUploadedFile(
            "test.csv",
            csv_content.getvalue().encode('utf-8'),
            content_type="text/csv"
        )
        
        response = self.client.post(
            reverse('students:bulk_import'),
            {'csv_file': csv_file}
        )
        
        self.assertEqual(response.status_code, 403)


class StudentPromotionViewTest(StudentViewTestBase):
    """Test StudentPromotionView"""
    
    def setUp(self):
        super().setUp()
        
        # Create students eligible for promotion
        self.students = StudentFactory.create_batch(
            5,
            current_class=self.ss1_class,
            enrollment_session=self.session,
            status=StudentStatus.ACTIVE
        )
        
        # Ensure SS2 class exists
        from apps.corecode.models import StudentClass
        self.ss2_class, _ = StudentClass.objects.get_or_create(
            name='SS2',
            defaults={
                'display_name': 'SS 2',
                'education_level': 'sss',
                'max_students': 45,
                'sort_order': 14,
                'is_active': True
            }
        )
    
    def test_promotion_view_get(self):
        """Test promotion view GET request"""
        response = self.client.get(reverse('students:promotion'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'students/pages/promotion.html')
        self.assertIn('classes', response.context)
        self.assertIn('current_session', response.context)
    
    def test_promote_students_success(self):
        """Test successful student promotion"""
        student_ids = [str(s.id) for s in self.students[:3]]
        
        response = self.client.post(
            reverse('students:promotion'),
            {
                'from_class': self.ss1_class.id,
                'to_class': self.ss2_class.id,
                'students': student_ids
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Check students were promoted
        for student in self.students[:3]:
            student.refresh_from_db()
            self.assertEqual(student.current_class, self.ss2_class)
        
        # Check unpromoted students remain
        for student in self.students[3:]:
            student.refresh_from_db()
            self.assertEqual(student.current_class, self.ss1_class)
        
        # Check success message
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('Successfully promoted' in str(m) for m in messages))
    
    def test_promote_no_students_selected(self):
        """Test promotion with no students selected"""
        response = self.client.post(
            reverse('students:promotion'),
            {
                'from_class': self.ss1_class.id,
                'to_class': self.ss2_class.id,
                'students': []
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Check error message
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('No students selected' in str(m) for m in messages))
        
        # No students should be promoted
        for student in self.students:
            student.refresh_from_db()
            self.assertEqual(student.current_class, self.ss1_class)
    
    def test_promote_invalid_to_class(self):
        """Test promotion to non-existent class"""
        student_ids = [str(s.id) for s in self.students[:1]]
        
        response = self.client.post(
            reverse('students:promotion'),
            {
                'from_class': self.ss1_class.id,
                'to_class': 99999,  # Invalid class ID
                'students': student_ids
            }
        )
        
        self.assertEqual(response.status_code, 200)  # Should show error
        self.assertContains(response, 'not found')
    
    def test_promote_ineligible_student(self):
        """Test promotion of ineligible student (not active)"""
        # Create suspended student
        suspended_student = StudentFactory(
            current_class=self.ss1_class,
            status=StudentStatus.SUSPENDED
        )
        
        response = self.client.post(
            reverse('students:promotion'),
            {
                'from_class': self.ss1_class.id,
                'to_class': self.ss2_class.id,
                'students': [str(suspended_student.id)]
            }
        )
        
        # Should still redirect but might have partial success
        self.assertEqual(response.status_code, 302)
        
        # Student should not be promoted
        suspended_student.refresh_from_db()
        self.assertEqual(suspended_student.current_class, self.ss1_class)
    
    def test_promotion_permission_required(self):
        """Test promotion requires specific permission"""
        # Remove promotion permission
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename='promote_student')
        self.staff_user.user_permissions.remove(perm)
        
        response = self.client.get(reverse('students:promotion'))
        self.assertEqual(response.status_code, 403)
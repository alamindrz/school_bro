"""
Staffs Selectors - READ Layer
Returns dicts, never model instances
ALL read operations go through this layer
"""

from django.db.models import Q, Count, Avg, Sum, Prefetch
from django.utils import timezone
from typing import Optional, List, Dict, Any, Tuple
from datetime import date, timedelta, datetime

from .models import (
    Staff, SubjectAssignment, DutyAssignment, LeaveRequest,
    StaffAttendance, Qualification, WorkExperience, PerformanceEvaluation,
    StaffDocument
)
from .constants import StaffType, StaffCategory, EmploymentStatus, LeaveStatus, DutyPost

from apps.corecode.selectors import (
    AcademicSessionSelector,
    AcademicTermSelector,
    StudentClassSelector
)


class StaffSelector:
    """
    All staff read operations.
    SINGLE SOURCE OF TRUTH for staff data retrieval.
    Returns dictionaries, NEVER model instances.
    """

    @staticmethod
    def get_by_id(staff_id: int) -> Optional[Dict[str, Any]]:
        """
        Get staff member by ID.
        
        Args:
            staff_id: Primary key of staff member
            
        Returns:
            Dictionary with staff data or None if not found
        """
        try:
            staff = Staff.objects.select_related(
                'user', 'supervisor', 'created_by'
            ).prefetch_related(
                'subject_assignments',
                'duties',
                'qualifications',
                'work_experiences',
                'evaluations',
                'documents'
            ).get(id=staff_id)

            return {
                'id': staff.id,
                'staff_id': staff.staff_id,
                'user_id': staff.user.id if staff.user else None,
                'full_name': staff.get_full_name,
                'first_name': staff.first_name,
                'last_name': staff.last_name,
                'middle_name': staff.middle_name,
                'gender': staff.gender,
                'gender_display': staff.get_gender_display(),
                'date_of_birth': staff.date_of_birth.isoformat(),
                'age': staff.age,
                'marital_status': staff.marital_status,
                'marital_status_display': staff.get_marital_status_display(),
                'blood_group': staff.blood_group,
                'email': staff.email,
                'phone': staff.phone,
                'alternate_phone': staff.alternate_phone,
                'address': staff.address,
                'city': staff.city,
                'state_of_origin': staff.state_of_origin,
                'lga': staff.lga,
                'nationality': staff.nationality,
                'passport_url': staff.passport_photograph.url if staff.passport_photograph else None,

                # Employment
                'staff_type': staff.staff_type,
                'staff_type_display': staff.get_staff_type_display(),
                'staff_category': staff.staff_category,
                'staff_category_display': staff.get_staff_category_display(),
                'employment_status': staff.employment_status,
                'employment_status_display': staff.get_employment_status_display(),
                'employment_type': staff.employment_type,
                'employment_type_display': staff.get_employment_type_display(),
                'shift': staff.shift,
                'shift_display': staff.get_shift_display(),
                'date_employed': staff.date_employed.isoformat(),
                'date_confirmed': staff.date_confirmed.isoformat() if staff.date_confirmed else None,
                'retirement_date': staff.retirement_date.isoformat() if staff.retirement_date else None,
                'years_of_service': staff.years_of_service,
                'department': staff.department,
                'unit': staff.unit,

                # Supervisor
                'supervisor': {
                    'id': staff.supervisor.id,
                    'name': staff.supervisor.get_full_name,
                    'staff_id': staff.supervisor.staff_id,
                } if staff.supervisor else None,

                # ualifications
                'highest_qualification': staff.highest_qualification,
                'highest_qualification_display': staff.get_highest_qualification_display(),
                'qualification_details': staff.qualification_details,

                # Bank Details
                'bank_name': staff.bank_name,
                'account_number': staff.account_number,
                'account_name': staff.account_name,
                'pension_number': staff.pension_number,
                'tax_id': staff.tax_id,

                # Emergency Contact
                'emergency_contact_name': staff.emergency_contact_name,
                'emergency_contact_phone': staff.emergency_contact_phone,
                'emergency_contact_relationship': staff.emergency_contact_relationship,

                # Medical
                'medical_conditions': staff.medical_conditions,
                'allergies': staff.allergies,
                'doctor_name': staff.doctor_name,
                'doctor_phone': staff.doctor_phone,

                # Statistics
                'subject_count': staff.subject_assignments.count(),
                'duty_count': staff.duties.filter(is_active=True).count(),
                'qualification_count': staff.qualifications.count(),
                'experience_count': staff.work_experiences.count(),
                'document_count': staff.documents.count(),

                # Metadata
                'created_by': staff.created_by.get_full_name() if staff.created_by else None,
                'created_at': staff.created_at.isoformat(),
                'updated_at': staff.updated_at.isoformat(),
            }
        except Staff.DoesNotExist:
            return None

    @staticmethod
    def get_by_staff_id(staff_id: str) -> Optional[Dict[str, Any]]:
        """
        Get staff member by staff ID (e.g., STF-2024-001).
        
        Args:
            staff_id: Unique staff identifier
            
        Returns:
            Dictionary with staff data or None if not found
        """
        try:
            staff = Staff.objects.get(staff_id=staff_id)
            return StaffSelector.get_by_id(staff.id)
        except Staff.DoesNotExist:
            return None

    @staticmethod
    def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        """
        Get staff member by email address.
        
        Args:
            email: Email address
            
        Returns:
            Dictionary with staff data or None if not found
        """
        try:
            staff = Staff.objects.get(email=email)
            return StaffSelector.get_by_id(staff.id)
        except Staff.DoesNotExist:
            return None

    @staticmethod
    def list_staff(
        staff_type: Optional[str] = None,
        staff_category: Optional[str] = None,
        employment_status: Optional[str] = None,
        department: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = 'last_name'
    ) -> List[Dict[str, Any]]:
        """
        List staff members with filtering and pagination.
        
        Args:
            staff_type: Filter by staff type
            staff_category: Filter by staff category
            employment_status: Filter by employment status
            department: Filter by department (partial match)
            search: Search across name, email, phone, staff_id
            limit: Maximum number of records to return
            offset: Number of records to skip (for pagination)
            order_by: Field to order by (prefix with '-' for descending)
            
        Returns:
            List of staff member dictionaries
        """
        queryset = Staff.objects.all()

        # Apply filters
        if staff_type:
            queryset = queryset.filter(staff_type=staff_type)

        if staff_category:
            queryset = queryset.filter(staff_category=staff_category)

        if employment_status:
            queryset = queryset.filter(employment_status=employment_status)

        if department:
            queryset = queryset.filter(department__icontains=department)

        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(middle_name__icontains=search) |
                Q(staff_id__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )

        # Apply ordering
        if order_by.startswith('-'):
            queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by(order_by, 'first_name')

        # Apply pagination
        queryset = queryset[offset:offset + limit]

        staff_list = []
        for s in queryset:
            staff_list.append({
                'id': s.id,
                'staff_id': s.staff_id,
                'full_name': s.get_full_name,
                'first_name': s.first_name,
                'last_name': s.last_name,
                'middle_name': s.middle_name,
                'email': s.email,
                'phone': s.phone,
                'staff_type': s.staff_type,
                'staff_type_display': s.get_staff_type_display(),
                'staff_category': s.staff_category,
                'staff_category_display': s.get_staff_category_display(),
                'employment_status': s.employment_status,
                'employment_status_display': s.get_employment_status_display(),
                'department': s.department,
                'unit': s.unit,
                'gender': s.get_gender_display(),
                'date_employed': s.date_employed.isoformat(),
                'passport_url': s.passport_photograph.url if s.passport_photograph else None,
                'supervisor_name': s.supervisor.get_full_name if s.supervisor else None,
            })

        return staff_list

    @staticmethod
    def get_teaching_staff(
        class_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        session_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get teaching staff, optionally filtered by class/subject.
        
        Args:
            class_id: Filter by class
            subject_id: Filter by subject
            session_id: Academic session
            
        Returns:
            List of teaching staff dictionaries
        """
        queryset = Staff.objects.filter(
            staff_category=StaffCategory.ACADEMIC,
            employment_status=EmploymentStatus.ACTIVE
        )

        if class_id or subject_id:
            assignments = SubjectAssignment.objects.all()
            if class_id:
                assignments = assignments.filter(student_class_id=class_id)
            if subject_id:
                assignments = assignments.filter(subject_id=subject_id)
            if session_id:
                assignments = assignments.filter(academic_session_id=session_id)

            staff_ids = assignments.values_list('staff_id', flat=True).distinct()
            queryset = queryset.filter(id__in=staff_ids)

        return StaffSelector._queryset_to_list(queryset)

    @staticmethod
    def get_form_masters(
        class_id: Optional[int] = None,
        session_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get form masters/class teachers.
        
        Args:
            class_id: Filter by class
            session_id: Academic session
            
        Returns:
            List of form master dictionaries
        """
        assignments = SubjectAssignment.objects.filter(is_form_master=True)
        
        if class_id:
            assignments = assignments.filter(student_class_id=class_id)
        if session_id:
            assignments = assignments.filter(academic_session_id=session_id)

        staff_ids = assignments.values_list('staff_id', flat=True).distinct()
        queryset = Staff.objects.filter(id__in=staff_ids)
        
        return StaffSelector._queryset_to_list(queryset)

    @staticmethod
    def get_duty_staff(
        duty_post: Optional[str] = None,
        is_active: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get staff assigned to specific duties.
        
        Args:
            duty_post: Filter by duty post type
            is_active: Whether to include only active assignments
            
        Returns:
            List of staff dictionaries with duty information
        """
        duties = DutyAssignment.objects.filter(is_active=is_active)
        if duty_post:
            duties = duties.filter(duty_post=duty_post)

        staff_ids = duties.values_list('staff_id', flat=True).distinct()
        queryset = Staff.objects.filter(id__in=staff_ids)
        
        staff_list = []
        for staff in queryset:
            staff_dict = StaffSelector._staff_to_dict(staff)
            # Add duty information
            staff_duties = duties.filter(staff_id=staff.id)
            staff_dict['assigned_duties'] = [
                {
                    'id': d.id,
                    'duty_post': d.duty_post,
                    'duty_post_display': d.get_duty_post_display(),
                    'club_name': d.club_name,
                    'sport_name': d.sport_name,
                    'house_name': d.house_name,
                    'is_active': d.is_active,
                }
                for d in staff_duties
            ]
            staff_list.append(staff_dict)

        return staff_list

    @staticmethod
    def get_upcoming_birthdays(days: int = 30) -> List[Dict[str, Any]]:
        """
        Get staff with birthdays in the next N days.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of staff with upcoming birthdays
        """
        today = date.today()
        end_date = today + timedelta(days=days)
        
        # This is a bit complex because we need to compare month and day
        # We'll get all active staff and filter in Python
        staff = Staff.objects.filter(employment_status='active')
        
        birthdays = []
        for s in staff:
            # Create birthday date for this year
            birthday_this_year = date(today.year, s.date_of_birth.month, s.date_of_birth.day)
            
            # If birthday already passed this year, use next year
            if birthday_this_year < today:
                birthday_this_year = date(today.year + 1, s.date_of_birth.month, s.date_of_birth.day)
            
            # Check if within range
            if birthday_this_year <= end_date:
                days_until = (birthday_this_year - today).days
                birthdays.append({
                    'id': s.id,
                    'staff_id': s.staff_id,
                    'name': s.get_full_name,
                    'first_name': s.first_name,
                    'last_name': s.last_name,
                    'date': s.date_of_birth.isoformat(),
                    'birthday_formatted': s.date_of_birth.strftime('%B %d'),
                    'days_until': days_until,
                    'department': s.department,
                    'age_will_be': birthday_this_year.year - s.date_of_birth.year,
                    'email': s.email,
                    'phone': s.phone,
                })
        
        # Sort by days until birthday
        birthdays.sort(key=lambda x: x['days_until'])
        
        return birthdays

    @staticmethod
    def get_unique_departments() -> List[str]:
        """
        Get list of unique departments with active staff.
        
        Returns:
            List of department names
        """
        return list(
            Staff.objects.filter(
                employment_status='active'
            ).exclude(
                department=''
            ).values_list(
                'department', flat=True
            ).distinct().order_by('department')
        )

    @staticmethod
    def get_supervisor_choices(staff_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get list of staff who can be supervisors.
        
        Args:
            staff_id: Current staff ID to exclude from list
            
        Returns:
            List of potential supervisor dictionaries
        """
        queryset = Staff.objects.filter(
            employment_status='active'
        ).exclude(
            staff_type__in=[StaffType.CLEANER, StaffType.SECURITY, StaffType.DRIVER]
        )
        
        if staff_id:
            queryset = queryset.exclude(id=staff_id)
        
        supervisors = []
        for s in queryset.order_by('last_name', 'first_name'):
            supervisors.append({
                'id': s.id,
                'staff_id': s.staff_id,
                'name': s.get_full_name,
                'department': s.department,
                'staff_type': s.get_staff_type_display(),
            })
        
        return supervisors

    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """
        Get staff statistics.
        
        Returns:
            Dictionary with various staff statistics
        """
        total = Staff.objects.count()
        active = Staff.objects.filter(employment_status='active').count()
        
        # Get counts by category
        by_category = {}
        for cat_code, cat_label in StaffCategory.CHOICES:
            count = Staff.objects.filter(staff_category=cat_code).count()
            if count > 0:
                by_category[cat_code] = {
                    'label': cat_label,
                    'count': count
                }
        
        # Get counts by status
        by_status = {}
        for status_code, status_label in EmploymentStatus.CHOICES:
            count = Staff.objects.filter(employment_status=status_code).count()
            if count > 0:
                by_status[status_code] = {
                    'label': status_label,
                    'count': count
                }
        
        # Get gender distribution
        male = Staff.objects.filter(gender='M').count()
        female = Staff.objects.filter(gender='F').count()
        
        # Get teaching vs non-teaching
        teaching = Staff.objects.filter(staff_category=StaffCategory.ACADEMIC).count()
        non_teaching = Staff.objects.exclude(staff_category=StaffCategory.ACADEMIC).count()
        
        # Get department distribution
        department_counts = Staff.objects.values('department').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        departments = []
        for dept in department_counts:
            if dept['department']:
                departments.append({
                    'name': dept['department'],
                    'count': dept['count']
                })
        
        return {
            'total_staff': total,
            'active': active,
            'on_leave': Staff.objects.filter(employment_status='on_leave').count(),
            'suspended': Staff.objects.filter(employment_status='suspended').count(),
            'terminated': Staff.objects.filter(employment_status='terminated').count(),
            'by_category': by_category,
            'by_status': by_status,
            'male': male,
            'female': female,
            'teaching': teaching,
            'non_teaching': non_teaching,
            'departments': departments,
        }

    @staticmethod
    def search_staff(query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Quick search for staff autocomplete.
        
        Args:
            query: Search string
            limit: Maximum results
            
        Returns:
            List of staff matching search
        """
        if not query or len(query) < 2:
            return []
        
        staff = Staff.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(staff_id__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        ).filter(employment_status='active')[:limit]
        
        results = []
        for s in staff:
            results.append({
                'id': s.id,
                'staff_id': s.staff_id,
                'name': s.get_full_name,
                'email': s.email,
                'phone': s.phone,
                'department': s.department,
                'staff_type': s.get_staff_type_display(),
            })
        
        return results

    @staticmethod
    def _staff_to_dict(staff) -> Dict[str, Any]:
        """Convert staff model to dictionary (helper method)."""
        return {
            'id': staff.id,
            'staff_id': staff.staff_id,
            'full_name': staff.get_full_name,
            'first_name': staff.first_name,
            'last_name': staff.last_name,
            'email': staff.email,
            'phone': staff.phone,
            'staff_type': staff.staff_type,
            'staff_type_display': staff.get_staff_type_display(),
            'staff_category': staff.staff_category,
            'staff_category_display': staff.get_staff_category_display(),
            'employment_status': staff.employment_status,
            'employment_status_display': staff.get_employment_status_display(),
            'department': staff.department,
            'unit': staff.unit,
            'gender': staff.get_gender_display(),
            'date_employed': staff.date_employed.isoformat(),
            'passport_url': staff.passport_photograph.url if staff.passport_photograph else None,
        }

    @staticmethod
    def _queryset_to_list(queryset) -> List[Dict[str, Any]]:
        """Convert staff queryset to list of dictionaries."""
        return [StaffSelector._staff_to_dict(s) for s in queryset]


class SubjectAssignmentSelector:
    """
    Subject assignment read operations.
    """

    @staticmethod
    def get_by_id(assignment_id: int) -> Optional[Dict[str, Any]]:
        """Get subject assignment by ID."""
        try:
            a = SubjectAssignment.objects.select_related(
                'staff', 'subject', 'student_class', 
                'academic_session', 'academic_term', 'assigned_by'
            ).get(id=assignment_id)
            
            return {
                'id': a.id,
                'staff': {
                    'id': a.staff.id,
                    'name': a.staff.get_full_name,
                    'staff_id': a.staff.staff_id,
                },
                'subject': {
                    'id': a.subject.id,
                    'name': a.subject.name,
                    'code': a.subject.code,
                },
                'class': {
                    'id': a.student_class.id,
                    'name': a.student_class.display_name,
                },
                'session': {
                    'id': a.academic_session.id,
                    'name': a.academic_session.name,
                },
                'term': {
                    'id': a.academic_term.id,
                    'name': a.academic_term.name,
                    'display': a.academic_term.get_term_display() if a.academic_term else None,
                } if a.academic_term else None,
                'is_class_teacher': a.is_class_teacher,
                'is_form_master': a.is_form_master,
                'periods_per_week': a.periods_per_week,
                'assigned_by': a.assigned_by.get_full_name() if a.assigned_by else None,
                'assigned_at': a.assigned_at.isoformat(),
            }
        except SubjectAssignment.DoesNotExist:
            return None

    @staticmethod
    def get_for_staff(
        staff_id: int, 
        session_id: Optional[int] = None,
        academic_year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get subject assignments for a staff member.
        
        Args:
            staff_id: Staff ID
            session_id: Filter by academic session
            academic_year: Filter by year
            
        Returns:
            List of assignment dictionaries
        """
        queryset = SubjectAssignment.objects.filter(
            staff_id=staff_id
        ).select_related(
            'subject', 'student_class', 'academic_session', 'academic_term'
        )

        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        
        if academic_year:
            queryset = queryset.filter(academic_session__name__icontains=str(academic_year))

        assignments = []
        for a in queryset.order_by('student_class', 'subject'):
            assignments.append({
                'id': a.id,
                'subject': {
                    'id': a.subject.id,
                    'name': a.subject.name,
                    'code': a.subject.code,
                },
                'class': {
                    'id': a.student_class.id,
                    'name': a.student_class.display_name,
                },
                'session': a.academic_session.name,
                'term': a.academic_term.get_term_display() if a.academic_term else None,
                'is_class_teacher': a.is_class_teacher,
                'is_form_master': a.is_form_master,
                'periods_per_week': a.periods_per_week,
            })

        return assignments

    @staticmethod
    def get_for_class(
        class_id: int,
        session_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get subject assignments for a class.
        
        Args:
            class_id: Class ID
            session_id: Academic session ID
            
        Returns:
            List of assignment dictionaries
        """
        queryset = SubjectAssignment.objects.filter(
            student_class_id=class_id
        ).select_related('staff', 'subject')

        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)

        assignments = []
        for a in queryset:
            assignments.append({
                'id': a.id,
                'staff': {
                    'id': a.staff.id,
                    'name': a.staff.get_full_name,
                },
                'subject': {
                    'id': a.subject.id,
                    'name': a.subject.name,
                },
                'periods_per_week': a.periods_per_week,
                'is_form_master': a.is_form_master,
            })

        return assignments

    @staticmethod
    def get_form_master_for_class(
        class_id: int,
        session_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get form master for a specific class.
        
        Args:
            class_id: Class ID
            session_id: Academic session ID
            
        Returns:
            Form master dictionary or None
        """
        try:
            assignment = SubjectAssignment.objects.select_related('staff').get(
                student_class_id=class_id,
                is_form_master=True,
                academic_session_id=session_id
            )
            return {
                'id': assignment.id,
                'staff_id': assignment.staff.id,
                'staff_name': assignment.staff.get_full_name,
                'staff_email': assignment.staff.email,
                'staff_phone': assignment.staff.phone,
                'staff_passport': assignment.staff.passport_photograph.url if assignment.staff.passport_photograph else None,
            }
        except SubjectAssignment.DoesNotExist:
            return None

    @staticmethod
    def get_teaching_load(staff_id: int, session_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get teaching load summary for a staff member.
        
        Args:
            staff_id: Staff ID
            session_id: Academic session ID
            
        Returns:
            Teaching load statistics
        """
        assignments = SubjectAssignment.objects.filter(staff_id=staff_id)
        
        if session_id:
            assignments = assignments.filter(academic_session_id=session_id)
        
        total_periods = sum(a.periods_per_week for a in assignments)
        total_classes = assignments.values('student_class').distinct().count()
        total_subjects = assignments.values('subject').distinct().count()
        
        return {
            'staff_id': staff_id,
            'total_assignments': assignments.count(),
            'total_periods': total_periods,
            'total_classes': total_classes,
            'total_subjects': total_subjects,
            'average_periods_per_class': total_periods / total_classes if total_classes > 0 else 0,
            'is_form_master': assignments.filter(is_form_master=True).exists(),
        }



class DutyAssignmentSelector:
    """
    Duty assignment read operations.
    """

    @staticmethod
    def get_by_id(duty_id: int) -> Optional[Dict[str, Any]]:
        """Get duty assignment by ID."""
        try:
            d = DutyAssignment.objects.select_related(
                'staff', 'academic_session', 'student_class', 'assigned_by'
            ).get(id=duty_id)
            
            return {
                'id': d.id,
                'staff': {
                    'id': d.staff.id,
                    'name': d.staff.get_full_name,
                },
                'duty_post': d.duty_post,
                'duty_post_display': d.get_duty_post_display(),
                'academic_session': {
                    'id': d.academic_session.id,
                    'name': d.academic_session.name,
                } if d.academic_session else None,
                'student_class': {
                    'id': d.student_class.id,
                    'name': d.student_class.display_name,
                } if d.student_class else None,
                'club_name': d.club_name,
                'sport_name': d.sport_name,
                'house_name': d.house_name,
                'day_of_week': d.day_of_week,
                'start_time': d.start_time.isoformat() if d.start_time else None,
                'end_time': d.end_time.isoformat() if d.end_time else None,
                'is_active': d.is_active,
                'assigned_by': d.assigned_by.get_full_name() if d.assigned_by else None,
                'assigned_at': d.assigned_at.isoformat(),
            }
        except DutyAssignment.DoesNotExist:
            return None

    @staticmethod
    def get_for_staff(staff_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get duty assignments for a staff member.
        
        Args:
            staff_id: Staff ID
            active_only: Whether to include only active assignments
            
        Returns:
            List of duty assignment dictionaries
        """
        queryset = DutyAssignment.objects.filter(
            staff_id=staff_id
        ).select_related('academic_session', 'student_class')
        
        if active_only:
            queryset = queryset.filter(is_active=True)

        duties = []
        for d in queryset.order_by('-is_active', 'duty_post'):
            duties.append({
                'id': d.id,
                'duty_post': d.duty_post,
                'duty_post_display': d.get_duty_post_display(),
                'session': d.academic_session.name if d.academic_session else None,
                'class': d.student_class.display_name if d.student_class else None,
                'club_name': d.club_name,
                'sport_name': d.sport_name,
                'house_name': d.house_name,
                'day_of_week': d.get_day_of_week_display() if d.day_of_week else None,
                'start_time': d.start_time.isoformat() if d.start_time else None,
                'end_time': d.end_time.isoformat() if d.end_time else None,
                'is_active': d.is_active,
            })

        return duties

    @staticmethod
    def get_staff_by_duty(
        duty_post: str,
        session_id: Optional[int] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get staff assigned to a specific duty.
        
        Args:
            duty_post: Duty post type
            session_id: Academic session ID
            active_only: Whether to include only active assignments
            
        Returns:
            List of staff dictionaries
        """
        queryset = DutyAssignment.objects.filter(
            duty_post=duty_post
        ).select_related('staff')
        
        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        staff_list = []
        for d in queryset:
            staff_list.append({
                'id': d.staff.id,
                'staff_id': d.staff.staff_id,
                'name': d.staff.get_full_name,
                'department': d.staff.department,
                'duty_details': {
                    'id': d.id,
                    'club_name': d.club_name,
                    'sport_name': d.sport_name,
                    'house_name': d.house_name,
                }
            })
        
        return staff_list


class LeaveRequestSelector:
    """
    Leave request read operations.
    """

    @staticmethod
    def get_by_id(leave_id: int) -> Optional[Dict[str, Any]]:
        """
        Get leave request by ID.
        
        Args:
            leave_id: Leave request ID
            
        Returns:
            Leave request dictionary or None
        """
        try:
            lr = LeaveRequest.objects.select_related(
                'staff', 'approved_by'
            ).get(id=leave_id)
            
            return {
                'id': lr.id,
                'staff': {
                    'id': lr.staff.id,
                    'name': lr.staff.get_full_name,
                    'staff_id': lr.staff.staff_id,
                    'email': lr.staff.email,
                    'phone': lr.staff.phone,
                    'department': lr.staff.department,
                },
                'leave_type': lr.leave_type,
                'leave_type_display': lr.get_leave_type_display(),
                'start_date': lr.start_date.isoformat(),
                'end_date': lr.end_date.isoformat(),
                'return_date': lr.return_date.isoformat(),
                'days_requested': lr.days_requested,
                'reason': lr.reason,
                'handover_notes': lr.handover_notes,
                'alternative_phone': lr.alternative_phone,
                'alternative_email': lr.alternative_email,
                'status': lr.status,
                'status_display': lr.get_status_display(),
                'approved_by': lr.approved_by.get_full_name() if lr.approved_by else None,
                'approved_at': lr.approved_at.isoformat() if lr.approved_at else None,
                'approval_notes': lr.approval_notes,
                'created_at': lr.created_at.isoformat(),
            }
        except LeaveRequest.DoesNotExist:
            return None

    @staticmethod
    def get_for_staff(
        staff_id: int,
        status: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get leave requests for a staff member.
        
        Args:
            staff_id: Staff ID
            status: Filter by status
            year: Filter by year
            limit: Maximum results
            
        Returns:
            List of leave request dictionaries
        """
        queryset = LeaveRequest.objects.filter(staff_id=staff_id)

        if status:
            queryset = queryset.filter(status=status)

        if year:
            queryset = queryset.filter(start_date__year=year)

        leaves = []
        for lr in queryset.order_by('-created_at')[:limit]:
            leaves.append({
                'id': lr.id,
                'leave_type': lr.leave_type,
                'leave_type_display': lr.get_leave_type_display(),
                'start_date': lr.start_date.isoformat(),
                'end_date': lr.end_date.isoformat(),
                'return_date': lr.return_date.isoformat(),
                'days_requested': lr.days_requested,
                'reason': lr.reason[:100] + ('...' if len(lr.reason) > 100 else ''),
                'status': lr.status,
                'status_display': lr.get_status_display(),
                'approved_by': lr.approved_by.get_full_name() if lr.approved_by else None,
                'approved_at': lr.approved_at.isoformat() if lr.approved_at else None,
                'created_at': lr.created_at.isoformat(),
            })

        return leaves

    @staticmethod
    def list_leave_requests(
        status: Optional[str] = None,
        leave_type: Optional[str] = None,
        staff_id: Optional[int] = None,
        department: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List leave requests with filtering and pagination.
        
        Args:
            status: Filter by status
            leave_type: Filter by leave type
            staff_id: Filter by staff
            department: Filter by department
            start_date: Filter by start date >=
            end_date: Filter by end date <=
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            Tuple of (requests list, total count)
        """
        queryset = LeaveRequest.objects.select_related('staff').all()

        if status:
            queryset = queryset.filter(status=status)

        if leave_type:
            queryset = queryset.filter(leave_type=leave_type)

        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)

        if department:
            queryset = queryset.filter(staff__department__icontains=department)

        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)

        total = queryset.count()

        requests = []
        for lr in queryset.order_by('-created_at')[offset:offset + limit]:
            requests.append({
                'id': lr.id,
                'staff_id': lr.staff.id,
                'staff_name': lr.staff.get_full_name,
                'staff_department': lr.staff.department,
                'leave_type': lr.leave_type,
                'leave_type_display': lr.get_leave_type_display(),
                'start_date': lr.start_date.isoformat(),
                'end_date': lr.end_date.isoformat(),
                'days': lr.days_requested,
                'status': lr.status,
                'status_display': lr.get_status_display(),
                'reason': lr.reason[:100],
                'created_at': lr.created_at.isoformat(),
            })

        return requests, total

    @staticmethod
    def get_pending_requests() -> List[Dict[str, Any]]:
        """
        Get all pending leave requests.
        
        Returns:
            List of pending leave requests
        """
        pending = LeaveRequest.objects.filter(
            status=LeaveStatus.PENDING
        ).select_related('staff').order_by('start_date')

        requests = []
        for lr in pending:
            requests.append({
                'id': lr.id,
                'staff_id': lr.staff.id,
                'staff_name': lr.staff.get_full_name,
                'staff_type': lr.staff.get_staff_type_display(),
                'staff_department': lr.staff.department,
                'leave_type': lr.get_leave_type_display(),
                'start_date': lr.start_date.isoformat(),
                'end_date': lr.end_date.isoformat(),
                'days': lr.days_requested,
                'reason': lr.reason[:100],
                'created_at': lr.created_at.isoformat(),
            })

        return requests

    @staticmethod
    def get_leave_statistics(
        staff_id: Optional[int] = None,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get leave statistics.
        
        Args:
            staff_id: Filter by staff
            year: Filter by year
            
        Returns:
            Leave statistics dictionary
        """
        queryset = LeaveRequest.objects.all()
        
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        if year:
            queryset = queryset.filter(start_date__year=year)
        
        total = queryset.count()
        
        return {
            'total': total,
            'by_status': {
                status: queryset.filter(status=status).count()
                for status, _ in LeaveStatus.CHOICES
            },
            'by_type': {
                l_type: queryset.filter(leave_type=l_type).count()
                for l_type, _ in LeaveType.CHOICES
            },
            'total_days': queryset.aggregate(total_days=models.Sum('days_requested'))['total_days'] or 0,
            'average_days': queryset.aggregate(avg_days=models.Avg('days_requested'))['avg_days'] or 0,
        }


class StaffAttendanceSelector:
    """
    Staff attendance read operations.
    """

    @staticmethod
    def get_by_id(attendance_id: int) -> Optional[Dict[str, Any]]:
        """Get attendance record by ID."""
        try:
            a = StaffAttendance.objects.select_related(
                'staff', 'marked_by'
            ).get(id=attendance_id)
            
            return {
                'id': a.id,
                'staff': {
                    'id': a.staff.id,
                    'name': a.staff.get_full_name,
                    'staff_id': a.staff.staff_id,
                },
                'date': a.date.isoformat(),
                'check_in_time': a.check_in_time.isoformat() if a.check_in_time else None,
                'check_out_time': a.check_out_time.isoformat() if a.check_out_time else None,
                'status': a.status,
                'status_display': a.get_status_display(),
                'check_in_location': a.check_in_location,
                'check_out_location': a.check_out_location,
                'notes': a.notes,
                'marked_by': a.marked_by.get_full_name() if a.marked_by else None,
                'created_at': a.created_at.isoformat(),
            }
        except StaffAttendance.DoesNotExist:
            return None

    @staticmethod
    def get_for_date(
        date_obj: date,
        department: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get attendance for a specific date.
        
        Args:
            date_obj: Date to get attendance for
            department: Filter by department
            
        Returns:
            List of attendance records
        """
        attendances = StaffAttendance.objects.filter(
            date=date_obj
        ).select_related('staff').order_by('staff__last_name')

        if department:
            attendances = attendances.filter(staff__department=department)

        records = []
        for a in attendances:
            records.append({
                'id': a.id,
                'staff_id': a.staff.id,
                'staff_name': a.staff.get_full_name,
                'staff_type': a.staff.get_staff_type_display(),
                'department': a.staff.department,
                'status': a.status,
                'status_display': a.get_status_display(),
                'check_in': a.check_in_time.isoformat() if a.check_in_time else None,
                'check_out': a.check_out_time.isoformat() if a.check_out_time else None,
                'notes': a.notes,
            })

        return records

    @staticmethod
    def get_staff_summary(
        staff_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get attendance summary for a staff member over a period.
        
        Args:
            staff_id: Staff ID
            start_date: Period start date
            end_date: Period end date
            
        Returns:
            Attendance summary dictionary
        """
        attendances = StaffAttendance.objects.filter(
            staff_id=staff_id,
            date__gte=start_date,
            date__lte=end_date
        )

        total_days = (end_date - start_date).days + 1
        present = attendances.filter(status='present').count()
        absent = attendances.filter(status='absent').count()
        late = attendances.filter(status='late').count()
        leave = attendances.filter(status='on_leave').count()
        half_day = attendances.filter(status='half_day').count()

        return {
            'staff_id': staff_id,
            'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
            'total_days': total_days,
            'present': present,
            'absent': absent,
            'late': late,
            'on_leave': leave,
            'half_day': half_day,
            'attendance_rate': (present / total_days * 100) if total_days > 0 else 0,
            'punctuality_rate': ((present - late) / present * 100) if present > 0 else 0,
            'records': [
                {
                    'date': a.date.isoformat(),
                    'status': a.status,
                    'check_in': a.check_in_time.isoformat() if a.check_in_time else None,
                    'check_out': a.check_out_time.isoformat() if a.check_out_time else None,
                }
                for a in attendances.order_by('date')
            ],
        }

    @staticmethod
    def get_daily_summary(
        date_obj: date,
        department: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get daily attendance summary.
        
        Args:
            date_obj: Date to summarize
            department: Filter by department
            
        Returns:
            Daily summary dictionary
        """
        attendances = StaffAttendance.objects.filter(date=date_obj)
        
        if department:
            attendances = attendances.filter(staff__department=department)

        return {
            'date': date_obj.isoformat(),
            'total': attendances.count(),
            'by_status': {
                'present': attendances.filter(status='present').count(),
                'absent': attendances.filter(status='absent').count(),
                'late': attendances.filter(status='late').count(),
                'on_leave': attendances.filter(status='on_leave').count(),
                'half_day': attendances.filter(status='half_day').count(),
            },
            'by_department': list(
                attendances.values('staff__department').annotate(
                    count=models.Count('id')
                ).order_by('staff__department')
            ),
        }



class PerformanceSelector:
    """
    Performance evaluation read operations.
    """

    @staticmethod
    def get_by_id(eval_id: int) -> Optional[Dict[str, Any]]:
        """Get performance evaluation by ID."""
        try:
            e = PerformanceEvaluation.objects.select_related(
                'staff', 'evaluator'
            ).get(id=eval_id)
            
            return {
                'id': e.id,
                'staff': {
                    'id': e.staff.id,
                    'name': e.staff.get_full_name,
                },
                'evaluator': {
                    'id': e.evaluator.id,
                    'name': e.evaluator.get_full_name,
                } if e.evaluator else None,
                'evaluation_date': e.evaluation_date.isoformat(),
                'evaluation_period': e.evaluation_period,
                'punctuality': e.punctuality,
                'job_knowledge': e.job_knowledge,
                'quality_of_work': e.quality_of_work,
                'communication': e.communication,
                'teamwork': e.teamwork,
                'initiative': e.initiative,
                'overall_rating': e.overall_rating,
                'strengths': e.strengths,
                'areas_for_improvement': e.areas_for_improvement,
                'overall_comments': e.overall_comments,
                'recommendation': e.recommendation,
                'created_at': e.created_at.isoformat(),
            }
        except PerformanceEvaluation.DoesNotExist:
            return None

    @staticmethod
    def get_for_staff(staff_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get performance evaluations for a staff member.
        
        Args:
            staff_id: Staff ID
            limit: Maximum results
            
        Returns:
            List of evaluation dictionaries
        """
        evaluations = PerformanceEvaluation.objects.filter(
            staff_id=staff_id
        ).select_related('evaluator').order_by('-evaluation_date')[:limit]

        evals = []
        for e in evaluations:
            evals.append({
                'id': e.id,
                'evaluation_date': e.evaluation_date.isoformat(),
                'evaluation_period': e.evaluation_period,
                'evaluator': e.evaluator.get_full_name() if e.evaluator else None,
                'punctuality': e.punctuality,
                'job_knowledge': e.job_knowledge,
                'quality_of_work': e.quality_of_work,
                'communication': e.communication,
                'teamwork': e.teamwork,
                'initiative': e.initiative,
                'overall_rating': e.overall_rating,
                'strengths': e.strengths[:100] + ('...' if len(e.strengths) > 100 else ''),
            })

        return evals

    @staticmethod
    def get_average_ratings(
        staff_id: int,
        year: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Get average ratings for a staff member.
        
        Args:
            staff_id: Staff ID
            year: Filter by year
            
        Returns:
            Dictionary of average ratings
        """
        queryset = PerformanceEvaluation.objects.filter(staff_id=staff_id)

        if year:
            queryset = queryset.filter(evaluation_date__year=year)

        if not queryset.exists():
            return {}

        return {
            'punctuality': queryset.aggregate(avg=models.Avg('punctuality'))['avg'],
            'job_knowledge': queryset.aggregate(avg=models.Avg('job_knowledge'))['avg'],
            'quality_of_work': queryset.aggregate(avg=models.Avg('quality_of_work'))['avg'],
            'communication': queryset.aggregate(avg=models.Avg('communication'))['avg'],
            'teamwork': queryset.aggregate(avg=models.Avg('teamwork'))['avg'],
            'initiative': queryset.aggregate(avg=models.Avg('initiative'))['avg'],
            'overall': queryset.aggregate(avg=models.Avg('overall_rating'))['avg'],
            'total_evaluations': queryset.count(),
        }

    @staticmethod
    def get_performance_trends(staff_id: int, years: int = 3) -> List[Dict[str, Any]]:
        """
        Get performance trends over years.
        
        Args:
            staff_id: Staff ID
            years: Number of years to look back
            
        Returns:
            List of yearly performance summaries
        """
        current_year = date.today().year
        trends = []
        
        for year in range(current_year - years + 1, current_year + 1):
            ratings = PerformanceSelector.get_average_ratings(staff_id, year)
            if ratings:
                trends.append({
                    'year': year,
                    'ratings': ratings
                })
        
        return trends


class QualificationSelector:
    """
    Qualification read operations.
    """

    @staticmethod
    def get_for_staff(staff_id: int) -> List[Dict[str, Any]]:
        """
        Get qualifications for a staff member.
        
        Args:
            staff_id: Staff ID
            
        Returns:
            List of qualification dictionaries
        """
        qualifications = Qualification.objects.filter(
            staff_id=staff_id
        ).order_by('-year_obtained')

        quals = []
        for q in qualifications:
            quals.append({
                'id': q.id,
                'qualification_type': q.qualification_type,
                'qualification_type_display': q.get_qualification_type_display(),
                'title': q.title,
                'institution': q.institution,
                'year_obtained': q.year_obtained,
                'certificate_number': q.certificate_number,
                'expiry_date': q.expiry_date.isoformat() if q.expiry_date else None,
                'document_url': q.document.url if q.document else None,
                'verified': q.verified,
                'verified_by': q.verified_by.get_full_name() if q.verified_by else None,
                'verified_at': q.verified_at.isoformat() if q.verified_at else None,
            })

        return quals


class WorkExperienceSelector:
    """
    Work experience read operations.
    """

    @staticmethod
    def get_for_staff(staff_id: int) -> List[Dict[str, Any]]:
        """
        Get work experience for a staff member.
        
        Args:
            staff_id: Staff ID
            
        Returns:
            List of work experience dictionaries
        """
        experiences = WorkExperience.objects.filter(
            staff_id=staff_id
        ).order_by('-start_date')

        exp_list = []
        for e in experiences:
            exp_list.append({
                'id': e.id,
                'employer': e.employer,
                'position': e.position,
                'start_date': e.start_date.isoformat(),
                'end_date': e.end_date.isoformat() if e.end_date else None,
                'is_current': e.is_current,
                'responsibilities': e.responsibilities,
                'referee_name': e.referee_name,
                'referee_phone': e.referee_phone,
                'referee_email': e.referee_email,
            })

        return exp_list


class StaffDocumentSelector:
    """
    Staff document read operations.
    """

    @staticmethod
    def get_for_staff(staff_id: int) -> List[Dict[str, Any]]:
        """
        Get documents for a staff member.
        
        Args:
            staff_id: Staff ID
            
        Returns:
            List of document dictionaries
        """
        documents = StaffDocument.objects.filter(
            staff_id=staff_id
        ).order_by('-uploaded_at')

        docs = []
        for d in documents:
            docs.append({
                'id': d.id,
                'document_type': d.document_type,
                'document_type_display': d.get_document_type_display(),
                'title': d.title,
                'file_url': d.file.url if d.file else None,
                'file_name': d.file.name.split('/')[-1] if d.file else None,
                'file_size': d.file.size if d.file else 0,
                'uploaded_at': d.uploaded_at.isoformat(),
                'uploaded_by': d.uploaded_by.get_full_name() if d.uploaded_by else None,
            })

        return docs
"""
Staffs Forms - ALL forms for staffs app
Using crispy-tailwind for consistent styling
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Fieldset
from crispy_tailwind.layout import Submit as TailwindSubmit
from .models import Staff, SubjectAssignment, DutyAssignment, LeaveRequest, StaffAttendance, PerformanceEvaluation
from .constants import (
    StaffType, EmploymentType, ShiftType, QualificationType,
    LeaveType, DutyPost, Gender, MaritalStatus, BloodGroup,
    NIGERIAN_STATES
)
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector
from apps.corecode.models import Subject


class DateInput(forms.DateInput):
    input_type = 'date'


class TimeInput(forms.TimeInput):
    input_type = 'time'


class StaffForm(forms.ModelForm):
    """Comprehensive form for creating/editing staff members"""
    
    class Meta:
        model = Staff
        fields = [
            # Personal Information
            'first_name', 'last_name', 'middle_name', 'gender', 'date_of_birth',
            'marital_status', 'blood_group',
            # Contact Information
            'email', 'phone', 'alternate_phone', 'address', 'city',
            'state_of_origin', 'lga', 'nationality',
            # Employment Information
            'staff_type', 'employment_type', 'shift', 'date_employed',
            'department', 'unit', 'supervisor',
            # Qualifications
            'highest_qualification', 'qualification_details',
            # Bank Details
            'bank_name', 'account_number', 'account_name',
            'pension_number', 'tax_id',
            # Emergency Contact
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship',
            # Medical Information
            'medical_conditions', 'allergies', 'doctor_name', 'doctor_phone',
            # Photo
            'passport_photograph'
        ]
        widgets = {
            'date_of_birth': DateInput(),
            'date_employed': DateInput(),
            'address': forms.Textarea(attrs={'rows': 2}),
            'qualification_details': forms.Textarea(attrs={'rows': 3}),
            'medical_conditions': forms.Textarea(attrs={'rows': 2}),
            'allergies': forms.Textarea(attrs={'rows': 2}),
            'passport_photograph': forms.FileInput(attrs={'accept': 'image/*'}),
        }
        help_texts = {
            'phone': "Nigerian format: 08012345678",
            'emergency_contact_phone': "Nigerian format: 08012345678",
            'lga': "Local Government Area",
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Limit supervisor choices
        self.fields['supervisor'].queryset = Staff.objects.filter(
            employment_status='active'
        ).exclude(id=self.instance.id if self.instance else None)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.form_class = 'space-y-6'
        self.helper.layout = Layout(
            Fieldset(
                'Personal Information',
                Row(
                    Column('first_name', css_class='w-1/3 pr-2'),
                    Column('last_name', css_class='w-1/3 px-1'),
                    Column('middle_name', css_class='w-1/3 pl-2'),
                ),
                Row(
                    Column('gender', css_class='w-1/4 pr-2'),
                    Column('date_of_birth', css_class='w-1/4 px-1'),
                    Column('marital_status', css_class='w-1/4 px-1'),
                    Column('blood_group', css_class='w-1/4 pl-2'),
                ),
                'passport_photograph',
            ),
            Fieldset(
                'Contact Information',
                Row(
                    Column('email', css_class='w-1/2 pr-2'),
                    Column('phone', css_class='w-1/2 pl-2'),
                ),
                'alternate_phone',
                'address',
                Row(
                    Column('city', css_class='w-1/3 pr-2'),
                    Column('state_of_origin', css_class='w-1/3 px-1'),
                    Column('lga', css_class='w-1/3 pl-2'),
                ),
                'nationality',
            ),
            Fieldset(
                'Employment Information',
                Row(
                    Column('staff_type', css_class='w-1/3 pr-2'),
                    Column('employment_type', css_class='w-1/3 px-1'),
                    Column('shift', css_class='w-1/3 pl-2'),
                ),
                Row(
                    Column('date_employed', css_class='w-1/2 pr-2'),
                    Column('supervisor', css_class='w-1/2 pl-2'),
                ),
                Row(
                    Column('department', css_class='w-1/2 pr-2'),
                    Column('unit', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'Qualifications',
                'highest_qualification',
                'qualification_details',
            ),
            Fieldset(
                'Bank Details',
                Row(
                    Column('bank_name', css_class='w-1/2 pr-2'),
                    Column('account_number', css_class='w-1/2 pl-2'),
                ),
                'account_name',
                Row(
                    Column('pension_number', css_class='w-1/2 pr-2'),
                    Column('tax_id', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'Emergency Contact',
                'emergency_contact_name',
                Row(
                    Column('emergency_contact_phone', css_class='w-1/2 pr-2'),
                    Column('emergency_contact_relationship', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'Medical Information',
                'medical_conditions',
                'allergies',
                Row(
                    Column('doctor_name', css_class='w-1/2 pr-2'),
                    Column('doctor_phone', css_class='w-1/2 pl-2'),
                ),
            ),
            TailwindSubmit('submit', 'Save Staff Member', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        queryset = Staff.objects.filter(email=email)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("A staff member with this email already exists")
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Add phone validation
        return phone


class SubjectAssignmentForm(forms.ModelForm):
    """Form for assigning subjects to staff"""
    
    class Meta:
        model = SubjectAssignment
        fields = ['subject', 'student_class', 'academic_session', 'academic_term', 'periods_per_week', 'is_form_master', 'is_class_teacher']
        widgets = {
            'periods_per_week': forms.NumberInput(attrs={'min': 1, 'max': 40}),
        }
    
    def __init__(self, *args, staff=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['subject'].queryset = Subject.objects.filter(is_active=True)
        self.fields['student_class'].queryset = StudentClassSelector.get_all_classes_queryset()
        self.fields['academic_session'].queryset = AcademicSession.objects.filter(is_current=True)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        layout = [
            Fieldset(
                'Assignment Details',
                Row(
                    Column('subject', css_class='w-1/2 pr-2'),
                    Column('student_class', css_class='w-1/2 pl-2'),
                ),
                Row(
                    Column('academic_session', css_class='w-1/3 pr-2'),
                    Column('academic_term', css_class='w-1/3 px-1'),
                    Column('periods_per_week', css_class='w-1/3 pl-2'),
                ),
                Row(
                    Column('is_form_master', css_class='w-1/2 pr-2'),
                    Column('is_class_teacher', css_class='w-1/2 pl-2'),
                ),
            )
        ]
        
        if staff:
            layout.insert(0, HTML(f"""
                <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                    <p class="text-sm text-blue-800 dark:text-blue-200">
                        <i class="fas fa-info-circle mr-1"></i>
                        Assigning subject to: <strong>{staff.full_name}</strong>
                    </p>
                </div>
            """))
        
        layout.append(TailwindSubmit('submit', 'Assign Subject', css_class='bg-primary-600 hover:bg-primary-700 text-white'))
        
        self.helper.layout = Layout(*layout)


class DutyAssignmentForm(forms.ModelForm):
    """Form for assigning duties to staff"""
    
    class Meta:
        model = DutyAssignment
        fields = ['duty_post', 'academic_session', 'student_class', 'club_name', 'sport_name', 'house_name', 'day_of_week', 'start_time', 'end_time', 'is_active']
        widgets = {
            'day_of_week': forms.Select(choices=[(i, f"Day {i}") for i in range(1, 8)]),
            'start_time': TimeInput(),
            'end_time': TimeInput(),
        }
    
    def __init__(self, *args, staff=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['academic_session'].queryset = AcademicSession.objects.filter(is_current=True)
        self.fields['student_class'].queryset = StudentClassSelector.get_all_classes_queryset()
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        layout = [
            Fieldset(
                'Duty Details',
                Row(
                    Column('duty_post', css_class='w-1/2 pr-2'),
                    Column('academic_session', css_class='w-1/2 pl-2'),
                ),
                Row(
                    Column('club_name', css_class='w-1/3 pr-2'),
                    Column('sport_name', css_class='w-1/3 px-1'),
                    Column('house_name', css_class='w-1/3 pl-2'),
                ),
                'student_class',
                Row(
                    Column('day_of_week', css_class='w-1/3 pr-2'),
                    Column('start_time', css_class='w-1/3 px-1'),
                    Column('end_time', css_class='w-1/3 pl-2'),
                ),
                'is_active',
            )
        ]
        
        if staff:
            layout.insert(0, HTML(f"""
                <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                    <p class="text-sm text-blue-800 dark:text-blue-200">
                        <i class="fas fa-info-circle mr-1"></i>
                        Assigning duty to: <strong>{staff.full_name}</strong>
                    </p>
                </div>
            """))
        
        layout.append(TailwindSubmit('submit', 'Assign Duty', css_class='bg-primary-600 hover:bg-primary-700 text-white'))
        
        self.helper.layout = Layout(*layout)


class LeaveRequestForm(forms.ModelForm):
    """Form for staff leave requests"""
    
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'handover_notes', 'alternative_phone', 'alternative_email']
        widgets = {
            'start_date': DateInput(),
            'end_date': DateInput(),
            'reason': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Reason for leave...'}),
            'handover_notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Who will cover your duties?'}),
        }
    
    def __init__(self, *args, staff=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        layout = [
            Fieldset(
                'Leave Details',
                'leave_type',
                Row(
                    Column('start_date', css_class='w-1/2 pr-2'),
                    Column('end_date', css_class='w-1/2 pl-2'),
                ),
                'reason',
                'handover_notes',
                Row(
                    Column('alternative_phone', css_class='w-1/2 pr-2'),
                    Column('alternative_email', css_class='w-1/2 pl-2'),
                ),
            )
        ]
        
        if staff:
            # Show leave balances
            from .services.leave import LeaveService
            balances = LeaveService.get_leave_balances(staff.id)
            
            balance_html = '<div class="grid grid-cols-3 gap-2 mb-4">'
            for leave_type, balance in balances.items():
                balance_html += f'''
                    <div class="bg-gray-50 dark:bg-gray-800 rounded p-2 text-center">
                        <span class="text-xs text-gray-500 dark:text-gray-400">{leave_type.title()}</span>
                        <span class="text-lg font-bold text-primary-600 dark:text-primary-400">{balance}</span>
                    </div>
                '''
            balance_html += '</div>'
            
            layout.insert(0, HTML(balance_html))
        
        layout.append(TailwindSubmit('submit', 'Submit Leave Request', css_class='bg-primary-600 hover:bg-primary-700 text-white'))
        
        self.helper.layout = Layout(*layout)
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("End date must be after start date")
        
        return cleaned_data


class StaffAttendanceForm(forms.ModelForm):
    """Form for staff attendance"""
    
    class Meta:
        model = StaffAttendance
        fields = ['date', 'check_in_time', 'check_out_time', 'status', 'notes']
        widgets = {
            'date': DateInput(),
            'check_in_time': TimeInput(),
            'check_out_time': TimeInput(),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, staff=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        layout = [
            Fieldset(
                'Attendance Details',
                'date',
                Row(
                    Column('check_in_time', css_class='w-1/2 pr-2'),
                    Column('check_out_time', css_class='w-1/2 pl-2'),
                ),
                'status',
                'notes',
            )
        ]
        
        if staff:
            layout.insert(0, HTML(f"""
                <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                    <p class="text-sm font-medium text-gray-900 dark:text-gray-100">{staff.full_name}</p>
                    <p class="text-xs text-gray-500 dark:text-gray-400">{staff.staff_id}</p>
                </div>
            """))
        
        layout.append(TailwindSubmit('submit', 'Save Attendance', css_class='bg-primary-600 hover:bg-primary-700 text-white'))
        
        self.helper.layout = Layout(*layout)


class PerformanceEvaluationForm(forms.ModelForm):
    """Form for staff performance evaluations"""
    
    class Meta:
        model = PerformanceEvaluation
        fields = [
            'evaluation_period', 'evaluation_date',
            'punctuality', 'job_knowledge', 'quality_of_work',
            'communication', 'teamwork', 'initiative',
            'strengths', 'areas_for_improvement', 'overall_comments',
            'recommendation'
        ]
        widgets = {
            'evaluation_date': DateInput(),
            'strengths': forms.Textarea(attrs={'rows': 3}),
            'areas_for_improvement': forms.Textarea(attrs={'rows': 3}),
            'overall_comments': forms.Textarea(attrs={'rows': 3}),
            'recommendation': forms.Textarea(attrs={'rows': 2}),
        }
        help_texts = {
            'punctuality': "Rate from 1 (Poor) to 5 (Excellent)",
            'job_knowledge': "Rate from 1 (Poor) to 5 (Excellent)",
            'quality_of_work': "Rate from 1 (Poor) to 5 (Excellent)",
            'communication': "Rate from 1 (Poor) to 5 (Excellent)",
            'teamwork': "Rate from 1 (Poor) to 5 (Excellent)",
            'initiative': "Rate from 1 (Poor) to 5 (Excellent)",
        }
    
    def __init__(self, *args, staff=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        layout = [
            Fieldset(
                'Evaluation Period',
                Row(
                    Column('evaluation_period', css_class='w-1/2 pr-2'),
                    Column('evaluation_date', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'Ratings (1-5)',
                Row(
                    Column('punctuality', css_class='w-1/3 pr-2'),
                    Column('job_knowledge', css_class='w-1/3 px-1'),
                    Column('quality_of_work', css_class='w-1/3 pl-2'),
                ),
                Row(
                    Column('communication', css_class='w-1/3 pr-2'),
                    Column('teamwork', css_class='w-1/3 px-1'),
                    Column('initiative', css_class='w-1/3 pl-2'),
                ),
            ),
            Fieldset(
                'Comments',
                'strengths',
                'areas_for_improvement',
                'overall_comments',
                'recommendation',
            ),
        ]
        
        if staff:
            layout.insert(0, HTML(f"""
                <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                    <p class="text-sm text-blue-800 dark:text-blue-200">
                        <i class="fas fa-info-circle mr-1"></i>
                        Evaluating: <strong>{staff.full_name}</strong>
                    </p>
                </div>
            """))
        
        layout.append(TailwindSubmit('submit', 'Save Evaluation', css_class='bg-primary-600 hover:bg-primary-700 text-white'))
        
        self.helper.layout = Layout(*layout)
"""
Attendance Forms - ALL forms for attendance app
Using crispy-tailwind for consistent styling
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Fieldset
from crispy_tailwind.layout import Submit as TailwindSubmit
from .models import AttendanceRegister, AttendanceRecord, QRCode
from .constants import AttendanceStatus, SessionType, MarkingMethod
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector


class DateInput(forms.DateInput):
    input_type = 'date'


class TimeInput(forms.TimeInput):
    input_type = 'time'


class AttendanceRegisterForm(forms.ModelForm):
    """Form for creating attendance registers"""
    
    class Meta:
        model = AttendanceRegister
        fields = ['student_class', 'date', 'session_type', 'academic_session', 'academic_term']
        widgets = {
            'date': DateInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['student_class'].queryset = StudentClassSelector.get_all_classes_queryset()
        self.fields['academic_session'].queryset = AcademicSession.objects.filter(is_current=True)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Row(
                Column('student_class', css_class='w-1/2 pr-2'),
                Column('session_type', css_class='w-1/2 pl-2'),
            ),
            Row(
                Column('date', css_class='w-1/2 pr-2'),
                Column('academic_session', css_class='w-1/2 pl-2'),
            ),
            'academic_term',
            HTML("""
                <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                    <p class="text-sm text-blue-800 dark:text-blue-200">
                        <i class="fas fa-info-circle mr-1"></i>
                        If a register already exists for this class and date, it will be reused.
                    </p>
                </div>
            """),
            TailwindSubmit('submit', 'Create Register', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )


class AttendanceRecordForm(forms.ModelForm):
    """Form for individual attendance records"""
    
    class Meta:
        model = AttendanceRecord
        fields = ['status', 'check_in_time', 'remarks']
        widgets = {
            'check_in_time': TimeInput(),
            'remarks': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional remarks...'}),
        }
    
    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        layout = [
            Fieldset(
                'Attendance Details',
                Row(
                    Column('status', css_class='w-1/2 pr-2'),
                    Column('check_in_time', css_class='w-1/2 pl-2'),
                ),
                'remarks',
            )
        ]
        
        if student:
            layout.insert(0, HTML(f"""
                <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                    <p class="text-sm font-medium text-gray-900 dark:text-gray-100">{student.full_name}</p>
                    <p class="text-xs text-gray-500 dark:text-gray-400">{student.admission_number}</p>
                </div>
            """))
        
        layout.append(TailwindSubmit('submit', 'Save Attendance', css_class='bg-primary-600 hover:bg-primary-700 text-white'))
        
        self.helper.layout = Layout(*layout)


class BulkAttendanceForm(forms.Form):
    """Form for bulk attendance marking"""
    
    bulk_status = forms.ChoiceField(
        choices=AttendanceStatus.CHOICES,
        label="Mark all as"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            'bulk_status',
            HTML("""
                <p class="text-xs text-yellow-600 dark:text-yellow-400">
                    <i class="fas fa-exclamation-triangle mr-1"></i>
                    This will mark ALL students in this register with the selected status.
                </p>
            """),
            TailwindSubmit('submit', 'Apply to All', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )


class AttendanceSearchForm(forms.Form):
    """Form for searching attendance records"""
    
    start_date = forms.DateField(
        widget=DateInput,
        required=False,
        label="Start Date"
    )
    
    end_date = forms.DateField(
        widget=DateInput,
        required=False,
        label="End Date"
    )
    
    student_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput,
        label="Student ID"
    )
    
    class_id = forms.ModelChoiceField(
        queryset=StudentClassSelector.get_all_classes_queryset(),
        required=False,
        label="Class",
        empty_label="All Classes"
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + list(AttendanceStatus.CHOICES),
        required=False,
        label="Status"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Row(
                Column('start_date', css_class='w-1/2 pr-2'),
                Column('end_date', css_class='w-1/2 pl-2'),
            ),
            Row(
                Column('class_id', css_class='w-1/2 pr-2'),
                Column('status', css_class='w-1/2 pl-2'),
            ),
            TailwindSubmit('submit', 'Search', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )


class QRCodeForm(forms.ModelForm):
    """Form for generating QR codes"""
    
    class Meta:
        model = QRCode
        fields = ['student_id', 'student_name']
        widgets = {
            'student_id': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'student_name': forms.TextInput(attrs={'readonly': 'readonly'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Fieldset(
                'Student Information',
                Row(
                    Column('student_id', css_class='w-1/3 pr-2'),
                    Column('student_name', css_class='w-2/3 pl-2'),
                ),
            ),
            HTML("""
                <div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
                    <p class="text-sm text-yellow-800 dark:text-yellow-200">
                        <i class="fas fa-exclamation-triangle mr-1"></i>
                        This will generate a new QR code for the student. Existing QR codes will remain valid.
                    </p>
                </div>
            """),
            TailwindSubmit('submit', 'Generate QR Code', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
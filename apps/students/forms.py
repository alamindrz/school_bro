"""
Students Forms - ALL forms for students app
Using crispy-tailwind for consistent styling
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_tailwind.layout import Submit as TailwindSubmit
from .models import Student, Guardian, SavedStudentSearch
from .validators import StudentValidator, GuardianValidator

from .constants import StudentStatus
import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional


from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Fieldset, Div
from crispy_tailwind.layout import Submit as TailwindSubmit

from apps.corecode.models import StudentClass
from apps.corecode.selectors import StudentClassSelector
from .models import Student
from .validators import StudentValidator
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div, Field
from crispy_tailwind.layout import Submit as TailwindSubmit

from apps.corecode.models import StudentClass, AcademicSession
from apps.students.constants import StudentStatus



class BulkStudentImportForm(forms.Form):
    """
    Bulk Student Import Form with Crispy Forms layout
    Handles CSV validation, preview, and import options
    """
    
    # File upload field
    csv_file = forms.FileField(
        label=_("CSV File"),
        help_text=_("Upload a CSV file with student data. Download the template for the correct format."),
        validators=[FileExtensionValidator(['csv'])],
        widget=forms.FileInput(attrs={
            'accept': '.csv',
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100 dark:file:bg-primary-900 dark:file:text-primary-300'
        })
    )
    
    # Import options
    create_user_accounts = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Create portal user accounts"),
        help_text=_("Automatically create Django user accounts for students with email addresses"),
        widget=forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-300 focus:ring focus:ring-primary-200 focus:ring-opacity-50'})
    )
    
    send_welcome_emails = forms.BooleanField(
        required=False,
        initial=False,
        label=_("Send welcome emails"),
        help_text=_("Send login credentials via email to new students"),
        widget=forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-300 focus:ring focus:ring-primary-200 focus:ring-opacity-50'})
    )
    
    update_existing = forms.BooleanField(
        required=False,
        initial=False,
        label=_("Update existing records"),
        help_text=_("If student already exists, update their information instead of skipping"),
        widget=forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-300 focus:ring focus:ring-primary-200 focus:ring-opacity-50'})
    )
    
    batch_size = forms.IntegerField(
        required=False,
        initial=100,
        min_value=10,
        max_value=1000,
        label=_("Batch Size"),
        help_text=_("Number of records to process in each batch"),
        widget=forms.NumberInput(attrs={'class': 'block w-32 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'})
    )
    
    # Class filter (optional)
    class_filter = forms.ModelChoiceField(
        queryset=StudentClass.objects.filter(is_active=True),
        required=False,
        label=_("Restrict to Class"),
        help_text=_("If selected, only import students for this class"),
        widget=forms.Select(attrs={'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'})
    )
    
    # Hidden field for preview data
    preview_data = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    # Required CSV columns
    REQUIRED_COLUMNS = [
        'first_name', 'last_name', 'gender', 'date_of_birth', 'current_class'
    ]
    
    # Optional CSV columns
    OPTIONAL_COLUMNS = [
        'middle_name', 'email', 'phone', 'address', 'city', 
        'state_of_origin', 'nationality', 'blood_group', 
        'medical_notes', 'has_special_needs'
    ]
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Initialize Crispy Forms helper
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.form_class = 'space-y-6'
        self.helper.attrs = {
            'x-data': 'bulkImportForm()',
            'x-init': 'initForm()'
        }
        
        # Build the layout
        self.helper.layout = Layout(
            # Upload Section
            Fieldset(
                _('1. Upload CSV File'),
                Div(
                    HTML("""
                        <div class="flex items-center justify-center w-full">
                            <label for="id_csv_file" class="flex flex-col items-center justify-center w-full h-64 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:hover:bg-gray-700">
                                <div class="flex flex-col items-center justify-center pt-5 pb-6">
                                    <i class="fas fa-cloud-upload-alt text-4xl text-gray-400 mb-3"></i>
                                    <p class="mb-2 text-sm text-gray-500 dark:text-gray-400">
                                        <span class="font-semibold">Click to upload</span> or drag and drop
                                    </p>
                                    <p class="text-xs text-gray-500 dark:text-gray-400">CSV files only (max. 10MB)</p>
                                </div>
                            </label>
                        </div>
                    """),
                    'csv_file',
                    css_class='space-y-4'
                ),
                css_class='bg-white dark:bg-gray-900 p-6 rounded-lg border border-gray-200 dark:border-gray-700'
            ),
            
            # Options Section
            Fieldset(
                _('2. Import Options'),
                Row(
                    Column('create_user_accounts', css_class='md:w-1/3'),
                    Column('send_welcome_emails', css_class='md:w-1/3'),
                    Column('update_existing', css_class='md:w-1/3'),
                ),
                Row(
                    Column('batch_size', css_class='md:w-1/4'),
                    Column('class_filter', css_class='md:w-3/4'),
                ),
                css_class='bg-white dark:bg-gray-900 p-6 rounded-lg border border-gray-200 dark:border-gray-700'
            ),
            
            # Action Buttons
            Div(
                Div(
                    HTML("""
                        <button type="button" 
                                @click="previewImport()"
                                class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                                :disabled="isUploading">
                            <i class="fas fa-eye mr-2" :class="{'fa-spinner fa-spin': isUploading}"></i>
                            <span x-text="isUploading ? 'Previewing...' : 'Preview Data'"></span>
                        </button>
                    """),
                    HTML("""
                        <a href="{% url 'students:download_template' %}" 
                           class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
                            <i class="fas fa-download mr-2"></i>
                            Download Template
                        </a>
                    """),
                    css_class='flex space-x-3'
                ),
                css_class='flex justify-end'
            ),
            
            # Preview Section (hidden initially)
            Div(
                HTML("""
                    <div x-show="showPreview" 
                         x-transition:enter="transition ease-out duration-300"
                         x-transition:enter-start="opacity-0 transform scale-95"
                         x-transition:enter-end="opacity-100 transform scale-100"
                         id="preview-container">
                        <!-- Preview content will be loaded here via HTMX -->
                    </div>
                """),
            ),
            
            # Hidden preview data field
            'preview_data',
        )
    
    def clean_csv_file(self):
        """Validate CSV file structure and content."""
        csv_file = self.cleaned_data.get('csv_file')
        
        if not csv_file:
            raise forms.ValidationError(_("Please select a CSV file to upload."))
        
        # Check file size (10MB limit)
        if csv_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError(_("File size must be less than 10MB."))
        
        try:
            # Read and decode CSV
            decoded_file = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.reader(io_string)
            
            # Read and validate headers
            try:
                headers = next(reader)
            except StopIteration:
                raise forms.ValidationError(_("CSV file is empty."))
            
            # Clean headers
            headers = [h.strip().lower().replace(' ', '_') for h in headers]
            
            # Check for required columns
            missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in headers]
            if missing_columns:
                raise forms.ValidationError(
                    _("Missing required columns: %(columns)s") % {
                        'columns': ', '.join(missing_columns)
                    }
                )
            
            # Count rows
            row_count = sum(1 for _ in reader)
            if row_count == 0:
                raise forms.ValidationError(_("The CSV file contains no data rows."))
            
            if row_count > 5000:
                raise forms.ValidationError(_("File contains too many rows. Maximum is 5000."))
            
            # Reset file pointer
            csv_file.seek(0)
            
        except UnicodeDecodeError:
            raise forms.ValidationError(_("Invalid file encoding. Please save your CSV as UTF-8."))
        except Exception as e:
            raise forms.ValidationError(_("Error reading CSV file: %(error)s") % {'error': str(e)})
        
        return csv_file
    
    def get_preview_data(self) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Generate preview data from uploaded CSV.
        Returns (preview_data, statistics)
        """
        csv_file = self.cleaned_data.get('csv_file')
        
        if not csv_file:
            raise ValidationError("No CSV file provided")
        
        preview_data = []
        stats = {
            'total': 0,
            'valid': 0,
            'invalid': 0,
            'new': 0,
            'updates': 0,
            'skipped': 0
        }
        
        # Reset file pointer
        csv_file.seek(0)
        decoded_file = csv_file.read().decode('utf-8-sig')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        for row_num, row in enumerate(reader, start=2):
            stats['total'] += 1
            
            # Clean and validate row
            cleaned_data = self._clean_row_data(row)
            is_valid, error, validated_data = self._validate_row(cleaned_data)
            
            # Check if exists
            exists = self._check_student_exists(validated_data) if is_valid else False
            
            # Determine action
            if not is_valid:
                action = 'skip'
                stats['invalid'] += 1
            elif exists and not self.cleaned_data.get('update_existing'):
                action = 'skip'
                stats['skipped'] += 1
            elif exists:
                action = 'update'
                stats['updates'] += 1
                stats['valid'] += 1
            else:
                action = 'create'
                stats['new'] += 1
                stats['valid'] += 1
            
            preview_data.append({
                'row_number': row_num,
                'data': validated_data,
                'valid': is_valid,
                'error': error if not is_valid else None,
                'exists': exists,
                'action': action
            })
        
        return preview_data, stats
    
    def _clean_row_data(self, row: Dict) -> Dict:
        """Clean and normalize row data."""
        cleaned = {}
        for key, value in row.items():
            clean_key = key.strip().lower().replace(' ', '_')
            if value and value.strip():
                cleaned[clean_key] = value.strip()
            else:
                cleaned[clean_key] = None
        return cleaned
    
    def _validate_row(self, row: Dict) -> Tuple[bool, str, Dict]:
        """Validate a single row of data."""
        validated = {}
        errors = []
        
        # Check required fields
        for field in self.REQUIRED_COLUMNS:
            value = row.get(field)
            if not value:
                errors.append(f"Missing required field: {field}")
            else:
                validated[field] = value
        
        if errors:
            return False, '; '.join(errors), validated
        
        # Validate gender
        gender = row.get('gender', '').upper()
        if gender not in ['M', 'F']:
            errors.append(f"Invalid gender '{gender}'. Must be M or F")
        else:
            validated['gender'] = gender
        
        # Validate date of birth
        dob = row.get('date_of_birth')
        try:
            dob_date = datetime.strptime(dob, '%Y-%m-%d').date()
            age = (datetime.now().date() - dob_date).days // 365
            if age < 2 or age > 25:
                errors.append(f"Age {age} is outside acceptable range (2-25 years)")
            else:
                validated['date_of_birth'] = dob_date.isoformat()
        except ValueError:
            errors.append(f"Invalid date format '{dob}'. Use YYYY-MM-DD")
        
        # Validate class
        class_name = row.get('current_class')
        student_class = StudentClassSelector.get_by_name(class_name)
        if not student_class:
            errors.append(f"Class '{class_name}' not found")
        else:
            validated['current_class_id'] = student_class.id
            validated['current_class_name'] = student_class.display_name
        
        # Class filter check
        class_filter = self.cleaned_data.get('class_filter')
        if class_filter and validated.get('current_class_id') != class_filter.id:
            errors.append(f"Class '{class_name}' does not match selected filter")
        
        # Validate email if provided
        email = row.get('email')
        if email:
            try:
                StudentValidator.validate_email(email)
                validated['email'] = email
            except Exception as e:
                errors.append(f"Email: {str(e)}")
        
        # Validate phone if provided
        phone = row.get('phone')
        if phone:
            try:
                StudentValidator.validate_phone(phone)
                validated['phone'] = phone
            except Exception as e:
                errors.append(f"Phone: {str(e)}")
        
        # Add other fields
        for field in self.OPTIONAL_COLUMNS:
            if field not in ['email', 'phone'] and row.get(field):
                validated[field] = row.get(field)
        
        if errors:
            return False, '; '.join(errors), validated
        
        return True, "", validated
    
    def _check_student_exists(self, data: Dict) -> bool:
        """Check if student already exists."""
        email = data.get('email')
        if email:
            return Student.objects.filter(email=email).exists()
        
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        if first_name and last_name:
            return Student.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            ).exists()
        
        return False
    
    def get_template_context(self) -> Dict:
        """Get template context data."""
        return {
            'required_columns': self.REQUIRED_COLUMNS,
            'optional_columns': self.OPTIONAL_COLUMNS,
            'max_rows': 5000,
            'batch_sizes': [10, 50, 100, 200, 500, 1000],
            'column_descriptions': {
                'first_name': 'Student\'s first name',
                'last_name': 'Student\'s last name',
                'middle_name': 'Student\'s middle name (optional)',
                'gender': 'M or F',
                'date_of_birth': 'YYYY-MM-DD',
                'current_class': 'Class name (e.g., SS1, JSS2, Primary 5)',
                'email': 'Valid email address (required for portal access)',
                'phone': 'Nigerian phone number (e.g., 08012345678)',
                'address': 'Home address',
                'city': 'City of residence',
                'state_of_origin': 'State of origin',
                'nationality': 'Nationality (defaults to Nigerian)',
                'blood_group': 'A+, A-, B+, B-, O+, O-, AB+, AB-',
                'medical_notes': 'Any medical conditions',
                'has_special_needs': 'TRUE or FALSE',
            }
        }


class StudentStatusForm(forms.ModelForm):
    """Form to handle student lifecycle transitions"""
    
    class Meta:
        model = Student
        fields = ['status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.status:
            current_status = self.instance.status
            # Get valid next steps from your constants
            valid_next = StudentStatus.VALID_TRANSITIONS.get(current_status, [])
            
            # Filter the choices so the UI only shows allowed transitions
            self.fields['status'].choices = [
                (c, label) for c, label in StudentStatus.CHOICES 
                if c == current_status or c in valid_next
            ]

class DateInput(forms.DateInput):
    input_type = 'date'


class StudentBaseForm(forms.ModelForm):
    """Base form with common validation logic"""
    
    confirm_email = forms.EmailField(
        required=True,
        label="Confirm Email",
        widget=forms.EmailInput(attrs={'placeholder': 'Re-enter email address'})
    )
    
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'middle_name', 'gender', 'date_of_birth',
            'email', 'phone', 'address', 'city', 'state_of_origin',
            'current_class', 'blood_group', 'medical_notes',
            'has_special_needs', 'special_needs_notes'
        ]
        widgets = {
            'date_of_birth': DateInput(),
            'medical_notes': forms.Textarea(attrs={'rows': 3}),
            'special_needs_notes': forms.Textarea(attrs={'rows': 2}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Make email and phone required
        self.fields['email'].required = True
        self.fields['phone'].required = True
        
        # Add help texts
        self.fields['phone'].help_text = "Nigerian format: 08012345678"
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        confirm_email = self.cleaned_data.get('confirm_email')
        
        if email and confirm_email and email != confirm_email:
            raise forms.ValidationError("Email addresses do not match")
        
        # Validate format
        StudentValidator.validate_email(email)
        
        # Check uniqueness
        queryset = Student.objects.filter(email=email)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("A student with this email already exists")
        
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        StudentValidator.validate_phone(phone)
        return phone
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        student_class = self.cleaned_data.get('current_class')
        
        if dob and student_class:
            age = (date.today() - dob).days // 365
            StudentValidator.validate_class_for_age(student_class.name, age)
        
        return dob


class StudentCreateForm(StudentBaseForm):
    """Form for creating new students"""
    
    create_user_account = forms.BooleanField(
        required=False,
        initial=True,
        label="Create portal user account",
        help_text="Create Django user account for student login"
    )
    
    send_welcome_email = forms.BooleanField(
        required=False,
        initial=True,
        label="Send welcome email",
        help_text="Send login credentials via email"
    )
    
    class Meta(StudentBaseForm.Meta):
        fields = StudentBaseForm.Meta.fields + ['admission_number']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
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
                    Column('gender', css_class='w-1/2 pr-2'),
                    Column('date_of_birth', css_class='w-1/2 pl-2'),
                ),
                Row(
                    Column('blood_group', css_class='w-1/2 pr-2'),
                    Column('current_class', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'Contact Information',
                Row(
                    Column('email', css_class='w-1/2 pr-2'),
                    Column('confirm_email', css_class='w-1/2 pl-2'),
                ),
                Row(
                    Column('phone', css_class='w-1/2 pr-2'),
                    Column('city', css_class='w-1/2 pl-2'),
                ),
                'address',
                'state_of_origin',
            ),
            Fieldset(
                'Medical Information',
                'medical_notes',
                Row(
                    Column('has_special_needs', css_class='w-1/2'),
                    Column('special_needs_notes', css_class='w-1/2'),
                ),
            ),
            Fieldset(
                'Portal Access',
                'create_user_account',
                'send_welcome_email',
            ),
            TailwindSubmit('submit', 'Create Student', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
        
        # Hide admission_number field - auto-generated
        self.fields['admission_number'].widget = forms.HiddenInput()
        self.fields['admission_number'].required = False


class StudentUpdateForm(StudentBaseForm):
    """Form for updating existing students"""
    
    class Meta(StudentBaseForm.Meta):
        fields = StudentBaseForm.Meta.fields
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
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
                    Column('gender', css_class='w-1/2 pr-2'),
                    Column('date_of_birth', css_class='w-1/2 pl-2'),
                ),
                Row(
                    Column('blood_group', css_class='w-1/2 pr-2'),
                    Column('current_class', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'Contact Information',
                Row(
                    Column('email', css_class='w-1/2 pr-2'),
                    Column('confirm_email', css_class='w-1/2 pl-2'),
                ),
                Row(
                    Column('phone', css_class='w-1/2 pr-2'),
                    Column('city', css_class='w-1/2 pl-2'),
                ),
                'address',
                'state_of_origin',
            ),
            Fieldset(
                'Medical Information',
                'medical_notes',
                Row(
                    Column('has_special_needs', css_class='w-1/2'),
                    Column('special_needs_notes', css_class='w-1/2'),
                ),
            ),
            HTML("""
                <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                    <p class="text-sm text-gray-600 dark:text-gray-400">
                        <i class="fas fa-info-circle mr-1"></i>
                        Admission Number: <strong>{{ object.admission_number }}</strong> (cannot be changed)
                    </p>
                </div>
            """),
            TailwindSubmit('submit', 'Update Student', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )


class GuardianForm(forms.ModelForm):
    """Form for guardians"""
    
    create_portal_account = forms.BooleanField(
        required=False,
        initial=False,
        label="Create parent portal account",
        help_text="Create login credentials for parent"
    )
    
    class Meta:
        model = Guardian
        fields = [
            'first_name', 'last_name', 'relationship',
            'email', 'phone', 'alternate_phone', 'address',
            'occupation', 'employer', 'is_primary', 'is_emergency_contact'
        ]
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='w-1/3 pr-2'),
                Column('last_name', css_class='w-1/3 px-1'),
                Column('relationship', css_class='w-1/3 pl-2'),
            ),
            Row(
                Column('email', css_class='w-1/2 pr-2'),
                Column('phone', css_class='w-1/2 pl-2'),
            ),
            'alternate_phone',
            'address',
            Row(
                Column('occupation', css_class='w-1/2 pr-2'),
                Column('employer', css_class='w-1/2 pl-2'),
            ),
            Row(
                Column('is_primary', css_class='w-1/2'),
                Column('is_emergency_contact', css_class='w-1/2'),
            ),
            'create_portal_account',
            TailwindSubmit('submit', 'Save Guardian', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        GuardianValidator.validate_phone(phone)
        return phone
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            GuardianValidator.validate_email(email)
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.student:
            # Check guardian limit
            current_count = self.student.guardians.count()
            GuardianValidator.validate_guardian_limit(current_count)
            
            # Check primary guardian limit
            is_primary = cleaned_data.get('is_primary', False)
            current_primary = self.student.guardians.filter(is_primary=True).count()
            if self.instance.pk and self.instance.is_primary:
                current_primary -= 1
            GuardianValidator.validate_primary_guardian_count(current_primary, is_primary)
        
        return cleaned_data
        

class StudentSearchForm(forms.Form):
    """
    Advanced student search form with filtering capabilities.
    
    Features:
    - Text search (name, admission number, email)
    - Class filter
    - Status filter
    - Gender filter
    - Session filter
    - Date range filters
    - Export options
    - Saved searches
    """
    
    # Text search
    q = forms.CharField(
        required=False,
        label=_("Search"),
        help_text=_("Search by name, admission number, email, or phone"),
        widget=forms.TextInput(attrs={
            'placeholder': _('Search students...'),
            'class': 'block w-full px-4 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    
    # Class filter
    class_id = forms.ModelChoiceField(
        queryset=StudentClass.objects.filter(is_active=True),
        required=False,
        label=_("Class"),
        empty_label=_("All Classes"),
        widget=forms.Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    
    # Status filter
    status = forms.ChoiceField(
        choices=[('', _('All Status'))] + StudentStatus.CHOICES,
        required=False,
        label=_("Status"),
        widget=forms.Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    
    # Gender filter
    gender = forms.ChoiceField(
        choices=[
            ('', _('All Genders')),
            ('M', _('Male')),
            ('F', _('Female')),
        ],
        required=False,
        label=_("Gender"),
        widget=forms.Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    
    # Session filter
    session_id = forms.ModelChoiceField(
        queryset=AcademicSession.objects.all().order_by('-start_date'),
        required=False,
        label=_("Enrollment Session"),
        empty_label=_("All Sessions"),
        widget=forms.Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    
    # Date range filters
    enrollment_start = forms.DateField(
        required=False,
        label=_("Enrollment From"),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    
    enrollment_end = forms.DateField(
        required=False,
        label=_("Enrollment To"),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    
    date_of_birth_start = forms.DateField(
        required=False,
        label=_("Birth Date From"),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    
    date_of_birth_end = forms.DateField(
        required=False,
        label=_("Birth Date To"),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    
    # Sorting options
    SORT_CHOICES = [
        ('name_asc', _('Name (A-Z)')),
        ('name_desc', _('Name (Z-A)')),
        ('admission_asc', _('Admission Number (A-Z)')),
        ('admission_desc', _('Admission Number (Z-A)')),
        ('date_enrolled_desc', _('Recently Enrolled')),
        ('date_enrolled_asc', _('Oldest Enrolled')),
        ('date_of_birth_desc', _('Youngest First')),
        ('date_of_birth_asc', _('Oldest First')),
    ]
    
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='name_asc',
        label=_("Sort By"),
        widget=forms.Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    
    # Results per page
    per_page = forms.IntegerField(
        required=False,
        initial=25,
        min_value=10,
        max_value=100,
        label=_("Results Per Page"),
        widget=forms.NumberInput(attrs={
            'class': 'block w-24 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    
    # Export options (hidden by default, shown when export button clicked)
    export_format = forms.ChoiceField(
        choices=[
            ('', _('No Export')),
            ('csv', _('CSV')),
            ('excel', _('Excel')),
            ('pdf', _('PDF')),
        ],
        required=False,
        label=_("Export Format"),
        widget=forms.Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    
    export_columns = forms.MultipleChoiceField(
        choices=[
            ('admission_number', _('Admission Number')),
            ('full_name', _('Full Name')),
            ('current_class', _('Class')),
            ('gender', _('Gender')),
            ('date_of_birth', _('Date of Birth')),
            ('age', _('Age')),
            ('email', _('Email')),
            ('phone', _('Phone')),
            ('address', _('Address')),
            ('city', _('City')),
            ('state_of_origin', _('State')),
            ('enrollment_date', _('Enrollment Date')),
            ('status', _('Status')),
            ('guardians', _('Guardians')),
        ],
        required=False,
        label=_("Export Columns"),
        widget=forms.SelectMultiple(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
            'size': '8'
        })
    )
    
    # Saved searches
    saved_search_name = forms.CharField(
        required=False,
        label=_("Save Search As"),
        widget=forms.TextInput(attrs={
            'placeholder': _('Enter a name for this search...'),
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Initialize Crispy Forms helper
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'space-y-4'
        self.helper.attrs = {
            'x-data': 'studentSearchForm()',
            'x-init': 'initForm()',
            'id': 'student-search-form'
        }
        
        # Build the layout
        self.helper.layout = Layout(
            # Basic Search Section
            Div(
                HTML("""
                    <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                        <i class="fas fa-search mr-2 text-primary-500"></i> Basic Search
                    </h3>
                """),
                Row(
                    Column('q', css_class='md:col-span-2'),
                    Column('class_id', css_class='md:col-span-1'),
                    Column('status', css_class='md:col-span-1'),
                ),
                Row(
                    Column('gender', css_class='md:col-span-1'),
                    Column('session_id', css_class='md:col-span-1'),
                    Column('sort_by', css_class='md:col-span-1'),
                    Column('per_page', css_class='md:col-span-1'),
                ),
                css_class='bg-white dark:bg-gray-900 p-6 rounded-lg border border-gray-200 dark:border-gray-700'
            ),
            
            # Advanced Filters (collapsible)
            Div(
                HTML("""
                    <div @click="showAdvanced = !showAdvanced" 
                         class="flex items-center justify-between cursor-pointer mb-4">
                        <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">
                            <i class="fas fa-filter mr-2 text-primary-500"></i> Advanced Filters
                        </h3>
                        <i class="fas fa-chevron-down transition-transform duration-300"
                           :class="{'rotate-180': showAdvanced}"></i>
                    </div>
                """),
                Div(
                    Row(
                        Column('enrollment_start', css_class='md:col-span-1'),
                        Column('enrollment_end', css_class='md:col-span-1'),
                        Column('date_of_birth_start', css_class='md:col-span-1'),
                        Column('date_of_birth_end', css_class='md:col-span-1'),
                    ),
                    x_show="showAdvanced",
                    x_transition="transition ease-in-out duration-300",
                    css_class='space-y-4'
                ),
                css_class='bg-white dark:bg-gray-900 p-6 rounded-lg border border-gray-200 dark:border-gray-700'
            ),
            
            # Export Options (collapsible, shown when export button clicked)
            Div(
                HTML("""
                    <div @click="showExport = !showExport" 
                         class="flex items-center justify-between cursor-pointer mb-4">
                        <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">
                            <i class="fas fa-download mr-2 text-primary-500"></i> Export Options
                        </h3>
                        <i class="fas fa-chevron-down transition-transform duration-300"
                           :class="{'rotate-180': showExport}"></i>
                    </div>
                """),
                Div(
                    Row(
                        Column('export_format', css_class='md:col-span-1'),
                        Column('export_columns', css_class='md:col-span-3'),
                    ),
                    HTML("""
                        <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
                            <i class="fas fa-info-circle mr-1"></i>
                            Hold Ctrl/Cmd to select multiple columns
                        </p>
                    """),
                    x_show="showExport",
                    x_transition="transition ease-in-out duration-300",
                    css_class='space-y-4'
                ),
                css_class='bg-white dark:bg-gray-900 p-6 rounded-lg border border-gray-200 dark:border-gray-700'
            ),
            
            # Saved Searches (for authenticated users)
            Div(
                HTML("""
                    <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                        <i class="fas fa-bookmark mr-2 text-primary-500"></i> Saved Searches
                    </h3>
                """),
                Row(
                    Column('saved_search_name', css_class='md:col-span-2'),
                    Column(
                        HTML("""
                            <button type="button"
                                    @click="saveSearch()"
                                    class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
                                <i class="fas fa-save mr-2"></i> Save Search
                            </button>
                        """),
                        css_class='md:col-span-1 flex items-end'
                    ),
                ),
                Div(
                    HTML("""
                        <div class="mt-4" x-show="savedSearches.length > 0">
                            <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Your Saved Searches:</h4>
                            <div class="flex flex-wrap gap-2">
                                <template x-for="search in savedSearches" :key="search.id">
                                    <button type="button"
                                            @click="loadSavedSearch(search)"
                                            class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">
                                        <i class="fas fa-bookmark mr-1"></i>
                                        <span x-text="search.name"></span>
                                    </button>
                                </template>
                            </div>
                        </div>
                    """),
                    x_show="showAdvanced"
                ),
                css_class='bg-white dark:bg-gray-900 p-6 rounded-lg border border-gray-200 dark:border-gray-700'
            ),
            
            # Action Buttons
            Div(
                Div(
                    HTML("""
                        <button type="submit"
                                class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
                            <i class="fas fa-search mr-2"></i> Search
                        </button>
                        <button type="button"
                                @click="clearFilters()"
                                class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
                            <i class="fas fa-times mr-2"></i> Clear
                        </button>
                        <button type="button"
                                @click="exportResults()"
                                x-show="showExport"
                                class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500">
                            <i class="fas fa-download mr-2"></i> Export
                        </button>
                    """),
                    css_class='flex space-x-3'
                ),
                css_class='flex justify-end'
            ),
        )
    
    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        
        # Validate date ranges
        enrollment_start = cleaned_data.get('enrollment_start')
        enrollment_end = cleaned_data.get('enrollment_end')
        
        if enrollment_start and enrollment_end and enrollment_start > enrollment_end:
            self.add_error('enrollment_end', _('End date must be after start date'))
        
        dob_start = cleaned_data.get('date_of_birth_start')
        dob_end = cleaned_data.get('date_of_birth_end')
        
        if dob_start and dob_end and dob_start > dob_end:
            self.add_error('date_of_birth_end', _('End date must be after start date'))
        
        return cleaned_data
    
    def get_search_params(self) -> dict:
        """
        Get cleaned search parameters for query building.
        Returns a dictionary suitable for StudentSelector.
        """
        cleaned = self.cleaned_data
        
        params = {
            'search': cleaned.get('q'),
            'class_id': cleaned.get('class_id').id if cleaned.get('class_id') else None,
            'status': cleaned.get('status'),
            'gender': cleaned.get('gender'),
            'session_id': cleaned.get('session_id').id if cleaned.get('session_id') else None,
            'enrollment_start': cleaned.get('enrollment_start'),
            'enrollment_end': cleaned.get('enrollment_end'),
            'dob_start': cleaned.get('date_of_birth_start'),
            'dob_end': cleaned.get('date_of_birth_end'),
            'sort_by': cleaned.get('sort_by', 'name_asc'),
            'limit': cleaned.get('per_page', 25),
        }
        
        return params
    
    def get_export_filename(self) -> str:
        """Generate export filename based on search criteria."""
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Get basic criteria for filename
        class_name = self.cleaned_data.get('class_id')
        status = self.cleaned_data.get('status')
        
        parts = ['students']
        if class_name:
            parts.append(class_name.display_name.replace(' ', '_'))
        if status:
            parts.append(status)
        parts.append(timestamp)
        
        return '_'.join(parts)
    
    def get_template_context(self) -> dict:
        """Get template context for rendering."""
        return {
            'total_filters': len([v for v in self.cleaned_data.values() if v]),
            'has_active_filters': any(self.cleaned_data.values()),
            'export_formats': ['csv', 'excel', 'pdf'],
            'default_columns': [
                'admission_number', 'full_name', 'current_class', 'status'
            ],
            'sort_options': self.SORT_CHOICES,
        }



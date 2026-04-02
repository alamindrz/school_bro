"""
Admissions Forms - ALL forms for admissions app
Using crispy-tailwind for consistent styling
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Fieldset
from crispy_tailwind.layout import Submit as TailwindSubmit
from .models import Application
from .validators import ApplicationValidator
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector


class DateInput(forms.DateInput):
    input_type = 'date'


class PublicApplicationForm(forms.ModelForm):
    """Public-facing application form"""
    
    terms_agreed = forms.BooleanField(
        required=True,
        label="I confirm that the information provided is accurate",
        error_messages={'required': "You must agree to the terms to continue"}
    )
    
    class Meta:
        model = Application
        fields = [
            'first_name', 'last_name', 'middle_name', 'gender', 'date_of_birth',
            'email', 'phone', 'alternate_phone', 'address', 'city', 'state_of_origin',
            'nationality', 'applying_for_class', 'application_type',
            'previous_school', 'previous_class',
            'guardian_first_name', 'guardian_last_name', 'guardian_relationship',
            'guardian_phone', 'guardian_email', 'guardian_address', 'guardian_occupation',
        ]
        widgets = {
            'date_of_birth': DateInput(),
            'address': forms.Textarea(attrs={'rows': 2}),
            'guardian_address': forms.Textarea(attrs={'rows': 2}),
        }
        help_texts = {
            'phone': "Nigerian format: 08012345678",
            'guardian_phone': "Nigerian format: 08012345678",
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Limit class choices to active classes
        self.fields['applying_for_class'].queryset = StudentClassSelector.get_all_classes_queryset()
        
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
                    Column('nationality', css_class='w-1/2 pr-2'),
                    Column('state_of_origin', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'Contact Information',
                Row(
                    Column('email', css_class='w-1/2 pr-2'),
                    Column('phone', css_class='w-1/2 pl-2'),
                ),
                'alternate_phone',
                'address',
                'city',
            ),
            Fieldset(
                'Academic Information',
                Row(
                    Column('applying_for_class', css_class='w-1/2 pr-2'),
                    Column('application_type', css_class='w-1/2 pl-2'),
                ),
                Row(
                    Column('previous_school', css_class='w-1/2 pr-2'),
                    Column('previous_class', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'Guardian Information',
                Row(
                    Column('guardian_first_name', css_class='w-1/3 pr-2'),
                    Column('guardian_last_name', css_class='w-1/3 px-1'),
                    Column('guardian_relationship', css_class='w-1/3 pl-2'),
                ),
                Row(
                    Column('guardian_email', css_class='w-1/2 pr-2'),
                    Column('guardian_phone', css_class='w-1/2 pl-2'),
                ),
                'guardian_address',
                'guardian_occupation',
            ),
            Fieldset(
                'Terms and Conditions',
                'terms_agreed',
            ),
            TailwindSubmit('submit', 'Submit Application', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Check if admissions are open
        ApplicationValidator.validate_admissions_open()
        
        # Check for duplicate application
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        current_session = AcademicSessionSelector.get_current_session()
        
        if email and current_session:
            ApplicationValidator.validate_duplicate_application(
                email=email,
                phone=phone,
                session_id=current_session.id
            )
        
        return cleaned_data


class StaffApplicationForm(forms.ModelForm):
    """Staff-facing application form - staff creates application for a student (child/ward)"""
    
    class Meta:
        model = Application
        fields = [
            'first_name', 'last_name', 'middle_name', 'gender', 'date_of_birth',
            'email', 'phone', 'alternate_phone', 'address', 'city', 'state_of_origin', 'nationality',
            'applying_for_class', 'application_type',
            'previous_school', 'previous_class',
            'guardian_first_name', 'guardian_last_name', 'guardian_relationship',
            'guardian_phone', 'guardian_email', 'guardian_address', 'guardian_occupation',
        ]
        widgets = {
            'date_of_birth': DateInput(),
            'address': forms.Textarea(attrs={'rows': 2}),
            'guardian_address': forms.Textarea(attrs={'rows': 2}),
        }
        help_texts = {
            'phone': "Nigerian format: 08012345678",
            'guardian_phone': "Nigerian format: 08012345678",
        }
    
    def __init__(self, *args, **kwargs):
        # Pop user from kwargs before super().__init__
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set class queryset
        self.fields['applying_for_class'].queryset = StudentClassSelector.get_queryset_for_forms(active_only=True)
        self.fields['applying_for_class'].empty_label = "Select a class"
        
        # Make student name fields NOT pre-populated - staff enters them manually
        # Only pre-populate GUARDIAN fields from the logged-in staff user (for new applications)
        if user and user.is_authenticated and not self.instance.pk:
            from apps.staffs.models import Staff
            try:
                staff = Staff.objects.get(user=user)
                # GUARDIAN fields pre-populated from staff (editable)
                self.fields['guardian_first_name'].initial = staff.first_name
                self.fields['guardian_last_name'].initial = staff.last_name
                self.fields['guardian_email'].initial = staff.email
                self.fields['guardian_phone'].initial = staff.phone
                self.fields['guardian_address'].initial = staff.address
                self.fields['guardian_occupation'].initial = getattr(staff, 'job_title', 'Staff')
                self.fields['guardian_relationship'].initial = 'Staff'
            except Staff.DoesNotExist:
                # Fallback to user data if no staff profile
                self.fields['guardian_first_name'].initial = user.first_name
                self.fields['guardian_last_name'].initial = user.last_name
                self.fields['guardian_email'].initial = user.email
                self.fields['guardian_relationship'].initial = 'Staff'
        
        # Crispy Forms layout
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-6'
        self.helper.layout = Layout(
            Fieldset(
                'Student Information',
                HTML('<p class="text-sm text-gray-500 dark:text-gray-400 mb-3">Enter the student\'s details (the child/ward)</p>'),
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
                    Column('nationality', css_class='w-1/2 pr-2'),
                    Column('state_of_origin', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'Student Contact Information',
                HTML('<p class="text-sm text-gray-500 dark:text-gray-400 mb-3">Optional - for student\'s own account</p>'),
                Row(
                    Column('email', css_class='w-1/2 pr-2'),
                    Column('phone', css_class='w-1/2 pl-2'),
                ),
                'alternate_phone',
                'address',
                'city',
            ),
            Fieldset(
                'Academic Information',
                Row(
                    Column('applying_for_class', css_class='w-1/2 pr-2'),
                    Column('application_type', css_class='w-1/2 pl-2'),
                ),
                Row(
                    Column('previous_school', css_class='w-1/2 pr-2'),
                    Column('previous_class', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'Guardian Information',
                HTML('<p class="text-sm text-gray-500 dark:text-gray-400 mb-3">Pre-filled from your staff profile - editable</p>'),
                Row(
                    Column('guardian_first_name', css_class='w-1/3 pr-2'),
                    Column('guardian_last_name', css_class='w-1/3 px-1'),
                    Column('guardian_relationship', css_class='w-1/3 pl-2'),
                ),
                Row(
                    Column('guardian_email', css_class='w-1/2 pr-2'),
                    Column('guardian_phone', css_class='w-1/2 pl-2'),
                ),
                'guardian_address',
                'guardian_occupation',
            ),
            TailwindSubmit('submit', 'Save Application', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )


class ApplicationReviewForm(forms.Form):
    """Form for reviewing applications"""
    
    STATUS_CHOICES = [
        ('approved', 'Approve'),
        ('rejected', 'Reject'),
        ('waitlisted', 'Waitlist'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.RadioSelect,
        label="Decision"
    )
    
    review_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add review notes...'}),
        label="Review Notes"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            'status',
            'review_notes',
            TailwindSubmit('submit', 'Submit Review', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
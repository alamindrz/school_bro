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
    """Staff-facing application form with additional fields"""
    
    class Meta:
        model = Application
        fields = '__all__'
        widgets = {
            'date_of_birth': DateInput(),
            'review_notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-6'
        self.helper.layout = Layout(
            Fieldset(
                'Application Information',
                Row(
                    Column('application_number', css_class='w-1/2 pr-2'),
                    Column('status', css_class='w-1/2 pl-2'),
                ),
                Row(
                    Column('application_type', css_class='w-1/2 pr-2'),
                    Column('applying_for_session', css_class='w-1/2 pl-2'),
                ),
            ),
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
            # ... rest of the fields similar to PublicApplicationForm
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
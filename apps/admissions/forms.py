"""
Admissions Forms - ALL forms for admissions app
Using crispy-tailwind for consistent styling
"""

import logging
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Fieldset
from crispy_tailwind.layout import Submit as TailwindSubmit
from .models import Application
from .validators import ApplicationValidator
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector

logger = logging.getLogger(__name__)


class DateInput(forms.DateInput):
    input_type = 'date'


class PublicApplicationForm(forms.ModelForm):
    """Public-facing application form with clear error handling"""
    
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
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'w-full'}),
            'guardian_address': forms.Textarea(attrs={'rows': 2, 'class': 'w-full'}),
        }
        help_texts = {
            'phone': "Nigerian format: 08012345678",
            'guardian_phone': "Nigerian format: 08012345678",
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set class choices
        self.fields['applying_for_class'].queryset = StudentClassSelector.get_queryset_for_forms(active_only=True)
        self.fields['applying_for_class'].empty_label = "Select a class"
        
        # Make email and phone optional for student
        self.fields['email'].required = False
        self.fields['phone'].required = False
        self.fields['alternate_phone'].required = False
        self.fields['address'].required = False
        self.fields['city'].required = False
        
        # Make guardian email optional
        self.fields['guardian_email'].required = False
        self.fields['guardian_address'].required = False
        self.fields['guardian_occupation'].required = False
        
        # Convert guardian_relationship to ChoiceField
        from apps.students.constants import GuardianRelationship
        self.fields['guardian_relationship'] = forms.ChoiceField(
            choices=GuardianRelationship.CHOICES,
            required=True,
            label="Relationship",
            initial='other'
        )
        
        # Crispy Forms layout
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-6'
        self.helper.layout = Layout(
            Fieldset(
                'Student Personal Information',
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
                'Student Contact Information (Optional)',
                HTML('<p class="text-sm text-gray-500 mb-3">If provided, the student can log in to view their records</p>'),
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
                'Guardian Information (Primary Contact)',
                HTML('<p class="text-sm text-red-500 mb-3">* All fields marked with * are required</p>'),
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
            TailwindSubmit('submit', 'Submit Application', css_class='bg-primary-600 hover:bg-primary-700 text-white w-full')
        )
    
    def clean_email(self):
        """Validate email format if provided"""
        email = self.cleaned_data.get('email')
        if email and '@' not in email:
            raise forms.ValidationError("Enter a valid email address")
        return email
    
    def clean_phone(self):
        """Validate phone number format if provided"""
        phone = self.cleaned_data.get('phone')
        if phone and len(phone) < 10:
            raise forms.ValidationError("Enter a valid phone number (minimum 10 digits)")
        return phone
    
    def clean_guardian_phone(self):
        """Validate guardian phone number"""
        phone = self.cleaned_data.get('guardian_phone')
        if not phone:
            raise forms.ValidationError("Guardian phone number is required")
        if len(phone) < 10:
            raise forms.ValidationError("Enter a valid phone number (minimum 10 digits)")
        return phone
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        
        logger.info("PublicApplicationForm.clean() called")
        
        # Check if admissions are open
        try:
            ApplicationValidator.validate_admissions_open()
            logger.info("Admissions open check passed")
        except Exception as e:
            logger.error(f"Admissions open check failed: {e}")
            raise forms.ValidationError(str(e))
        
        # Check for duplicate application (only if email provided)
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        
        if email or phone:
            try:
                current_session = AcademicSessionSelector.get_current_session()
                if current_session:
                    ApplicationValidator.validate_duplicate_application(
                        email=email if email else None,
                        phone=phone if phone else None,
                        session_id=current_session.id
                    )
                    logger.info("Duplicate check passed")
            except Exception as e:
                logger.error(f"Duplicate check failed: {e}")
                raise forms.ValidationError(str(e))
        
        return cleaned_data


class StaffApplicationForm(forms.ModelForm):
    """Staff-facing application form with sibling copy feature"""
    
    copy_from_sibling = forms.ChoiceField(
        choices=[],
        required=False,
        label="Copy from existing child",
        help_text="Select a sibling to copy guardian information"
    )
    
    use_same_last_name = forms.BooleanField(
        required=False,
        initial=True,
        label="Same last name as sibling",
        help_text="Uncheck if this child has a different last name"
    )
    
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
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set class queryset
        self.fields['applying_for_class'].queryset = StudentClassSelector.get_queryset_for_forms(active_only=True)
        self.fields['applying_for_class'].empty_label = "Select a class"
        
        # Make student contact fields optional
        self.fields['email'].required = False
        self.fields['phone'].required = False
        self.fields['alternate_phone'].required = False
        self.fields['address'].required = False
        self.fields['city'].required = False
        
        # Make guardian email optional
        self.fields['guardian_email'].required = False
        self.fields['guardian_address'].required = False
        self.fields['guardian_occupation'].required = False
        
        # Guardian relationship choices
        from apps.students.constants import GuardianRelationship
        self.fields['guardian_relationship'] = forms.ChoiceField(
            choices=GuardianRelationship.CHOICES,
            required=True,
            label="Relationship",
            initial='other'
        )
        
        # Mark as staff child
        self.user = user
        if user and user.is_authenticated and not self.instance.pk:
            self.instance.is_staff_child = True
        
        # Load existing children for this staff
        self.existing_children = self._get_existing_children(user)
        
        if self.existing_children:
            choices = [('', '-- Select a sibling to copy from --')]
            for child in self.existing_children:
                choices.append((str(child['id']), f"{child['name']} (Class: {child['class']})"))
            self.fields['copy_from_sibling'].choices = choices
            
            # Make last name optional if copying from sibling
            self.fields['last_name'].required = False
            self.fields['last_name'].help_text = "Leave blank to use sibling's last name"
        
        # Crispy Forms layout
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-6'
        self.helper.layout = Layout(
            Fieldset(
                'Sibling Information (Optional)',
                HTML('<p class="text-sm text-gray-500 mb-3">If this child has a sibling already in the school, select them to auto-fill guardian information</p>'),
                'copy_from_sibling',
                'use_same_last_name',
            ),
            Fieldset(
                'Student Information',
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
                'Student Contact Information (Optional)',
                HTML('<p class="text-sm text-gray-500 mb-3">For the student\'s own account - leave blank if not needed</p>'),
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
                HTML('<p class="text-sm text-gray-500 mb-3">Pre-filled from your profile - editable</p>'),
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
    
    def _get_existing_children(self, user):
        """Get existing children for this staff member"""
        from apps.students.models import Student
        from apps.parents.models import ParentProfile, ChildLink
        from apps.staffs.models import Staff
        
        if not user or not user.is_authenticated:
            return []
        
        try:
            staff = Staff.objects.get(user=user)
            parent = ParentProfile.objects.filter(email=staff.email).first()
            
            if not parent:
                return []
            
            children = ChildLink.objects.filter(parent=parent)
            result = []
            for child in children:
                student = Student.objects.filter(id=child.student_id).first()
                if student:
                    result.append({
                        'id': student.id,
                        'name': student.get_full_name,
                        'first_name': student.first_name,
                        'last_name': student.last_name,
                        'class': child.student_class,
                        'class_id': student.current_class_id,
                    })
            return result
        except Exception as e:
            logger.warning(f"Failed to get existing children: {e}")
            return []
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Handle sibling copy
        copy_from = cleaned_data.get('copy_from_sibling')
        use_same_last_name = cleaned_data.get('use_same_last_name', True)
        
        if copy_from:
            sibling = next((c for c in self.existing_children if str(c['id']) == copy_from), None)
            if sibling:
                # Copy guardian info from sibling
                if not cleaned_data.get('guardian_first_name'):
                    cleaned_data['guardian_first_name'] = sibling.get('guardian_first_name', self.user.first_name if self.user else '')
                if not cleaned_data.get('guardian_last_name'):
                    cleaned_data['guardian_last_name'] = sibling.get('guardian_last_name', self.user.last_name if self.user else '')
                
                # Handle last name
                if use_same_last_name and not cleaned_data.get('last_name'):
                    cleaned_data['last_name'] = sibling['last_name']
        
        # Pre-populate guardian info from staff if not provided
        if self.user and self.user.is_authenticated:
            if not cleaned_data.get('guardian_first_name'):
                cleaned_data['guardian_first_name'] = self.user.first_name
            if not cleaned_data.get('guardian_last_name'):
                cleaned_data['guardian_last_name'] = self.user.last_name
            if not cleaned_data.get('guardian_email'):
                cleaned_data['guardian_email'] = self.user.email
            if not cleaned_data.get('guardian_phone'):
                # Try to get from staff profile
                from apps.staffs.models import Staff
                try:
                    staff = Staff.objects.get(user=self.user)
                    cleaned_data['guardian_phone'] = staff.phone
                except Staff.DoesNotExist:
                    pass
        
        return cleaned_data


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
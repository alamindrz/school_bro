"""
Parents Forms - ALL forms for parents app
Using crispy-tailwind for consistent styling
"""

from django import forms
from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Fieldset
from crispy_tailwind.layout import Submit as TailwindSubmit
from .models import ParentProfile, ChildLink, Message
from .constants import RelationshipType

User = get_user_model()


class ParentLoginForm(forms.Form):
    """Form for parent portal login (magic link)"""
    
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email address',
            'class': 'form-input'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            'email',
            HTML("""
                <p class="text-xs text-gray-500 dark:text-gray-400 text-center">
                    We'll send a secure login link to your email. No password needed.
                </p>
            """),
            TailwindSubmit('submit', 'Send Login Link', css_class='w-full bg-primary-600 hover:bg-primary-700 text-white')
        )


class ParentProfileForm(forms.ModelForm):
    """Form for editing parent profile"""
    
    class Meta:
        model = ParentProfile
        fields = ['first_name', 'last_name', 'email', 'phone', 'alternate_phone', 'preferred_language']
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': '08012345678'}),
            'alternate_phone': forms.TextInput(attrs={'placeholder': '08012345678'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Fieldset(
                'Personal Information',
                Row(
                    Column('first_name', css_class='w-1/2 pr-2'),
                    Column('last_name', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'Contact Information',
                'email',
                Row(
                    Column('phone', css_class='w-1/2 pr-2'),
                    Column('alternate_phone', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'Preferences',
                'preferred_language',
            ),
            TailwindSubmit('submit', 'Update Profile', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        from .validators import ParentValidator
        ParentValidator.validate_phone(phone)
        return phone


class NotificationPreferencesForm(forms.Form):
    """Form for notification preferences"""
    
    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent
        
        from .constants import NotificationType, NotificationChannel
        
        # Dynamically create fields for each notification type
        for notif_type, _ in NotificationType.CHOICES:
            field_name = f"notify_{notif_type}"
            current_prefs = parent.notification_preferences.get(notif_type, []) if parent else []
            
            self.fields[field_name] = forms.MultipleChoiceField(
                label=notif_type.replace('_', ' ').title(),
                choices=NotificationChannel.CHOICES,
                widget=forms.CheckboxSelectMultiple(attrs={'class': 'space-y-2'}),
                required=False,
                initial=current_prefs
            )
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-6'
        
        # Build layout dynamically
        layout_fields = []
        for notif_type, _ in NotificationType.CHOICES:
            field_name = f"notify_{notif_type}"
            layout_fields.append(
                Fieldset(
                    notif_type.replace('_', ' ').title(),
                    field_name,
                )
            )
        
        layout_fields.append(TailwindSubmit('submit', 'Save Preferences', css_class='bg-primary-600 hover:bg-primary-700 text-white'))
        
        self.helper.layout = Layout(*layout_fields)


class ChildLinkForm(forms.ModelForm):
    """Form for linking a parent to a student"""
    
    class Meta:
        model = ChildLink
        fields = ['student_id', 'student_name', 'student_class', 'relationship', 'is_primary']
        widgets = {
            'student_id': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'student_name': forms.TextInput(attrs={'readonly': 'readonly'}),
            'student_class': forms.TextInput(attrs={'readonly': 'readonly'}),
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
                'student_class',
            ),
            Fieldset(
                'Relationship',
                Row(
                    Column('relationship', css_class='w-1/2 pr-2'),
                    Column('is_primary', css_class='w-1/2 pl-2'),
                ),
            ),
            TailwindSubmit('submit', 'Link Child', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )


class ParentMessageForm(forms.ModelForm):
    """Form for sending messages from parent portal"""
    
    class Meta:
        model = Message
        fields = ['subject', 'body']
        widgets = {
            'subject': forms.TextInput(attrs={'placeholder': 'Enter message subject'}),
            'body': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Type your message here...'}),
        }
    
    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.student = student
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        layout = [
            Fieldset(
                'Message Details',
                'subject',
                'body',
            )
        ]
        
        if student:
            layout.insert(0, HTML(f"""
                <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                    <p class="text-sm text-blue-800 dark:text-blue-200">
                        <i class="fas fa-info-circle mr-1"></i>
                        Sending message about: <strong>{student.full_name}</strong>
                    </p>
                </div>
            """))
        
        layout.append(TailwindSubmit('submit', 'Send Message', css_class='bg-primary-600 hover:bg-primary-700 text-white'))
        
        self.helper.layout = Layout(*layout)
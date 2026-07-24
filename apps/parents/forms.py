"""
Parents Forms - ALL forms for parents app
Using crispy-tailwind for consistent styling
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Fieldset
from crispy_tailwind.layout import Submit as TailwindSubmit

from .models import ParentProfile, ChildLink, Message
from .constants import RelationshipType


class ParentLoginForm(forms.Form):
    email = forms.EmailField(
        label=_("Email Address"),
        widget=forms.EmailInput(attrs={
            'placeholder': _('Enter your email address'),
            'class': 'form-input',
            'autocomplete': 'email',
            'required': True,
        })
    )
    password = forms.CharField(
        label=_("Password"),
        required=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': _('Enter your password (optional)'),
            'class': 'form-input',
            'autocomplete': 'current-password',
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            'email',
            'password',
            HTML("""
                <p class="text-xs text-gray-500 dark:text-gray-400 text-center">
                    Enter your password if you have one, or leave it blank to receive a magic link.
                </p>
            """),
            TailwindSubmit('submit', _('Log In'), 
                          css_class='w-full bg-primary-600 hover:bg-primary-700 text-white')
        )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email


class ParentProfileForm(forms.ModelForm):
    class Meta:
        model = ParentProfile
        fields = ['first_name', 'last_name', 'email', 'phone', 'alternate_phone']
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': _('08012345678')}),
            'alternate_phone': forms.TextInput(attrs={'placeholder': _('08012345678')}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Fieldset(_('Personal   Information'),
                Row(Column('first_name', css_class='w-1/2 pr-2'), Column('last_name', css_class='w-1/2 pl-2')),
            ),
            Fieldset(_('Contact Information'),
                'email',
                Row(Column('phone', css_class='w-1/2 pr-2'), Column('alternate_phone', css_class='w-1/2 pl-2')),
            ),
            Fieldset(_('Preferences'), 'preferred_language'),
            TailwindSubmit('submit', _('Update Profile'), css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        return phone
    
    def clean_alternate_phone(self):
        phone = self.cleaned_data.get('alternate_phone')
        return phone

class ChildLinkForm(forms.ModelForm):
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
            Fieldset(_('Student Information'),
                Row(Column('student_id', css_class='w-1/3 pr-2'), Column('student_name', css_class='w-2/3 pl-2')),
                'student_class',
            ),
            Fieldset(_('Relationship'),
                Row(Column('relationship', css_class='w-1/2 pr-2'), Column('is_primary', css_class='w-1/2 pl-2')),
            ),
            TailwindSubmit('submit', _('Link Child'), css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id')
        if not student_id:
            raise ValidationError(_("Student ID is required"))
        from apps.students.selectors import StudentSelector
        if not StudentSelector.exists(student_id):
            raise ValidationError(_("Student not found"))
        return student_id


class ParentMessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['subject', 'body']
        widgets = {
            'subject': forms.TextInput(attrs={'placeholder': _('Enter message subject'), 'maxlength': 200, 'required': True}),
            'body': forms.Textarea(attrs={'rows': 5, 'placeholder': _('Type your message here...'), 'required': True}),
        }
    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.student = student
        self.fields['subject'].max_length = 200
        self.fields['body'].max_length = 10000
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        layout = [Fieldset(_('Message Details'), 'subject', 'body')]
        if student:
            layout.insert(0, HTML(f"""
                <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                    <p class="text-sm text-blue-800 dark:text-blue-200">
                        <i class="fas fa-info-circle mr-1"></i>
                        {_('Sending message about:')} <strong>{student.full_name}</strong>
                    </p>
                </div>
            """))
        layout.append(TailwindSubmit('submit', _('Send Message'), css_class='bg-primary-600 hover:bg-primary-700 text-white'))
        self.helper.layout = Layout(*layout)
    def clean_body(self):
        body = self.cleaned_data.get('body')
        if body:
            from django.utils.html import strip_tags
            body = strip_tags(body)
            if len(body) < 10:
                raise ValidationError(_("Message must be at least 10 characters"))
        return body


class ResendMagicLinkForm(forms.Form):
    email = forms.EmailField(
        label=_("Email Address"),
        widget=forms.EmailInput(attrs={'placeholder': _('Enter your email address'), 'class': 'form-input', 'autocomplete': 'email', 'required': True})
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            'email',
            TailwindSubmit('submit', _('Resend Link'), css_class='w-full bg-primary-600 hover:bg-primary-700 text-white')
        )
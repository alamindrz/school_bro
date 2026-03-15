"""
Corecode Forms - ALL forms for corecode app
Using crispy-tailwind for consistent styling
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Field
from crispy_tailwind.layout import Submit as TailwindSubmit
from .models import AcademicSession, AcademicTerm, StudentClass, SiteConfig


class AcademicSessionForm(forms.ModelForm):
    """Form for AcademicSession"""
    
    class Meta:
        model = AcademicSession
        fields = ['name', 'code', 'start_date', 'end_date', 'is_current']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='w-1/2 pr-2'),
                Column('code', css_class='w-1/2 pl-2'),
            ),
            Row(
                Column('start_date', css_class='w-1/2 pr-2'),
                Column('end_date', css_class='w-1/2 pl-2'),
            ),
            'is_current',
            HTML("""
                <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 mt-4">
                    <p class="text-sm text-blue-800 dark:text-blue-200">
                        <i class="fas fa-info-circle mr-1"></i>
                        Terms will be automatically created when you save this session.
                    </p>
                </div>
            """),
            TailwindSubmit('submit', 'Save Session', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )


class StudentClassForm(forms.ModelForm):
    """Form for StudentClass"""
    
    class Meta:
        model = StudentClass
        fields = ['display_name', 'max_students', 'is_active']
        widgets = {
            'display_name': forms.TextInput(attrs={'placeholder': 'e.g., SS 1'}),
            'max_students': forms.NumberInput(attrs={'min': 1, 'max': 100}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('display_name', css_class='w-1/2'),
                Column('max_students', css_class='w-1/2'),
            ),
            'is_active',
            HTML("""
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
                    <i class="fas fa-lock mr-1"></i> Class name and code cannot be changed as they follow Nigerian 6-3-3-4 standard.
                </p>
            """),
            TailwindSubmit('submit', 'Update Class', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
    
    def clean_max_students(self):
        max_students = self.cleaned_data.get('max_students')
        if max_students and max_students > 100:
            raise forms.ValidationError("Maximum students cannot exceed 100")
        return max_students


class SiteConfigForm(forms.Form):
    """Form for Site Configuration (not ModelForm due to key-value structure)"""
    
    def __init__(self, *args, **kwargs):
        self.configs = kwargs.pop('configs', {})
        super().__init__(*args, **kwargs)
        
        for key, config in self.configs.items():
            field = self.create_field(key, config)
            if field:
                self.fields[key] = field
    
    def create_field(self, key, config):
        """Create appropriate field based on config key"""
        if key in ['ADMISSIONS_OPEN', 'AUTO_ENROLL_APPROVED', 'EXAM_CLEARANCE_REQUIRED', 'MAINTENANCE_MODE']:
            return forms.BooleanField(
                label=key.replace('_', ' ').title(),
                required=False,
                initial=config.value == 'True',
                help_text=config.description
            )
        elif key in ['PASS_MARK', 'DISTINCTION_MARK', 'TERMS_PER_SESSION']:
            return forms.IntegerField(
                label=key.replace('_', ' ').title(),
                required=False,
                initial=config.value,
                min_value=0,
                max_value=100,
                help_text=config.description
            )
        elif key in ['APPLICATION_FEE']:
            return forms.DecimalField(
                label=key.replace('_', ' ').title(),
                required=False,
                initial=config.value,
                min_value=0,
                help_text=config.description
            )
        else:
            return forms.CharField(
                label=key.replace('_', ' ').title(),
                required=False,
                initial=config.value,
                help_text=config.description,
                widget=forms.TextInput(attrs={'class': 'form-input'})
            )
    
    def save(self, user=None):
        """Save config values"""
        from .services import SiteConfigService
        for key, value in self.cleaned_data.items():
            SiteConfigService.set_config(key, value, user)
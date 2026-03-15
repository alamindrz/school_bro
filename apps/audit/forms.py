"""
Audit Forms
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from crispy_tailwind.layout import Submit as TailwindSubmit
from .models import AuditRetentionPolicy


class AuditSearchForm(forms.Form):
    """Form for searching audit logs"""
    
    username = forms.CharField(required=False, max_length=150)
    action = forms.ChoiceField(required=False, choices=[])
    app_label = forms.ChoiceField(required=False, choices=[])
    model_name = forms.CharField(required=False, max_length=100)
    object_id = forms.CharField(required=False, max_length=100)
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    ip_address = forms.GenericIPAddressField(required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate choices dynamically
        from .models import AuditLog
        self.fields['action'].choices = [('', 'All Actions')] + list(AuditLog.objects.values_list('action', 'action').distinct())
        self.fields['app_label'].choices = [('', 'All Apps')] + list(AuditLog.objects.values_list('app_label', 'app_label').distinct())
        
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Row(
                Column('username', css_class='w-1/3 pr-2'),
                Column('action', css_class='w-1/3 px-1'),
                Column('app_label', css_class='w-1/3 pl-2'),
            ),
            Row(
                Column('model_name', css_class='w-1/3 pr-2'),
                Column('object_id', css_class='w-1/3 px-1'),
                Column('ip_address', css_class='w-1/3 pl-2'),
            ),
            Row(
                Column('start_date', css_class='w-1/2 pr-2'),
                Column('end_date', css_class='w-1/2 pl-2'),
            ),
            TailwindSubmit('submit', 'Search Audit Logs', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )


class RetentionPolicyForm(forms.ModelForm):
    """Form for audit retention policies"""
    
    class Meta:
        model = AuditRetentionPolicy
        fields = ['app_label', 'model_name', 'retention_days', 'action_retention', 'is_active']
        widgets = {
            'action_retention': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Row(
                Column('app_label', css_class='w-1/2 pr-2'),
                Column('model_name', css_class='w-1/2 pl-2'),
            ),
            'retention_days',
            'action_retention',
            'is_active',
            TailwindSubmit('submit', 'Save Policy', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
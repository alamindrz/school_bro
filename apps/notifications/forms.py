"""
Notifications Forms
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Fieldset
from crispy_tailwind.layout import Submit as TailwindSubmit
from .models import NotificationTemplate, Notification, NotificationPreference
from .constants import NotificationType, NotificationChannel, NotificationPriority


class NotificationTemplateForm(forms.ModelForm):
    """Form for notification templates"""
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'name', 'notification_type', 'email_subject', 'email_template',
            'sms_template', 'push_title', 'push_body', 'in_app_message',
            'available_variables', 'is_active'
        ]
        widgets = {
            'email_template': forms.Textarea(attrs={'rows': 10}),
            'in_app_message': forms.Textarea(attrs={'rows': 5}),
            'available_variables': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='w-1/2 pr-2'),
                Column('notification_type', css_class='w-1/2 pl-2'),
            ),
            Fieldset(
                'Email Template',
                'email_subject',
                'email_template',
            ),
            Fieldset(
                'SMS Template',
                'sms_template',
            ),
            Fieldset(
                'Push Notification',
                Row(
                    Column('push_title', css_class='w-1/2 pr-2'),
                    Column('push_body', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'In-App Message',
                'in_app_message',
            ),
            Fieldset(
                'Variables',
                'available_variables',
            ),
            'is_active',
            TailwindSubmit('submit', 'Save Template', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )


class NotificationPreferenceForm(forms.ModelForm):
    """Form for notification preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled',
            'quiet_hours_start', 'quiet_hours_end', 'preferences'
        ]
        widgets = {
            'quiet_hours_start': forms.TimeInput(attrs={'type': 'time'}),
            'quiet_hours_end': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Fieldset(
                'Channel Settings',
                Row(
                    Column('email_enabled', css_class='w-1/4'),
                    Column('sms_enabled', css_class='w-1/4'),
                    Column('push_enabled', css_class='w-1/4'),
                    Column('in_app_enabled', css_class='w-1/4'),
                ),
            ),
            Fieldset(
                'Quiet Hours',
                Row(
                    Column('quiet_hours_start', css_class='w-1/2 pr-2'),
                    Column('quiet_hours_end', css_class='w-1/2 pl-2'),
                ),
            ),
            Fieldset(
                'Per-Type Preferences',
                'preferences',
            ),
            TailwindSubmit('submit', 'Save Preferences', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )


class BulkNotificationForm(forms.Form):
    """Form for sending bulk notifications"""
    
    notification_type = forms.ChoiceField(choices=NotificationType.CHOICES)
    title = forms.CharField(max_length=200)
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))
    priority = forms.ChoiceField(choices=NotificationPriority.CHOICES, initial='normal')
    recipient_type = forms.ChoiceField(choices=[
        ('all_students', 'All Students'),
        ('all_parents', 'All Parents'),
        ('all_staff', 'All Staff'),
        ('specific_class', 'Specific Class'),
    ])
    class_id = forms.IntegerField(required=False, label="Class ID (for specific class)")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Row(
                Column('notification_type', css_class='w-1/2 pr-2'),
                Column('priority', css_class='w-1/2 pl-2'),
            ),
            'title',
            'message',
            'recipient_type',
            'class_id',
            TailwindSubmit('submit', 'Send Notification', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
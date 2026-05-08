"""
Timetable Forms
"""

from django import forms
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.staffs.models import Staff, TeacherSubjectQualification
from apps.corecode.models import Subject
from .models import Timetable


class TeacherQualificationForm(forms.ModelForm):
    """Form for managing teacher subject qualifications"""

    class Meta:
        model = TeacherSubjectQualification
        fields = ['teacher', 'subject', 'is_primary']
        widgets = {
            'teacher': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'subject': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].queryset = Staff.objects.filter(
            employment_status='active',
            staff_category='academic'
        )
        self.fields['subject'].queryset = Subject.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        teacher = cleaned_data.get('teacher')
        subject = cleaned_data.get('subject')

        if teacher and subject:
            existing = TeacherSubjectQualification.objects.filter(
                teacher=teacher,
                subject=subject
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError(
                    f"{teacher.get_full_name} is already qualified to teach {subject.name}"
                )

        return cleaned_data


class TimetableSlotUpdateForm(forms.Form):
    """Form for updating a timetable slot via HTMX"""

    teacher_id = forms.IntegerField(required=False)
    subject_id = forms.IntegerField(required=False)
    room = forms.CharField(max_length=50, required=False)
    is_free_period = forms.BooleanField(required=False, initial=False)
    timetable_id = forms.IntegerField(required=True)
    day_id = forms.IntegerField(required=True)
    period_id = forms.IntegerField(required=True)

    def clean(self):
        cleaned_data = super().clean()
        teacher_id = cleaned_data.get('teacher_id')
        subject_id = cleaned_data.get('subject_id')
        is_free_period = cleaned_data.get('is_free_period')

        if not is_free_period and teacher_id and not subject_id:
            raise ValidationError("Please select a subject for this teacher")

        if teacher_id:
            try:
                Staff.objects.get(id=teacher_id, employment_status='active', staff_category='academic')
            except Staff.DoesNotExist:
                raise ValidationError("Selected teacher is not valid or not active")

        if subject_id:
            try:
                Subject.objects.get(id=subject_id, is_active=True)
            except Subject.DoesNotExist:
                raise ValidationError("Selected subject is not valid")

        return cleaned_data


class TimetableForm(forms.ModelForm):
    """Form for creating/editing timetables"""

    class Meta:
        model = Timetable
        fields = ['name', 'academic_session', 'academic_term', 'student_class', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg',
                'placeholder': 'e.g., SS1A First Term'
            }),
            'academic_session': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'academic_term': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'student_class': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['academic_term'].required = False
        self.fields['name'].required = False


class BulkQualificationForm(forms.Form):
    """Form for bulk assigning qualifications to multiple teachers"""

    teacher_ids = forms.ModelMultipleChoiceField(
        queryset=Staff.objects.filter(employment_status='active', staff_category='academic'),
        widget=forms.CheckboxSelectMultiple,
        label="Select Teachers"
    )
    subject_ids = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        label="Select Subjects"
    )
    is_primary = forms.BooleanField(
        required=False, initial=False,
        label="Set as primary subject"
    )

    @transaction.atomic
    def save(self, created_by=None):
        teacher_ids = self.cleaned_data['teacher_ids']
        subject_ids = self.cleaned_data['subject_ids']
        is_primary = self.cleaned_data['is_primary']

        created_count = 0
        for teacher in teacher_ids:
            for subject in subject_ids:
                qual, created = TeacherSubjectQualification.objects.get_or_create(
                    teacher=teacher,
                    subject=subject,
                    defaults={
                        'is_primary': is_primary,
                        'created_by': created_by
                    }
                )
                if created:
                    created_count += 1

        return created_count
"""
Results Forms - ALL forms for results app
Using crispy-tailwind for consistent styling
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Fieldset
from crispy_tailwind.layout import Submit as TailwindSubmit
from apps.corecode.models import Subject

from .models import ScoreSheet, Result, ResultComment
from .constants import SubjectType, GradeSystem, RemarkType
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector
from apps.staffs.selectors import StaffSelector


class SubjectForm(forms.ModelForm):
    """Form for creating/editing subjects"""
    
    class Meta:
        model = Subject
        fields = ['name', 'code', 'subject_type', 'description', 'is_nigerian_core', 'offered_in_classes', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'offered_in_classes': forms.SelectMultiple(attrs={'size': 10, 'class': 'select-multiple'}),
        }
        help_texts = {
            'code': "e.g., ENG, MTH, SCI",
            'offered_in_classes': "Hold Ctrl/Cmd to select multiple classes",
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['offered_in_classes'].queryset = StudentClassSelector.get_all_classes_queryset()
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='w-1/2 pr-2'),
                Column('code', css_class='w-1/2 pl-2'),
            ),
            Row(
                Column('subject_type', css_class='w-1/2 pr-2'),
                Column('is_nigerian_core', css_class='w-1/2 pl-2'),
            ),
            'description',
            'offered_in_classes',
            'is_active',
            TailwindSubmit('submit', 'Save Subject', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        return code.upper()


class ScoreSheetForm(forms.ModelForm):
    """Form for creating result sheets"""
    
    subjects = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Subjects"
    )
    
    class Meta:
        model = ScoreSheet
        fields = ['student_class', 'academic_session', 'academic_term']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['student_class'].queryset = StudentClassSelector.get_all_classes_queryset()
        self.fields['academic_session'].queryset = AcademicSession.objects.filter(is_current=True)
        self.fields['subjects'].queryset = Subject.objects.filter(is_active=True)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Row(
                Column('student_class', css_class='w-1/2 pr-2'),
                Column('academic_session', css_class='w-1/2 pl-2'),
            ),
            'academic_term',
            Fieldset(
                'Select Subjects',
                'subjects',
                css_class='mt-4'
            ),
            HTML("""
                <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                    <p class="text-sm text-blue-800 dark:text-blue-200">
                        <i class="fas fa-info-circle mr-1"></i>
                        You can add teachers and adjust subject settings after creating the sheet.
                    </p>
                </div>
            """),
            TailwindSubmit('submit', 'Create Result Sheet', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )


class ResultEntryForm(forms.Form):
    """Form for entering individual student results"""
    
    def __init__(self, *args, subject=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.subject = subject
        
        # Dynamically create score fields based on subject
        self.fields['ca1'] = forms.IntegerField(
            required=False,
            min_value=0,
            max_value=100,
            widget=forms.NumberInput(attrs={'class': 'w-20', 'placeholder': 'CA1'}),
            label="CA1"
        )
        
        self.fields['ca2'] = forms.IntegerField(
            required=False,
            min_value=0,
            max_value=100,
            widget=forms.NumberInput(attrs={'class': 'w-20', 'placeholder': 'CA2'}),
            label="CA2"
        )
        
        self.fields['ca3'] = forms.IntegerField(
            required=False,
            min_value=0,
            max_value=100,
            widget=forms.NumberInput(attrs={'class': 'w-20', 'placeholder': 'CA3'}),
            label="CA3"
        )
        
        self.fields['exam'] = forms.IntegerField(
            required=False,
            min_value=0,
            max_value=100,
            widget=forms.NumberInput(attrs={'class': 'w-20', 'placeholder': 'Exam'}),
            label="Exam"
        )
        
        if subject and subject.has_practical:
            self.fields['practical'] = forms.IntegerField(
                required=False,
                min_value=0,
                max_value=100,
                widget=forms.NumberInput(attrs={'class': 'w-20', 'placeholder': 'Practical'}),
                label="Practical"
            )
        
        if subject and subject.has_project:
            self.fields['project'] = forms.IntegerField(
                required=False,
                min_value=0,
                max_value=100,
                widget=forms.NumberInput(attrs={'class': 'w-20', 'placeholder': 'Project'}),
                label="Project"
            )
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.form_show_labels = False
        
        # Build layout dynamically
        layout_fields = []
        for field_name in self.fields:
            layout_fields.append(Column(field_name, css_class='w-16'))
        
        self.helper.layout = Layout(
            Row(*layout_fields, css_class='flex space-x-2 justify-end')
        )


class BulkResultUploadForm(forms.Form):
    """Form for bulk result upload via CSV"""
    
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Upload a CSV file with results. Download template for format."
    )
    
    def __init__(self, *args, sheet=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sheet = sheet
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.form_class = 'space-y-4'
        
        layout = [
            'csv_file',
            HTML("""
                <div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
                    <p class="text-sm text-yellow-800 dark:text-yellow-200">
                        <i class="fas fa-exclamation-triangle mr-1"></i>
                        Make sure your CSV matches the template format. Incorrect formatting may cause errors.
                    </p>
                </div>
            """)
        ]
        
        if sheet:
            layout.insert(0, HTML(f"""
                <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                    <p class="text-sm text-blue-800 dark:text-blue-200">
                        <i class="fas fa-info-circle mr-1"></i>
                        Uploading for: {sheet.student_class.display_name} - {sheet.academic_term.name}
                    </p>
                </div>
            """))
        
        layout.append(TailwindSubmit('submit', 'Upload Results', css_class='bg-primary-600 hover:bg-primary-700 text-white'))
        
        self.helper.layout = Layout(*layout)
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError("File must be a CSV")
        
        if csv_file.size > 5 * 1024 * 1024:  # 5MB
            raise forms.ValidationError("File size must be less than 5MB")
        
        return csv_file


class ResultCommentForm(forms.ModelForm):
    """Form for teacher comments on results"""
    
    class Meta:
        model = ResultComment
        fields = ['teacher_comment', 'class_teacher_comment', 'principal_comment', 'next_term_recommendation']
        widgets = {
            'teacher_comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Subject teacher\'s comments...'}),
            'class_teacher_comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Class teacher\'s comments...'}),
            'principal_comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Principal\'s comments...'}),
            'next_term_recommendation': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Recommendations for next term...'}),
        }
    
    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        layout = [
            Fieldset(
                'Teacher\'s Comments',
                'teacher_comment',
            ),
            Fieldset(
                'Class Teacher\'s Comments',
                'class_teacher_comment',
            ),
            Fieldset(
                'Principal\'s Comments',
                'principal_comment',
            ),
            Fieldset(
                'Next Term Recommendation',
                'next_term_recommendation',
            ),
        ]
        
        if student:
            layout.insert(0, HTML(f"""
                <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                    <p class="text-sm font-medium text-gray-900 dark:text-gray-100">{student.full_name}</p>
                </div>
            """))
        
        layout.append(TailwindSubmit('submit', 'Save Comments', css_class='bg-primary-600 hover:bg-primary-700 text-white'))
        
        self.helper.layout = Layout(*layout)
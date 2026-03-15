"""
Finance Forms - ALL forms for finance app
Using crispy-tailwind for consistent styling
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Fieldset
from crispy_tailwind.layout import Submit as TailwindSubmit
from decimal import Decimal
from .models import FeeStructure, Invoice, Payment, FeeWaiver
from .constants import FeeType, FeeTerm, PaymentMethod
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector


class DateInput(forms.DateInput):
    input_type = 'date'


class FeeStructureForm(forms.ModelForm):
    """Form for creating/editing fee structures"""
    
    class Meta:
        model = FeeStructure
        fields = ['student_class', 'fee_type', 'amount', 'term', 'academic_session', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['student_class'].queryset = StudentClassSelector.get_all_classes_queryset()
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Row(
                Column('student_class', css_class='w-1/2 pr-2'),
                Column('fee_type', css_class='w-1/2 pl-2'),
            ),
            Row(
                Column('amount', css_class='w-1/3 pr-2'),
                Column('term', css_class='w-1/3 px-1'),
                Column('academic_session', css_class='w-1/3 pl-2'),
            ),
            'description',
            'is_active',
            TailwindSubmit('submit', 'Save Fee Structure', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero")
        return amount


class InvoiceForm(forms.ModelForm):
    """Form for creating single invoices"""
    
    class Meta:
        model = Invoice
        fields = [
            'student_id', 'student_name', 'student_class',
            'fee_type', 'description', 'subtotal',
            'academic_session', 'academic_term', 'due_date'
        ]
        widgets = {
            'due_date': DateInput(),
            'description': forms.Textarea(attrs={'rows': 2}),
        }
        help_texts = {
            'student_id': "Enter student ID to auto-fill name and class",
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['student_class'].queryset = StudentClassSelector.get_all_classes_queryset()
        self.fields['academic_session'].queryset = AcademicSession.objects.filter(is_current=True)
        
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
                'Fee Details',
                Row(
                    Column('fee_type', css_class='w-1/2 pr-2'),
                    Column('subtotal', css_class='w-1/2 pl-2'),
                ),
                'description',
            ),
            Fieldset(
                'Academic Context',
                Row(
                    Column('academic_session', css_class='w-1/2 pr-2'),
                    Column('academic_term', css_class='w-1/2 pl-2'),
                ),
                'due_date',
            ),
            HTML("""
                <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                    <p class="text-sm text-blue-800 dark:text-blue-200">
                        <i class="fas fa-info-circle mr-1"></i>
                        The invoice total will be calculated after adding any discounts or waivers.
                    </p>
                </div>
            """),
            TailwindSubmit('submit', 'Create Invoice', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
    
    def clean_subtotal(self):
        subtotal = self.cleaned_data.get('subtotal')
        if subtotal <= 0:
            raise forms.ValidationError("Amount must be greater than zero")
        return subtotal


class BulkInvoiceForm(forms.Form):
    """Form for bulk invoice creation"""
    
    class_id = forms.ModelChoiceField(
        queryset=StudentClassSelector.get_all_classes_queryset(),
        label="Class",
        help_text="Invoices will be created for all active students in this class"
    )
    
    fee_type = forms.ChoiceField(
        choices=FeeType.CHOICES,
        label="Fee Type"
    )
    
    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        label="Amount (₦)"
    )
    
    academic_session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.filter(is_current=True),
        label="Session"
    )
    
    academic_term = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label="Term",
        help_text="Leave blank for one-time or per-session fees"
    )
    
    due_date = forms.DateField(
        widget=DateInput,
        required=False,
        label="Due Date"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            Row(
                Column('class_id', css_class='w-1/2 pr-2'),
                Column('fee_type', css_class='w-1/2 pl-2'),
            ),
            Row(
                Column('amount', css_class='w-1/3 pr-2'),
                Column('academic_session', css_class='w-1/3 px-1'),
                Column('academic_term', css_class='w-1/3 pl-2'),
            ),
            'due_date',
            HTML("""
                <div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
                    <p class="text-sm text-yellow-800 dark:text-yellow-200">
                        <i class="fas fa-exclamation-triangle mr-1"></i>
                        This will create invoices for ALL active students in the selected class.
                    </p>
                </div>
            """),
            TailwindSubmit('submit', 'Create Bulk Invoices', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )


class PaymentForm(forms.Form):
    """Form for recording payments"""
    
    invoice_id = forms.IntegerField(
        widget=forms.HiddenInput,
        required=False
    )
    
    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        label="Amount (₦)"
    )
    
    payment_method = forms.ChoiceField(
        choices=[(k, v) for k, v in PaymentMethod.CHOICES if k not in ['paystack', 'waiver']],
        label="Payment Method"
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes...'}),
        label="Notes"
    )
    
    def __init__(self, *args, invoice=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.invoice = invoice
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        layout = [
            'invoice_id',
            Row(
                Column('amount', css_class='w-1/2 pr-2'),
                Column('payment_method', css_class='w-1/2 pl-2'),
            ),
            'notes',
        ]
        
        if invoice:
            layout.insert(1, HTML(f"""
                <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                    <p class="text-sm text-gray-600 dark:text-gray-400">
                        Invoice: <strong>{invoice.invoice_number}</strong><br>
                        Student: {invoice.student_name}<br>
                        Balance: <span class="text-yellow-600 dark:text-yellow-400">₦{invoice.balance}</span>
                    </p>
                </div>
            """))
        
        layout.append(TailwindSubmit('submit', 'Record Payment', css_class='bg-primary-600 hover:bg-primary-700 text-white'))
        
        self.helper.layout = Layout(*layout)
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        
        if self.invoice and amount:
            if amount > self.invoice.balance:
                raise forms.ValidationError(
                    f"Payment amount (₦{amount}) exceeds invoice balance (₦{self.invoice.balance})"
                )
        
        return cleaned_data


class WaiverRequestForm(forms.ModelForm):
    """Form for requesting fee waivers"""
    
    class Meta:
        model = FeeWaiver
        fields = ['amount', 'reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Explain reason for waiver request...'}),
        }
    
    def __init__(self, *args, invoice=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.invoice = invoice
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        layout = [
            Row(
                Column('amount', css_class='w-1/2'),
                Column(HTML(f'<p class="text-sm text-gray-500 dark:text-gray-400 mt-2">Max: ₦{invoice.balance if invoice else 0}</p>'), css_class='w-1/2'),
            ),
            'reason',
        ]
        
        layout.append(TailwindSubmit('submit', 'Submit Waiver Request', css_class='bg-primary-600 hover:bg-primary-700 text-white'))
        
        self.helper.layout = Layout(*layout)
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        
        if self.invoice and amount > self.invoice.balance:
            raise forms.ValidationError(f"Amount cannot exceed invoice balance (₦{self.invoice.balance})")
        
        return amount


class DateRangeReportForm(forms.Form):
    """Form for date range reports"""
    
    REPORT_TYPES = [
        ('daily', 'Daily Report'),
        ('weekly', 'Weekly Report'),
        ('monthly', 'Monthly Report'),
        ('custom', 'Custom Range'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        label="Report Type"
    )
    
    start_date = forms.DateField(
        widget=DateInput,
        required=False,
        label="Start Date"
    )
    
    end_date = forms.DateField(
        widget=DateInput,
        required=False,
        label="End Date"
    )
    
    class_id = forms.ModelChoiceField(
        queryset=StudentClassSelector.get_all_classes_queryset(),
        required=False,
        label="Class (Optional)",
        help_text="Leave blank for all classes"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'space-y-4'
        self.helper.layout = Layout(
            'report_type',
            Row(
                Column('start_date', css_class='w-1/2 pr-2'),
                Column('end_date', css_class='w-1/2 pl-2'),
            ),
            'class_id',
            TailwindSubmit('submit', 'Generate Report', css_class='bg-primary-600 hover:bg-primary-700 text-white')
        )
    
    def clean(self):
        cleaned_data = super().clean()
        report_type = cleaned_data.get('report_type')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if report_type == 'custom' and (not start_date or not end_date):
            raise forms.ValidationError("Both start and end dates are required for custom report")
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date cannot be after end date")
        
        return cleaned_data
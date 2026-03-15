"""
Staff views for admissions management
"""

from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required

import logging

from ..models import Application, ApplicationNote, ApplicationReview
from ..selectors import ApplicationSelector, ApplicationPaymentSelector
from ..services import ApplicationService, EnrollmentService, PaymentService
from ..constants import ApplicationStatus
from ..exceptions import (
    ApplicationNotFoundError,
    InvalidApplicationStatusError,
    EnrollmentHandoffError,
)

from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog

logger = logging.getLogger(__name__)


class ApplicationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List all applications with filtering"""
    template_name = 'admissions/pages/application_list.html'
    context_object_name = 'applications'
    permission_required = 'admissions.view_application'
    paginate_by = 25
    
    def get_queryset(self):
        """Get filtered queryset"""
        status = self.request.GET.get('status')
        class_id = self.request.GET.get('class_id')
        session_id = self.request.GET.get('session_id')
        search = self.request.GET.get('search')
        
        return ApplicationSelector.list_applications(
            status=status,
            class_id=class_id,
            session_id=session_id,
            search=search
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ApplicationStatus.CHOICES
        context['classes'] = StudentClassSelector.get_all_classes()
        context['sessions'] = AcademicSessionSelector.list_sessions(limit=5)
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_class'] = self.request.GET.get('class_id', '')
        context['selected_session'] = self.request.GET.get('session_id', '')
        context['search_query'] = self.request.GET.get('search', '')
        context['stats'] = ApplicationSelector.get_statistics()
        return context


class ApplicationDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detailed application view"""
    model = Application
    template_name = 'admissions/pages/application_detail.html'
    context_object_name = 'application'
    permission_required = 'admissions.view_application'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['application_data'] = ApplicationSelector.get_by_id(self.object.id)
        context['payment'] = ApplicationPaymentSelector.get_for_application(self.object.id)
        return context


class ApplicationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create new application (staff-facing)"""
    model = Application
    template_name = 'admissions/pages/application_form.html'
    fields = [
        'first_name', 'last_name', 'middle_name', 'gender', 'date_of_birth',
        'email', 'phone', 'alternate_phone', 'address', 'city', 'state_of_origin',
        'nationality', 'applying_for_class', 'application_type',
        'previous_school', 'previous_class',
        'guardian_first_name', 'guardian_last_name', 'guardian_relationship',
        'guardian_phone', 'guardian_email', 'guardian_address', 'guardian_occupation',
    ]
    permission_required = 'admissions.add_application'
    success_url = reverse_lazy('admissions:list')
    
    def form_valid(self, form):
        try:
            # Create application using service
            application = ApplicationService.create_application(
                **form.cleaned_data,
                created_by_id=self.request.user.id
            )
            
            messages.success(
                self.request,
                f'Application {application.application_number} created successfully.'
            )
            
            return redirect('admissions:detail', pk=application.id)
            
        except Exception as e:
            messages.error(self.request, f'Error creating application: {str(e)}')
            return self.form_invalid(form)


class ApplicationReviewView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Review application (approve/reject/waitlist)"""
    permission_required = 'admissions.change_application'
    
    def post(self, request, *args, **kwargs):
        application_id = kwargs.get('pk')
        new_status = request.POST.get('status')
        review_notes = request.POST.get('notes', '')
        
        try:
            application = ApplicationService.review_application(
                application_id=application_id,
                new_status=new_status,
                review_notes=review_notes,
                reviewed_by_id=request.user.id
            )
            
            messages.success(
                request,
                f'Application {application.application_number} {new_status}.'
            )
            
        except InvalidApplicationStatusError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error reviewing application: {str(e)}')
        
        return redirect('admissions:detail', pk=application_id)


class ApplicationEnrollView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Enroll approved applicant as student"""
    permission_required = 'admissions.enroll_applicant'
    
    def post(self, request, *args, **kwargs):
        application_id = kwargs.get('pk')
        
        try:
            result = EnrollmentService.enroll_applicant(
                application_id=application_id,
                enrolled_by_id=request.user.id
            )
            
            messages.success(
                request,
                f'Successfully enrolled {result["student_name"]}. '
                f'Admission Number: {result["student_admission_number"]}'
            )
            
        except (ApplicationNotFoundError, InvalidApplicationStatusError) as e:
            messages.error(request, str(e))
        except EnrollmentHandoffError as e:
            messages.error(request, f'Enrollment failed: {str(e)}')
        except Exception as e:
            messages.error(request, f'Unexpected error: {str(e)}')
        
        return redirect('admissions:detail', pk=application_id)


class ApplicationAddNoteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Add note to application"""
    permission_required = 'admissions.add_applicationnote'
    
    def post(self, request, *args, **kwargs):
        application_id = kwargs.get('pk')
        note_text = request.POST.get('note')
        
        if not note_text:
            messages.error(request, 'Note cannot be empty')
            return redirect('admissions:detail', pk=application_id)
        
        try:
            ApplicationService.add_note(
                application_id=application_id,
                note=note_text,
                created_by_id=request.user.id
            )
            
            messages.success(request, 'Note added successfully.')
            
        except ApplicationNotFoundError as e:
            messages.error(request, str(e))
        
        return redirect('admissions:detail', pk=application_id)


class PaymentInitializeView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Initialize Paystack payment for application"""
    permission_required = 'admissions.process_payment'
    
    def post(self, request, *args, **kwargs):
        application_id = kwargs.get('pk')
        
        try:
            application = Application.objects.get(id=application_id)
            
            result = PaymentService.initialize_paystack_payment(
                application_id=application_id,
                email=application.email
            )
            
            # Redirect to Paystack
            return redirect(result['authorization_url'])
            
        except Application.DoesNotExist:
            messages.error(request, 'Application not found')
            return redirect('admissions:list')
        except Exception as e:
            messages.error(request, f'Payment initialization failed: {str(e)}')
            return redirect('admissions:detail', pk=application_id)


class PaymentCallbackView(TemplateView):
    """Paystack payment callback"""
    template_name = 'admissions/pages/payment_callback.html'
    
    def get(self, request, *args, **kwargs):
        reference = request.GET.get('reference')
        trxref = request.GET.get('trxref')
        
        # Use reference or trxref
        ref = reference or trxref
        
        if not ref:
            messages.error(request, 'No payment reference provided')
            return redirect('admissions:list')
        
        try:
            result = PaymentService.verify_payment(ref)
            
            if result.get('success'):
                messages.success(request, 'Payment verified successfully!')
                return redirect('admissions:detail', pk=result['application_id'])
            else:
                messages.error(request, f'Payment verification failed: {result.get("message")}')
                return redirect('admissions:list')
                
        except Exception as e:
            messages.error(request, f'Payment verification error: {str(e)}')
            return redirect('admissions:list')


@method_decorator(require_POST, name='dispatch')
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('admissions.bulk_enroll', raise_exception=True), name='dispatch')
class BulkEnrollView(View):
    """Bulk enroll multiple approved applicants"""
    
    def post(self, request, *args, **kwargs):
        application_ids = request.POST.getlist('application_ids')
        
        if not application_ids:
            messages.error(request, 'No applications selected')
            return redirect('admissions:list')
        
        try:
            results = EnrollmentService.bulk_enroll(
                application_ids=[int(id) for id in application_ids],
                enrolled_by_id=request.user.id
            )
            
            if results['failed']:
                messages.warning(
                    request,
                    f"Enrolled {len(results['successful'])} students. "
                    f"{len(results['failed'])} failed."
                )
            else:
                messages.success(
                    request,
                    f"Successfully enrolled {len(results['successful'])} students."
                )
                
        except Exception as e:
            messages.error(request, f'Bulk enrollment failed: {str(e)}')
        
        return redirect('admissions:list')
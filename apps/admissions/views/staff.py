"""
Staff views for admissions management
"""

from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required

import logging

from ..models import Application, ApplicationNote, ApplicationReview
from ..selectors import ApplicationSelector
from ..services import ApplicationService, EnrollmentService
from ..constants import ApplicationStatus
from ..exceptions import (
    ApplicationNotFoundError,
    InvalidApplicationStatusError,
    EnrollmentHandoffError,
    AdmissionsClosedError,
)

from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector, SiteConfigSelector
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog
from apps.corecode.constants import SiteConfigKey

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
        context['admissions_open'] = SiteConfigSelector.get_config_value(SiteConfigKey.ADMISSIONS_OPEN, False)
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
        context['can_review'] = self.object.created_by_id != self.request.user.id
        return context


class ApplicationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create new application (staff-facing)"""
    model = Application
    template_name = 'admissions/pages/application_form.html'
    permission_required = 'admissions.add_application'
    
    def dispatch(self, request, *args, **kwargs):
        """Check if admissions are open - if closed, redirect with message"""
        admissions_open = SiteConfigSelector.get_config_value(SiteConfigKey.ADMISSIONS_OPEN, False)
        if not admissions_open:
            messages.error(request, 'Admissions are currently closed. No new applications can be created.')
            return redirect('admissions:list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_class(self):
        """Import form here to avoid circular imports"""
        from ..forms import StaffApplicationForm
        return StaffApplicationForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        classes = StudentClassSelector.get_all_classes(active_only=True)
        context['classes'] = classes
        context['current_session'] = AcademicSessionSelector.get_current_session()
        context['admissions_open'] = True
        return context
    
    def get_success_url(self):
        return reverse_lazy('admissions:detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Get current session
                current_session = AcademicSessionSelector.get_current_session()
                if not current_session:
                    messages.error(self.request, 'No active academic session configured.')
                    return self.form_invalid(form)
                
                # Create application using service
                cleaned_data = form.cleaned_data
                
                application = ApplicationService.create_application(
                    first_name=cleaned_data['first_name'],
                    last_name=cleaned_data['last_name'],
                    middle_name=cleaned_data.get('middle_name', ''),
                    gender=cleaned_data['gender'],
                    date_of_birth=cleaned_data['date_of_birth'].isoformat(),
                    email=cleaned_data.get('email', ''),
                    phone=cleaned_data.get('phone', ''),
                    alternate_phone=cleaned_data.get('alternate_phone', ''),
                    address=cleaned_data.get('address', ''),
                    city=cleaned_data.get('city', ''),
                    state_of_origin=cleaned_data.get('state_of_origin', ''),
                    nationality=cleaned_data.get('nationality', 'Nigerian'),
                    applying_for_class_id=cleaned_data['applying_for_class'].id,
                    application_type=cleaned_data.get('application_type', 'new'),
                    previous_school=cleaned_data.get('previous_school', ''),
                    previous_class=cleaned_data.get('previous_class', ''),
                    guardian_first_name=cleaned_data['guardian_first_name'],
                    guardian_last_name=cleaned_data['guardian_last_name'],
                    guardian_relationship=cleaned_data['guardian_relationship'],
                    guardian_phone=cleaned_data['guardian_phone'],
                    guardian_email=cleaned_data.get('guardian_email', ''),
                    guardian_address=cleaned_data.get('guardian_address', ''),
                    guardian_occupation=cleaned_data.get('guardian_occupation', ''),
                    created_by_id=self.request.user.id,
                    skip_invoice=True  # Staff applications don't require payment
                )
                
                messages.success(
                    self.request,
                    f'Application {application.application_number} created and submitted for review.'
                )
                
                return redirect('admissions:detail', pk=application.id)
                
        except AdmissionsClosedError:
            messages.error(self.request, 'Admissions are currently closed.')
            return redirect('admissions:list')
        except Exception as e:
            logger.exception("Application creation failed")
            messages.error(self.request, f'Error creating application: {str(e)}')
            return self.form_invalid(form)


class ApplicationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Update existing application (staff-facing)"""
    model = Application
    template_name = 'admissions/pages/application_form.html'
    permission_required = 'admissions.change_application'
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user can edit this application"""
        application = self.get_object()
        
        # Only draft applications can be edited
        if application.status != ApplicationStatus.DRAFT:
            messages.error(request, f'Cannot edit application with status: {application.get_status_display()}')
            return redirect('admissions:detail', pk=application.pk)
        
        # Only the creator can edit (or superuser)
        if application.created_by_id != request.user.id and not request.user.is_superuser:
            messages.error(request, 'You can only edit applications you created.')
            return redirect('admissions:detail', pk=application.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_class(self):
        """Import form here to avoid circular imports"""
        from ..forms import StaffApplicationForm
        return StaffApplicationForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        classes = StudentClassSelector.get_all_classes(active_only=True)
        context['classes'] = classes
        context['current_session'] = AcademicSessionSelector.get_current_session()
        context['is_edit'] = True
        context['admissions_open'] = SiteConfigSelector.get_config_value(SiteConfigKey.ADMISSIONS_OPEN, False)
        return context
    
    def get_success_url(self):
        return reverse_lazy('admissions:detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                application = form.save(commit=False)
                application.updated_at = timezone.now()
                application.save()
                
                # Log the update
                SystemLogService.log_action(
                    user=self.request.user,
                    action=SystemLog.ActionType.UPDATE,
                    app_label=SystemLog.AppLabel.ADMISSIONS,
                    model_name='Application',
                    object_id=str(application.id),
                    object_repr=application.application_number,
                    changes=form.cleaned_data,
                    ip_address='',
                    user_agent=''
                )
                
                messages.success(
                    self.request,
                    f'Application {application.application_number} updated successfully.'
                )
                
                return redirect(self.get_success_url())
                
        except Exception as e:
            logger.exception("Application update failed")
            messages.error(self.request, f'Error updating application: {str(e)}')
            return self.form_invalid(form)


class ApplicationReviewView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Review application (approve/reject/waitlist)"""
    permission_required = 'admissions.change_application'
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user can review this application"""
        application_id = kwargs.get('pk')
        application = get_object_or_404(Application, id=application_id)
        
        # Prevent self-review
        if application.created_by_id == request.user.id:
            messages.error(request, 'You cannot review an application you created.')
            return redirect('admissions:detail', pk=application_id)
        
        return super().dispatch(request, *args, **kwargs)
    
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
            
            if not application.invoice_id:
                messages.error(request, 'No invoice found for this application.')
                return redirect('admissions:detail', pk=application_id)
            
            # Delegate to finance app
            from apps.finance.services import PaymentService
            result = PaymentService.initialize_paystack_payment(
                invoice_id=application.invoice_id,
                email=application.email or application.guardian_email
            )
            
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
        
        ref = reference or trxref
        
        if not ref:
            messages.error(request, 'No payment reference provided')
            return redirect('admissions:list')
        
        try:
            from apps.finance.services import PaymentService
            result = PaymentService.verify_paystack_payment(ref)
            
            if result.get('success'):
                invoice_id = result.get('invoice_id')
                if invoice_id:
                    try:
                        application = Application.objects.get(invoice_id=invoice_id)
                        messages.success(request, 'Payment verified successfully!')
                        return redirect('admissions:detail', pk=application.id)
                    except Application.DoesNotExist:
                        messages.warning(request, 'Payment verified but application not found.')
                        return redirect('admissions:list')
                
                messages.success(request, 'Payment verified successfully!')
                return redirect('admissions:list')
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
"""
Public Admissions Views
========================

Applicant-facing portal (no authentication required).

Responsibilities:
- Submit application
- Check application status
- Initialize payment (delegated to finance app)
- Handle payment callback (delegated to finance app)

Architecture:
- Business logic lives in services
- Data retrieval via selectors (read models / dicts)
- Payment handling delegated to finance app
- Views handle HTTP concerns only
"""

import logging
from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, TemplateView, FormView
from django.contrib import messages

from ..services import ApplicationService
from ..selectors import ApplicationSelector
from ..constants import ApplicationStatus
from ..exceptions import (
    AdmissionsClosedError,
    DuplicateApplicationError,
)

from apps.corecode.selectors import (
    StudentClassSelector,
    AcademicSessionSelector,
)
from apps.corecode.services import SiteConfigService
from apps.corecode.constants import SiteConfigKey

# Import finance services for payment handling
from apps.finance.services import PaymentService
from apps.finance.constants import InvoiceStatus

logger = logging.getLogger(__name__)


class PublicApplicationCreateView(FormView):
    """
    Public application form (no login required).
    """

    template_name = "admissions/public/apply.html"
    success_url = reverse_lazy("admissions:public_success")

    fields = [
        "first_name", "last_name", "middle_name",
        "gender", "date_of_birth",
        "email", "phone", "alternate_phone",
        "address", "city", "state_of_origin", "nationality",
        "applying_for_class", "application_type",
        "previous_school", "previous_class",
        "guardian_first_name", "guardian_last_name",
        "guardian_relationship", "guardian_phone",
        "guardian_email", "guardian_address",
        "guardian_occupation",
    ]

    # -------------------------
    # Guard Admissions Status
    # -------------------------

    def dispatch(self, request, *args, **kwargs):
        if not self._admissions_open():
            return redirect("admissions:public_closed")
        return super().dispatch(request, *args, **kwargs)

    def _admissions_open(self) -> bool:
        is_open = SiteConfigService.get_config(
            SiteConfigKey.ADMISSIONS_OPEN, False
        )

        if not is_open:
            logger.info("Admissions attempt while closed.")
            messages.error(self.request, "Admissions are currently closed.")
            return False

        deadline = SiteConfigService.get_config(
            SiteConfigKey.ADMISSION_DEADLINE
        )

        if deadline:
            try:
                deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
                if timezone.now().date() > deadline_date:
                    logger.info("Admissions attempt after deadline.")
                    messages.error(
                        self.request,
                        f"Application deadline ({deadline_date}) has passed."
                    )
                    return False
            except ValueError:
                logger.warning("Invalid ADMISSION_DEADLINE config.")

        return True

    # -------------------------
    # Context
    # -------------------------

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["classes"] = StudentClassSelector.get_all_classes(
            active_only=True
        )

        session = AcademicSessionSelector.get_current_session()
        context["current_session"] = session.name if session else "Not configured"

        context["application_fee"] = SiteConfigService.get_config(
            SiteConfigKey.APPLICATION_FEE, 5000
        )

        return context

    # -------------------------
    # Form Processing
    # -------------------------

    def form_valid(self, form):
        try:
            with transaction.atomic():

                session = AcademicSessionSelector.get_current_session()
                if not session:
                    logger.error("No active academic session configured.")
                    messages.error(
                        self.request,
                        "System configuration error. Try again later."
                    )
                    return self.form_invalid(form)

                application = ApplicationService.create_application(
                    **self._build_application_payload(form)
                )

                logger.info(
                    "Application created",
                    extra={"application_number": application.application_number}
                )

                # Store application number in session for success page
                self.request.session['last_application_number'] = application.application_number

                # Redirect to payment page
                return redirect(
                    "admissions:public_payment",
                    application_number=application.application_number,
                )

        except AdmissionsClosedError as e:
            logger.warning("Admissions closed during submission.")
            messages.error(self.request, str(e))
            return redirect("admissions:public_closed")

        except DuplicateApplicationError as e:
            logger.warning("Duplicate application attempt.")
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        except Exception:
            logger.exception("Unexpected application creation error.")
            messages.error(self.request, "An unexpected error occurred.")
            return self.form_invalid(form)

    def _build_application_payload(self, form):
        cleaned = form.cleaned_data

        return {
            **cleaned,
            "date_of_birth": cleaned["date_of_birth"].isoformat(),
            "applying_for_class_id": cleaned["applying_for_class"].id,
            "created_by_id": None,
        }
        

class PublicApplicationStatusView(TemplateView):
    """
    Allows applicants to check status by:
    - Application number
    - Email
    """

    template_name = "admissions/public/status.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        application_number = kwargs.get("application_number")
        email = self.request.GET.get("email")

        application = None

        if application_number:
            application = ApplicationSelector.get_by_number(application_number)

        elif email:
            apps = ApplicationSelector.list_applications(
                search=email,  # Use search to find by email
                limit=1
            )
            application = apps[0] if apps else None

        context["application"] = application
        context["found"] = bool(application)

        return context
        

class PublicPaymentView(TemplateView):
    """
    Handles payment initialization.
    Delegates to finance app for actual payment processing.
    """

    template_name = "admissions/public/payment.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        app_number = kwargs.get("application_number")
        application = ApplicationSelector.get_by_number(app_number)

        if not application:
            context["error"] = "Application not found"
            return context

        # Check if payment is already completed via invoice
        if application.get("payment_completed"):
            context["already_paid"] = True
            context["invoice_paid"] = True

        # Get invoice details from apps.finance app if invoice exists
        invoice_id = application.get("invoice_id")
        invoice = None
        if invoice_id:
            from apps.finance.selectors import InvoiceSelector
            invoice = InvoiceSelector.get_by_id(invoice_id)

        context.update({
            "application": application,
            "invoice": invoice,
            "paystack_public_key": settings.PAYSTACK_PUBLIC_KEY,
            "amount": invoice.get("total", 5000) if invoice else 5000,
        })

        if context["amount"]:
            context["amount_in_kobo"] = int(context["amount"] * 100)

        return context

    def post(self, request, *args, **kwargs):
        app_number = kwargs.get("application_number")
        application = ApplicationSelector.get_by_number(app_number)

        if not application:
            messages.error(request, "Application not found.")
            return redirect("admissions:public_apply")

        # Check if already paid
        if application.get("payment_completed"):
            messages.info(request, "Payment already completed.")
            return redirect("admissions:public_success",
                            application_number=app_number)

        # Get invoice ID from application
        invoice_id = application.get("invoice_id")
        if not invoice_id:
            messages.error(request, "No invoice found for this application.")
            return redirect("admissions:public_apply")

        try:
            # Delegate to finance app for payment initialization
            result = PaymentService.initialize_paystack_payment(
                invoice_id=invoice_id,
                email=application["email"] or application["guardian_email"]
            )

            logger.info(
                "Payment initialized",
                extra={"application_number": app_number, "invoice_id": invoice_id}
            )

            return redirect(result["authorization_url"])

        except Exception as e:
            logger.exception(f"Payment initialization failed: {e}")
            messages.error(request, f"Unable to initialize payment: {str(e)}")
            return redirect(
                "admissions:public_payment",
                application_number=app_number,
            )
            


class PublicPaymentCallbackView(TemplateView):
    """
    Handles Paystack redirect callback.
    Delegates to finance app for verification.
    """

    def get(self, request, *args, **kwargs):
        reference = request.GET.get("reference") or request.GET.get("trxref")

        if not reference:
            messages.error(request, "Missing payment reference.")
            return redirect("admissions:public_apply")

        try:
            # Delegate to finance app for payment verification
            result = PaymentService.verify_paystack_payment(reference)

            if not result.get("success"):
                messages.error(request, result.get("message", "Verification failed"))
                return redirect("admissions:public_payment_failed")

            # Get the invoice to find associated application
            invoice_id = result.get("invoice_id")
            if invoice_id:
                from admissions.models import Application
                try:
                    application = Application.objects.get(invoice_id=invoice_id)
                    # Auto-submit application after successful payment
                    if application.status == ApplicationStatus.DRAFT:
                        ApplicationService.submit_application(
                            application_id=application.id,
                            submitted_by_id=None  # System submission
                        )
                        logger.info(f"Application {application.application_number} auto-submitted after payment")
                    
                    return redirect(
                        "admissions:public_success",
                        application_number=application.application_number
                    )
                except Application.DoesNotExist:
                    logger.warning(f"No application found for invoice {invoice_id}")
                    messages.error(request, "Application not found.")
                    return redirect("admissions:public_apply")

            messages.success(request, "Payment verified successfully!")
            return redirect("admissions:public_apply")

        except Exception as e:
            logger.exception(f"Payment callback error: {e}")
            messages.error(request, f"Error verifying payment: {str(e)}")
            return redirect("admissions:public_payment_failed")
            

@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(require_http_methods(["POST"]), name="dispatch")
class PaystackWebhookView(View):
    """
    Secure Paystack webhook endpoint.
    Delegates to finance app for processing.
    """

    def post(self, request, *args, **kwargs):
        # Verify signature
        if not PaymentService.verify_webhook(request):
            logger.warning("Invalid webhook signature.")
            return HttpResponse(status=401)

        try:
            import json
            payload = json.loads(request.body)
            event = payload.get("event")

            logger.info(f"Webhook received: {event}")

            # Delegate to finance app for processing
            result = PaymentService.handle_webhook(payload)

            # If payment was successful and we have invoice_id, check for application
            if event == "charge.success" and result.get("success"):
                invoice_id = result.get("invoice_id")
                if invoice_id:
                    from admissions.models import Application
                    try:
                        application = Application.objects.get(invoice_id=invoice_id)
                        if application.status == ApplicationStatus.DRAFT:
                            ApplicationService.submit_application(
                                application_id=application.id,
                                submitted_by_id=None
                            )
                            logger.info(f"Application {application.application_number} auto-submitted via webhook")
                    except Application.DoesNotExist:
                        logger.warning(f"No application found for invoice {invoice_id}")

            return JsonResponse({"status": "success"})

        except Exception as e:
            logger.exception(f"Webhook processing error: {e}")
            return JsonResponse({"status": "error"}, status=200)


class PublicSuccessView(TemplateView):
    """
    Displayed after successful application submission
    and/or successful payment.
    """

    template_name = "admissions/public/success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        application_number = kwargs.get("application_number")

        # Fallback to session
        if not application_number:
            application_number = self.request.session.get(
                "last_application_number"
            )

        if not application_number:
            logger.warning("Success page accessed without application number.")
            context["error"] = "Application not found."
            return context

        application = ApplicationSelector.get_by_number(application_number)

        if not application:
            logger.warning(
                "Invalid application number on success page.",
                extra={"application_number": application_number}
            )
            context["error"] = "Application not found."
            return context

        logger.info(
            "Success page viewed.",
            extra={"application_number": application_number}
        )

        # Clear session
        self.request.session.pop('last_application_number', None)

        context["application"] = application
        context["application_number"] = application_number
        context["payment_completed"] = application.get("payment_completed")

        return context
        
        
class PublicClosedView(TemplateView):
    """
    Shown when admissions are closed.
    """

    template_name = "admissions/public/closed.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        next_admission = SiteConfigService.get_config(
            SiteConfigKey.NEXT_ADMISSION_DATE,
            "To Be Announced"
        )

        logger.info("Admissions closed page viewed.")

        context["next_admission"] = next_admission
        return context
        
        
class PublicPaymentFailedView(TemplateView):
    """
    Shown when payment verification fails
    or user cancels payment.
    """

    template_name = "admissions/public/payment_failed.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        reference = self.request.GET.get("reference")

        logger.warning(
            "Payment failed page viewed.",
            extra={"reference": reference}
        )

        context["reference"] = reference
        return context
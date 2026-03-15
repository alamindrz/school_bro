"""
Public Admissions Views
========================

Applicant-facing portal (no authentication required).

Responsibilities:
- Submit application
- Check application status
- Initialize payment
- Handle payment callback
- Handle Paystack webhook

Architecture:
- Business logic lives in services
- Data retrieval via selectors (read models / dicts)
- Views handle HTTP concerns only
"""

import json
import hmac
import hashlib
import logging
from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, TemplateView, FormView
from django.contrib import messages

from ..models import ApplicationPayment
from ..services import ApplicationService, PaymentService
from ..selectors import ApplicationSelector
from ..constants import ApplicationStatus
from ..exceptions import (
    AdmissionsClosedError,
    DuplicateApplicationError,
    PaymentVerificationError,
)

from apps.corecode.selectors import (
    StudentClassSelector,
    AcademicSessionSelector,
)
from apps.corecode.services import SiteConfigService
from apps.corecode.constants import SiteConfigKey

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
                email=email,
                limit=1
            )
            application = apps[0] if apps else None

        context["application"] = application
        context["found"] = bool(application)

        return context
        

class PublicPaymentView(TemplateView):
    """
    Handles payment initialization.
    """

    template_name = "admissions/public/payment.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        app_number = kwargs.get("application_number")
        application = ApplicationSelector.get_by_number(app_number)

        if not application:
            context["error"] = "Application not found"
            return context

        if application.get("payment", {}).get("status") == "completed":
            context["already_paid"] = True

        context.update({
            "application": application,
            "paystack_public_key": settings.PAYSTACK_PUBLIC_KEY,
            "amount": application.get("payment", {}).get("amount", 5000),
        })

        context["amount_in_kobo"] = int(context["amount"] * 100)

        return context

    def post(self, request, *args, **kwargs):
        app_number = kwargs.get("application_number")
        application = ApplicationSelector.get_by_number(app_number)

        if not application:
            messages.error(request, "Application not found.")
            return redirect("admissions:public_apply")

        if application.get("payment", {}).get("status") == "completed":
            messages.info(request, "Payment already completed.")
            return redirect("admissions:public_success",
                            application_number=app_number)

        try:
            result = PaymentService.initialize_paystack_payment(
                application_id=application["id"],
                email=application["email"],
            )

            logger.info(
                "Payment initialized",
                extra={"application_number": app_number}
            )

            return redirect(result["authorization_url"])

        except Exception:
            logger.exception("Payment initialization failed.")
            messages.error(request, "Unable to initialize payment.")
            return redirect(
                "admissions:public_payment",
                application_number=app_number,
            )
            


class PublicPaymentCallbackView(TemplateView):
    """
    Handles Paystack redirect callback.
    """

    def get(self, request, *args, **kwargs):
        reference = request.GET.get("reference") or request.GET.get("trxref")

        if not reference:
            messages.error(request, "Missing payment reference.")
            return redirect("admissions:public_apply")

        try:
            result = PaymentService.verify_payment(reference)

            if not result.get("success"):
                messages.error(request, result.get("message", "Verification failed"))
                return redirect("admissions:public_payment_failed")

            app_id = result.get("application_id")
            app = ApplicationSelector.get_by_id(app_id)

            logger.info("Payment verified", extra={"reference": reference})

            return redirect(
                "admissions:public_success",
                application_number=app["application_number"],
            )

        except Exception:
            logger.exception("Payment callback error.")
            messages.error(request, "Error verifying payment.")
            return redirect("admissions:public_payment_failed")
            

@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(require_http_methods(["POST"]), name="dispatch")
class PaystackWebhookView(View):
    """
    Secure Paystack webhook endpoint.
    """

    def post(self, request, *args, **kwargs):
        signature = (
            request.headers.get("x-paystack-signature")
            or request.META.get("HTTP_X_PAYSTACK_SIGNATURE")
        )

        if not self._verify_signature(signature, request.body):
            logger.warning("Invalid webhook signature.")
            return HttpResponse(status=401)

        try:
            payload = json.loads(request.body)
            event = payload.get("event")

            logger.info(f"Webhook received: {event}")

            if event == "charge.success":
                return self._handle_success(payload["data"])

            if event == "charge.failed":
                return self._handle_failure(payload["data"])

            return JsonResponse({"status": "ignored"})

        except Exception:
            logger.exception("Webhook processing error.")
            return JsonResponse({"status": "error"}, status=200)

    def _verify_signature(self, signature, payload):
        if not signature or not settings.PAYSTACK_SECRET_KEY:
            return False

        expected = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode(),
            payload,
            hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def _handle_success(self, data):
        reference = data.get("reference")

        try:
            PaymentService.verify_payment(reference)
            return JsonResponse({"status": "success"})
        except Exception:
            logger.exception("Webhook payment verification failed.")
            return JsonResponse({"status": "error"}, status=200)

    def _handle_failure(self, data):
        reference = data.get("reference")

        try:
            payment = ApplicationPayment.objects.get(
                paystack_reference=reference
            )
            payment.mark_failed(data)
        except ApplicationPayment.DoesNotExist:
            logger.warning("Payment record not found.")

        return JsonResponse({"status": "recorded"})
        

class PublicSuccessView(TemplateView):
    """
    Displayed after successful application submission
    and/or successful payment.
    """

    template_name = "admissions/public/success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        application_number = kwargs.get("application_number")

        # Fallback to session (optional convenience only)
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

        context["application"] = application
        context["application_number"] = application_number

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
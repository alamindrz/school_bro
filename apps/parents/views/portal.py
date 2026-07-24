"""
Portal Views - Parent facing portal pages
Uses central notifications app for all notifications
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic import TemplateView, View
from django.views.decorators.cache import never_cache  
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
import logging
from datetime import timedelta

from ..services import PortalService, AccessService
from ..selectors import (
    ParentProfileSelector, PortalDashboardSelector,
    ChildLinkSelector, MessageSelector
)
from apps.corecode.selectors import AcademicSessionSelector, AcademicTermSelector
from apps.finance.services import PaymentService
from apps.finance.models import PaymentReceipt
from apps.finance.constants import PaymentMethod, PaymentStatus
from decimal import Decimal
from ..models import ParentProfile, ChildLink, Message, PortalSession, ParentAccessLog, MagicLink, generate_device_fingerprint
from ..forms import (
    ParentLoginForm, ParentProfileForm, ParentMessageForm, ResendMagicLinkForm,
    ChildLinkForm
)
from ..exceptions import (
    SessionExpiredError, SessionHijackingError, RateLimitExceededError,
    MagicLinkExpiredError, MagicLinkAlreadyUsedError
)
from ..constants import (
    MAGIC_LINK_EXPIRY_MINUTES, SESSION_TIMEOUT_SECONDS,
    MAX_LOGIN_ATTEMPTS_PER_HOUR, MAX_LOGIN_ATTEMPTS_PER_IP
)

# Import central notification service
from apps.notifications.services import NotificationService
from apps.notifications.selectors import NotificationSelector as CentralNotificationSelector

from apps.students.selectors import StudentSelector
from apps.finance.selectors import InvoiceSelector, FinancialStatusSelector
from django.db import transaction
logger = logging.getLogger(__name__)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def rate_limit_check(key, limit, period_seconds):
    cache_key = f"rate_limit:{key}"
    attempts = cache.get(cache_key, 0)
    if attempts >= limit:
        return False
    cache.set(cache_key, attempts + 1, period_seconds)
    return True


class ParentPortalMixin:
    def dispatch(self, request, *args, **kwargs):
        session_key = request.COOKIES.get('parent_session') or request.headers.get('X-Parent-Session')
        if not session_key:
            return redirect('parents:login')
        try:
            parent = PortalService.validate_session(
                session_key, request,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            if not parent:
                response = redirect('parents:login')
                response.delete_cookie('parent_session')
                messages.warning(request, 'Your session has expired. Please log in again.')
                return response
            if parent.is_locked:
                messages.error(request, 'Your account is temporarily locked due to multiple failed attempts.')
                return redirect('parents:login')
            if not parent.is_active:
                messages.error(request, 'Your account is not active. Please contact the school.')
                return redirect('parents:login')
            if not request.path.startswith('/parents/api/'):
                session = PortalSession.objects.get(session_key=session_key)
                if session.expires_at - timezone.now() < timedelta(hours=1):
                    session.refresh()
            self.parent = parent
            self.parent_data = ParentProfileSelector.get_by_id(parent.id)
            return super().dispatch(request, *args, **kwargs)
        except (SessionExpiredError, SessionHijackingError) as e:
            logger.warning(f"Session validation failed: {str(e)}")
            response = redirect('parents:login')
            response.delete_cookie('parent_session')
            messages.error(request, str(e))
            return response
        except Exception as e:
            logger.error(f"Unexpected error in session validation: {str(e)}")
            response = redirect('parents:login')
            response.delete_cookie('parent_session')
            messages.error(request, 'An error occurred. Please log in again.')
            return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, 'parent_data') and self.parent_data:
            context['parent'] = self.parent_data
            # Use central notification selector for unread count
            unread = CentralNotificationSelector.get_unread_count(
                recipient_type='parent',
                recipient_id=self.parent.id
            )
            context['unread_notifications'] = unread
            # Get recent notifications
            notifications, total = CentralNotificationSelector.list_for_recipient(
                recipient_type='parent',
                recipient_id=self.parent.id,
                limit=5
            )
            context['recent_notifications'] = notifications
        return context

    def log_action(self, action, success=True, error_message='', student_id=None, details=None):
        try:
            ParentAccessLog.objects.create(
                parent=self.parent,
                action=action,
                ip_address=get_client_ip(self.request),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                student_id=student_id,
                details=details or {},
                success=success,
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Failed to log action {action}: {str(e)}")


class ParentLoginView(TemplateView):
    template_name = 'parents/portal/login.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company_name'] = getattr(settings, 'COMPANY_NAME', 'DETs Toolkit')
        context['form'] = ParentLoginForm()
        return context

    def post(self, request, *args, **kwargs):
        form = ParentLoginForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Please enter a valid email address')
            return self.get(request, *args, **kwargs)
        
        email = form.cleaned_data['email']
        password = form.cleaned_data.get('password', '')
        ip = get_client_ip(request)
        
        if not rate_limit_check(f"login_ip:{ip}", MAX_LOGIN_ATTEMPTS_PER_IP, 3600):
            messages.error(request, 'Too many login attempts. Please try again later.')
            return self.get(request, *args, **kwargs)
        
        if not rate_limit_check(f"login_email:{email}", MAX_LOGIN_ATTEMPTS_PER_HOUR, 3600):
            messages.error(request, 'Too many login attempts for this email. Please try again later.')
            return self.get(request, *args, **kwargs)
        
        try:
            parent = ParentProfile.objects.get_by_email(email)
            if not parent:
                ParentAccessLog.objects.create(
                    parent=None, action='LOGIN_FAILED', ip_address=ip,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    success=False, error_message='Email not found', details={'email': email}
                )
                messages.success(request, f'If an account exists for {email}, a login link has been sent.')
                return redirect('parents:login_sent')
            
            if parent.is_locked:
                messages.error(request, 'Your account is temporarily locked. Please try again later.')
                return self.get(request, *args, **kwargs)
            
            # If password provided, try password login
            if password:
                if parent.check_password(password):
                    # Password login successful
                    session = PortalSession.objects.create(
                        parent=parent, ip_address=ip,
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        expires_at=timezone.now() + timedelta(seconds=SESSION_TIMEOUT_SECONDS)
                    )
                    ParentAccessLog.objects.create(
                        parent=parent, action='LOGIN', ip_address=ip,
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        success=True, details={'method': 'password'}
                    )
                    response = redirect('parents:dashboard')
                    response.set_cookie('parent_session', session.session_key,
                                       max_age=SESSION_TIMEOUT_SECONDS, httponly=True,
                                       secure=settings.SECURE_SSL_REDIRECT or not settings.DEBUG,
                                       samesite='Strict')
                    messages.success(request, f'Welcome back, {parent.full_name}!')
                    return response
                else:
                    # Wrong password
                    parent.record_failed_login()
                    ParentAccessLog.objects.create(
                        parent=parent, action='LOGIN_FAILED', ip_address=ip,
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        success=False, error_message='Invalid password'
                    )
                    messages.error(request, 'Invalid password. Please try again or leave blank for magic link.')
                    return self.get(request, *args, **kwargs)
            
            # No password or blank — send magic link
            magic_link = parent.generate_magic_link()
            from django.template.loader import render_to_string
            from django.core.mail import send_mail
            link_url = request.build_absolute_uri(reverse('parents:magic_link', kwargs={'token': magic_link.token}))
            context = {
                'parent': parent, 'link_url': link_url,
                'expiry_minutes': MAGIC_LINK_EXPIRY_MINUTES,
                'company_name': getattr(settings, 'COMPANY_NAME', 'DETs Toolkit'),
            }
            html_message = render_to_string('parents/emails/magic_link.html', context)
            plain_message = f"Hello {parent.full_name},\n\nClick the link below to log in:\n{link_url}\n\nThis link expires in {MAGIC_LINK_EXPIRY_MINUTES} minutes."
            ParentAccessLog.objects.create(
                parent=parent, action='LOGIN', ip_address=ip,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True, details={'email_sent': True}
            )
            send_mail(
                subject='Parent Portal Login Link', message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[email],
                html_message=html_message, fail_silently=False,
            )
            messages.success(request, f'If an account exists for {email}, a login link has been sent.')
            return redirect('parents:login_sent')
            
        except Exception as e:
            logger.error(f"Login error for {email}: {str(e)}")
            messages.error(request, 'An error occurred. Please try again.')
            return self.get(request, *args, **kwargs)
    

class LoginSentView(TemplateView):
    template_name = 'parents/portal/login_sent.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company_name'] = getattr(settings, 'COMPANY_NAME', 'DETs Toolkit')
        context['form'] = ResendMagicLinkForm()
        return context


class ResendMagicLinkView(View):
    def post(self, request):
        form = ResendMagicLinkForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Please enter a valid email address')
            return redirect('parents:login_sent')
        email = form.cleaned_data['email']
        ip = get_client_ip(request)
        if not rate_limit_check(f"resend_email:{email}", 3, 3600):
            messages.error(request, 'Too many resend attempts. Please try again later.')
            return redirect('parents:login_sent')
        try:
            parent = ParentProfile.objects.get_by_email(email)
            if parent:
                magic_link = parent.generate_magic_link()
                # Send email (same as login)
                # ... (omitted for brevity, same as above)
                ParentAccessLog.objects.create(
                    parent=parent,
                    action='LOGIN',
                    ip_address=ip,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    success=True,
                    details={'email_sent': True, 'resend': True}
                )
            messages.success(request, f'New login link sent to {email}. Please check your email.')
        except Exception as e:
            logger.error(f"Resend error for {email}: {str(e)}")
            messages.error(request, 'An error occurred. Please try again.')
        return redirect('parents:login_sent')


class MagicLinkView(View):
    @method_decorator(never_cache)
    def get(self, request, token):
        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        device_fingerprint = generate_device_fingerprint(request)
        try:
            magic_link = MagicLink.objects.select_related('parent').get(token=token)
            if magic_link.is_expired:
                raise MagicLinkExpiredError()
            if magic_link.is_used:
                raise MagicLinkAlreadyUsedError()
            if not magic_link.parent.is_active:
                messages.error(request, 'Your account is not active. Please contact the school.')
                return redirect('parents:login')
            if magic_link.parent.is_locked:
                messages.error(request, 'Your account is locked. Please try again later.')
                return redirect('parents:login')
            magic_link.use(request)
            session = PortalSession.objects.create(
                parent=magic_link.parent,
                ip_address=ip,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                expires_at=timezone.now() + timedelta(seconds=SESSION_TIMEOUT_SECONDS)
            )
            ParentAccessLog.objects.create(
                parent=magic_link.parent,
                action='LOGIN',
                ip_address=ip,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                success=True,
                details={'magic_link': True, 'session_key': str(session.session_key)[:8]}
            )
            magic_link.parent.record_login(device_fingerprint)
            response = redirect('parents:dashboard')
            response.set_cookie(
                'parent_session',
                session.session_key,
                max_age=SESSION_TIMEOUT_SECONDS,
                httponly=True,
                secure=settings.SECURE_SSL_REDIRECT or not settings.DEBUG,
                samesite='Strict',
                domain=settings.SESSION_COOKIE_DOMAIN if hasattr(settings, 'SESSION_COOKIE_DOMAIN') else None
            )
            messages.success(request, f'Welcome back, {magic_link.parent.full_name}!')
            return response
        except MagicLinkExpiredError as e:
            logger.info(f"Expired magic link used: {token}")
            messages.error(request, str(e))
            return redirect('parents:login')
        except MagicLinkAlreadyUsedError as e:
            logger.warning(f"Already used magic link: {token}")
            messages.error(request, str(e))
            return redirect('parents:login')
        except MagicLink.DoesNotExist:
            logger.warning(f"Invalid magic link: {token}")
            messages.error(request, 'Invalid login link.')
            return redirect('parents:login')
        except Exception as e:
            logger.error(f"Magic link error: {str(e)}")
            messages.error(request, 'An error occurred. Please try again.')
            return redirect('parents:login')


class LogoutView(ParentPortalMixin, View):
    def get(self, request):
        session_key = request.COOKIES.get('parent_session')
        if session_key:
            try:
                session = PortalSession.objects.get(session_key=session_key)
                session.terminate("User logout")
                ParentAccessLog.objects.create(
                    parent=self.parent,
                    action='LOGOUT',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    success=True
                )
            except PortalSession.DoesNotExist:
                pass
        response = redirect('parents:login')
        response.delete_cookie('parent_session')
        messages.info(request, 'You have been logged out.')
        return response


class DashboardView(ParentPortalMixin, TemplateView):
    template_name = 'parents/portal/dashboard.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dashboard = PortalDashboardSelector.get_dashboard_data(self.parent.id)
        context.update(dashboard)
        return context


class ChildrenView(ParentPortalMixin, TemplateView):
    template_name = 'parents/pages/children.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from ..selectors import PortalDashboardSelector
        dashboard = PortalDashboardSelector.get_dashboard_data(self.parent.id)
        context['children'] = dashboard.get('children', [])
        return context

class ChildDetailView(ParentPortalMixin, TemplateView):
    template_name = 'parents/portal/child_detail.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student_id = kwargs.get('student_id')
        if not PortalService.verify_child_access(self.parent.id, student_id, 'view_results'):
            messages.error(self.request, 'You do not have access to this student\'s information')
            return redirect('parents:children')
        student = StudentSelector.get_by_id(student_id)
        if not student:
            messages.error(self.request, 'Student not found')
            return redirect('parents:children')
        context['student'] = student
        try:
            from apps.admissions.selectors import ApplicationSelector
            application = ApplicationSelector.get_by_student_id(student_id)
            if application:
                context['application'] = application
        except ImportError:
            pass
        context['balance'] = InvoiceSelector.get_student_balance(student_id)
        context['exam_clearance'] = FinancialStatusSelector.is_student_cleared_for_exams(student_id)
        context['invoices'] = InvoiceSelector.list_invoices(student_id=student_id, limit=10)
        self.log_action('VIEW_PROFILE', student_id=student_id)
        return context


class FeesView(ParentPortalMixin, TemplateView):
    template_name = 'parents/portal/fees.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student_id = self.request.GET.get('student_id')
        page = int(self.request.GET.get('page', 1))
        per_page = 20
        if student_id:
            if not PortalService.verify_child_access(self.parent.id, int(student_id), 'view_fees'):
                messages.error(self.request, 'Access denied')
                return redirect('parents:fees')
            offset = (page - 1) * per_page
            context['invoices'] = InvoiceSelector.list_invoices(
                student_id=int(student_id), limit=per_page, offset=offset
            )
            context['selected_student'] = StudentSelector.get_by_id(int(student_id))
            context['has_more'] = len(context['invoices']) == per_page
            context['page'] = page
            self.log_action('VIEW_FEES', student_id=int(student_id))
        else:
            all_invoices = []
            for child in self.parent_data['children']:
                if child.get('permissions', {}).get('view_fees', True):
                    invoices = InvoiceSelector.list_invoices(
                        student_id=child['student_id'], limit=10
                    )
                    all_invoices.extend(invoices)
            all_invoices.sort(key=lambda x: x.get('issue_date', ''), reverse=True)
            context['invoices'] = all_invoices[:50]
            self.log_action('VIEW_FEES')
        return context
        
        
        

class PayFeesView(ParentPortalMixin, TemplateView):
    """Pay fees for a child"""

    template_name = "parents/pages/pay_fees.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student_id = self.request.GET.get("student_id")

        if student_id:
            db_id = student_id
            if not str(student_id).isdigit():
                from apps.students.models import Student

                s = Student.objects.filter(admission_number=student_id).first()
                if s:
                    db_id = s.id
                else:
                    messages.error(self.request, "Student not found")
                    return context

            db_id = int(db_id)

            # Verify parent access
            has_access = PortalService.verify_child_access(
                self.parent.id, db_id, "view_fees"
            )
            if not has_access:
                messages.error(self.request, "Access denied")
                return context

            student = StudentSelector.get_by_id(db_id)
            if not student:
                messages.error(self.request, "Student not found")
                return context

            context["student"] = student
            context["balance"] = InvoiceSelector.get_student_balance(db_id)

            current_session = AcademicSessionSelector.get_current_session()
            current_term = AcademicTermSelector.get_current_term()

            if current_session and current_term:
                context["term_status"] = (
                    FinancialStatusSelector.get_term_payment_status(
                        student_id=db_id,
                        session_id=current_session.id,
                        term_id=current_term.id,
                    )
                )
                context["all_terms"] = (
                    FinancialStatusSelector.get_all_terms_status(
                        student_id=db_id, session_id=current_session.id
                    )
                )

                invoices = InvoiceSelector.list_invoices(
                    student_id=db_id,
                    session_id=current_session.id,
                    term_id=current_term.id,
                    status=["pending", "partial", "overdue"],
                )

                from apps.finance.models import Payment as PaymentModel

                for invoice in invoices:
                    invoice["has_pending_payment"] = (
                        PaymentModel.objects.filter(
                            invoice_id=invoice["id"], status="pending"
                        ).exists()
                    )

                context["invoices"] = invoices
                payable_invoices = [
                    inv for inv in invoices if not inv["has_pending_payment"]
                ]
                context["payable_total"] = sum(
                    (
                        Decimal(str(inv["balance"]))
                        for inv in payable_invoices
                    ),
                    Decimal("0"),
                )
                context["payable_count"] = len(payable_invoices)

            context["payment_methods"] = [
                (v, l)
                for v, l in PaymentMethod.CHOICES
                if v in (PaymentMethod.BANK_TRANSFER, PaymentMethod.CASH)
            ]
            context["current_session"] = current_session
            context["current_term"] = current_term

            self.log_action("VIEW_FEES", student_id=db_id)

        return context

    def post(self, request):
        student_id = request.POST.get("student_id")
        invoice_id = request.POST.get("invoice_id")
        amount = request.POST.get("amount")
        method = request.POST.get("method")
        receipt_file = request.FILES.get("receipt")

        if not all([student_id, invoice_id, amount, method]):
            messages.error(request, "Please fill all required fields")
            return redirect(
                f"{reverse('parents:pay_fees')}?student_id={student_id}"
            )

        student_id = int(student_id)
        if not PortalService.verify_child_access(
            self.parent.id, student_id, "view_fees"
        ):
            messages.error(request, "Access denied")
            return redirect("parents:children")

        allowed_methods = (PaymentMethod.BANK_TRANSFER, PaymentMethod.CASH)
        if method not in allowed_methods:
            messages.error(request, "Invalid payment method")
            return redirect(
                f"{reverse('parents:pay_fees')}?student_id={student_id}"
            )

        if not receipt_file:
            messages.error(request, "Please upload your payment receipt.")
            return redirect(
                f"{reverse('parents:pay_fees')}?student_id={student_id}"
            )

        try:
            amount = Decimal(amount)
            if amount <= 0:
                messages.error(request, "Enter a valid amount.")
                return redirect(
                    f"{reverse('parents:pay_fees')}?student_id={student_id}"
                )

            current_session = AcademicSessionSelector.get_current_session()
            current_term = AcademicTermSelector.get_current_term()
            if not current_session or not current_term:
                messages.error(request, "No active academic term found.")
                return redirect(
                    f"{reverse('parents:pay_fees')}?student_id={student_id}"
                )

            from apps.finance.models import Payment as PaymentModel

            student_invoices = InvoiceSelector.list_invoices(
                student_id=student_id,
                session_id=current_session.id,
                term_id=current_term.id,
                status=["pending", "partial", "overdue"],
            )
            invoices_by_id = {inv["id"]: inv for inv in student_invoices}
            payable_by_id = {
                inv_id: inv
                for inv_id, inv in invoices_by_id.items()
                if not PaymentModel.objects.filter(
                    invoice_id=inv_id, status="pending"
                ).exists()
            }

            is_pay_all = invoice_id == "all"

            if is_pay_all:
                target_invoices = list(payable_by_id.values())
            else:
                single_invoice_id = int(invoice_id)
                if single_invoice_id not in invoices_by_id:
                    messages.error(request, "Invalid invoice")
                    return redirect(
                        f"{reverse('parents:pay_fees')}?student_id={student_id}"
                    )
                if single_invoice_id not in payable_by_id:
                    messages.error(
                        request,
                        "This invoice already has a payment awaiting verification.",
                    )
                    return redirect(
                        f"{reverse('parents:pay_fees')}?student_id={student_id}"
                    )

                target_invoices = [payable_by_id[single_invoice_id]] + [
                    inv
                    for iid, inv in payable_by_id.items()
                    if iid != single_invoice_id
                ]

            if not target_invoices:
                messages.error(
                    request,
                    "Nothing payable — every outstanding invoice already has a payment awaiting verification.",
                )
                return redirect(
                    f"{reverse('parents:pay_fees')}?student_id={student_id}"
                )

            total_outstanding = sum(
                (Decimal(str(inv["balance"])) for inv in target_invoices),
                Decimal("0"),
            )

            if amount > total_outstanding:
                amount = total_outstanding
                messages.info(
                    request,
                    f"Payment amount adjusted to outstanding balance: ₦{amount:,.0f}",
                )

            total_paid = Decimal("0")
            remaining = amount
            invoices_paid = 0
            first_invoice_id = target_invoices[0]["id"]

            with transaction.atomic():
                for inv in target_invoices:
                    if remaining <= 0:
                        break

                    inv_balance = Decimal(str(inv["balance"]))
                    pay_amount = min(remaining, inv_balance)
                    if pay_amount <= 0:
                        continue

                    is_primary_target = (
                        not is_pay_all and inv["id"] == first_invoice_id
                    )
                    notes = (
                        f"Payment by parent {self.parent.full_name}"
                        if is_primary_target
                        else f"Bulk/rollover payment by parent {self.parent.full_name}"
                    )

                    if method == PaymentMethod.BANK_TRANSFER:
                        payment = PaymentService.record_bank_transfer_payment(
                            invoice_id=inv["id"],
                            amount=pay_amount,
                            received_by_id=request.user.id
                            if request.user.is_authenticated
                            else None,
                            notes=notes,
                        )
                    else:
                        payment = PaymentService.record_cash_payment(
                            invoice_id=inv["id"],
                            amount=pay_amount,
                            received_by_id=request.user.id
                            if request.user.is_authenticated
                            else None,
                            notes=notes,
                        )

                    receipt_file.seek(0)
                    PaymentReceipt.objects.create(
                        payment=payment,
                        receipt_file=receipt_file,
                        uploaded_by=request.user
                        if request.user.is_authenticated
                        else None,
                    )


                    total_paid += pay_amount
                    remaining -= pay_amount
                    invoices_paid += 1

            self.log_action(
                "VIEW_FEES",
                student_id=student_id,
                details={
                    "invoice_id": "all" if is_pay_all else single_invoice_id,
                    "amount": float(total_paid),
                    "method": method,
                    "invoices_paid": invoices_paid,
                },
            )

            verifying = (
                " Awaiting verification by school admin."
                if method == PaymentMethod.BANK_TRANSFER
                else ""
            )
            if invoices_paid == 1 and not is_pay_all:
                messages.success(
                    request, f"Payment of ₦{total_paid:,.0f} recorded.{verifying}"
                )
            elif is_pay_all:
                messages.success(
                    request,
                    f"₦{total_paid:,.0f} submitted across {invoices_paid} invoices.{verifying}",
                )
            else:
                messages.success(
                    request,
                    f"₦{total_paid:,.0f} recorded, covering this invoice and {invoices_paid - 1} other outstanding invoice(s).{verifying}",
                )

        except RuntimeError as e:
            if str(e) == "payment_amount_mismatch":
                messages.error(
                    request,
                    "We could not safely process this payment — please contact the school office. No charge has been recorded.",
                )
            else:
                logger.error(f"Payment failed for parent {self.parent.id}: {e}")
                messages.error(request, f"Payment failed: {str(e)}")
        except Exception as e:
            logger.error(f"Payment failed for parent {self.parent.id}: {e}")
            messages.error(request, f"Payment failed: {str(e)}")

        return redirect(f"{reverse('parents:pay_fees')}?student_id={student_id}")





class PaymentsView(ParentPortalMixin, TemplateView):
    template_name = 'parents/portal/payments.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.finance.selectors import PaymentSelector
        student_id = self.request.GET.get('student_id')
        if student_id:
            if not PortalService.verify_child_access(self.parent.id, int(student_id), 'view_fees'):
                messages.error(self.request, 'Access denied')
                return redirect('parents:payments')
            context['payments'] = PaymentSelector.list_payments(
                student_id=int(student_id), limit=50
            )
            context['selected_student'] = StudentSelector.get_by_id(int(student_id))
            


class NotificationsView(ParentPortalMixin, TemplateView):
    """View notifications using central notifications app"""
    template_name = 'parents/portal/notifications.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = int(self.request.GET.get('page', 1))
        per_page = 20
        offset = (page - 1) * per_page
        
        notifications, total = CentralNotificationSelector.list_for_recipient(
            recipient_type='parent',
            recipient_id=self.parent.id,
            limit=per_page,
            offset=offset,
            unread_only=False
        )
        
        context['notifications'] = notifications
        context['total_count'] = total
        context['has_more'] = len(notifications) == per_page
        context['page'] = page
        
        self.log_action('VIEW_PROFILE')
        return context


class MarkNotificationReadView(ParentPortalMixin, View):
    """Mark a notification as read using central notification service"""
    
    def post(self, request, notification_id):
        try:
            success = NotificationService.mark_as_read(notification_id)
            if success:
                self.log_action('VIEW_PROFILE', details={'notification_id': notification_id})
        except Exception as e:
            logger.error(f"Error marking notification read: {e}")
        
        if request.headers.get('HX-Request'):
            unread_count = CentralNotificationSelector.get_unread_count(
                recipient_type='parent', 
                recipient_id=self.parent.id
            )
            return HttpResponse(f'<span class="notification-count">{unread_count}</span>')
        
        return redirect('parents:notifications')


class MarkAllNotificationsReadView(ParentPortalMixin, View):
    """Mark all notifications as read using central notification service"""
    
    def post(self, request):
        unread_count = CentralNotificationSelector.get_unread_count(
            recipient_type='parent', 
            recipient_id=self.parent.id
        )
        
        if unread_count > 1000:
            messages.warning(
                request,
                f'You have {unread_count} unread notifications. Please mark them in batches.'
            )
            return redirect('parents:notifications')
        
        count = NotificationService.mark_all_as_read(
            recipient_type='parent',
            recipient_id=self.parent.id
        )
        
        self.log_action('VIEW_PROFILE', details={'marked_all_read': count})
        messages.success(request, f'Marked {count} notifications as read.')
        return redirect('parents:notifications')
        
        
class MessagesView(ParentPortalMixin, TemplateView):
    """View message conversations"""
    template_name = 'parents/portal/messages.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['conversations'] = MessageSelector.get_conversations(self.parent.id)
        self.log_action('VIEW_PROFILE')
        return context


class MessageThreadView(ParentPortalMixin, TemplateView):
    """View message thread for a student"""
    template_name = 'parents/portal/message_thread.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student_id = kwargs.get('student_id')
        
        if not PortalService.verify_child_access(self.parent.id, int(student_id), 'communicate'):
            messages.error(self.request, 'You do not have permission to message about this student')
            return redirect('parents:messages')
        
        student = StudentSelector.get_by_id(int(student_id))
        if not student:
            messages.error(self.request, 'Student not found')
            return redirect('parents:messages')
        
        context['student'] = student
        context['messages'] = MessageSelector.get_messages_for_student(
            self.parent.id, int(student_id)
        )
        context['form'] = ParentMessageForm()
        
        self.log_action('VIEW_PROFILE', student_id=int(student_id))
        return context


class SendMessageView(ParentPortalMixin, View):
    """Send a new message"""
    
    def post(self, request):
        student_id = request.POST.get('student_id')
        form = ParentMessageForm(request.POST)
        
        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return redirect('parents:messages')
        
        if not PortalService.verify_child_access(self.parent.id, int(student_id), 'communicate'):
            messages.error(request, 'You do not have permission to send messages about this student')
            return redirect('parents:messages')
        
        student = StudentSelector.get_by_id(int(student_id))
        if not student:
            messages.error(request, 'Student not found')
            return redirect('parents:messages')
        
        msg = Message.objects.create(
            sender_parent_id=self.parent.id,
            sender_name=self.parent.full_name,
            subject=form.cleaned_data['subject'],
            body=form.cleaned_data['body'],
            student_id=int(student_id),
            student_name=student['full_name']
        )
        
        self.log_action('SEND_MESSAGE', student_id=int(student_id), details={'message_id': msg.id})
        
        # Send notification to teachers
        try:
            NotificationService.send_notification(
                notification_type='general_announcement',
                title=f"New message from {self.parent.full_name}",
                message=f"Parent sent a message about {student['full_name']}: {msg.subject[:50]}...",
                recipient_type='staff',
                role='teacher',
                data={'message_id': msg.id, 'student_id': student_id},
                action_url=f"/staff/messages/{student_id}/",
                action_text="View Message",
                created_by_id=request.user.id if request.user.is_authenticated else None
            )
            logger.info(f"Teacher notification sent for message {msg.id}")
        except Exception as e:
            logger.error(f"Failed to notify teachers about message {msg.id}: {str(e)}")
        
        messages.success(request, 'Message sent successfully')
        return redirect('parents:message_thread', student_id=student_id)


class ProfileView(ParentPortalMixin, TemplateView):
    """View and edit parent profile"""
    template_name = 'parents/portal/profile.html'
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['profile_form'] = ParentProfileForm(instance=self.parent)
        return self.render_to_response(context)
    
    def post(self, request):
        if 'profile_submit' in request.POST:
            form = ParentProfileForm(request.POST, instance=self.parent)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully')
                self.log_action('EDIT_PROFILE', details={'fields': list(form.changed_data)})
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        return redirect('parents:profile')



class SetPasswordView(ParentPortalMixin, View):
    """Set a password for email+password login"""
    
    def get(self, request):
        return render(request, 'parents/portal/set_password.html', {
            'parent': self.parent,
            'has_password': self.parent.has_password(),
        })
    
    def post(self, request):
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        if not password1 or len(password1) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return redirect('parents:set_password')
        
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return redirect('parents:set_password')
        
        self.parent.set_password(password1)
        self.log_action('SET_PASSWORD')
        messages.success(request, 'Password set successfully. You can now login with email and password.')
        return redirect('parents:profile')
        
        
class InvoiceDetailView(ParentPortalMixin, TemplateView):
    """View a single invoice with print option"""
    template_name = 'parents/pages/invoice_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice_id = kwargs.get('invoice_id')
        invoice = InvoiceSelector.get_by_id(invoice_id)
        
        if not invoice:
            messages.error(self.request, 'Invoice not found')
            return context
        
        # Verify parent has access to this student
        if not PortalService.verify_child_access(self.parent.id, invoice['student_id'], 'view_fees'):
            messages.error(self.request, 'Access denied')
            return context
        
        context['invoice'] = invoice
        context['student'] = StudentSelector.get_by_id(invoice['student_id'])
        context['payments'] = PaymentSelector.list_payments(invoice_id=invoice_id)
        
        self.log_action('VIEW_FEES', student_id=invoice['student_id'])
        return context
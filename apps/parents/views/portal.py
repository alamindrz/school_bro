"""
Portal Views - Parent facing portal pages
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import TemplateView, View, FormView
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import login
import logging

from ..services import PortalService, NotificationService, AccessService
from ..selectors import (
    ParentProfileSelector, PortalDashboardSelector,
    NotificationSelector, MessageSelector
)
from ..models import ParentProfile, ChildLink, Message
from ..exceptions import ParentNotFoundError, PortalAccessError

from apps.students.selectors import StudentSelector
from apps.finance.selectors import InvoiceSelector, FinancialStatusSelector

logger = logging.getLogger(__name__)


class ParentPortalMixin:
    """Mixin to verify parent portal access"""
    
    def dispatch(self, request, *args, **kwargs):
        # Check for session in cookie or header
        session_key = request.COOKIES.get('parent_session') or request.headers.get('X-Parent-Session')
        
        if not session_key:
            return redirect('parents:login')
        
        # Validate session
        parent = AccessService.validate_magic_link(session_key, request.META.get('REMOTE_ADDR'))
        
        if not parent:
            response = redirect('parents:login')
            response.delete_cookie('parent_session')
            return response
        
        self.parent = parent
        self.parent_data = ParentProfileSelector.get_by_id(parent.id)
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent'] = self.parent_data
        context['unread_notifications'] = NotificationSelector.get_unread_count(self.parent.id)
        return context


class ParentLoginView(TemplateView):
    """Parent portal login page"""
    template_name = 'parents/portal/login.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company_name'] = getattr(settings, 'COMPANY_NAME', 'DETs Toolkit')
        return context
    
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        
        if not email:
            messages.error(request, 'Please enter your email address')
            return self.get(request, *args, **kwargs)
        
        try:
            # Find parent by email
            parent = ParentProfile.objects.get(email=email)
            
            # Generate and send magic link
            success = AccessService.send_magic_link_email(
                parent_id=parent.id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            if success:
                messages.success(
                    request,
                    f'A login link has been sent to {email}. Please check your email.'
                )
                return redirect('parents:login_sent')
            else:
                messages.error(request, 'Failed to send login link. Please try again.')
                
        except ParentProfile.DoesNotExist:
            # Don't reveal that email doesn't exist for security
            messages.success(
                request,
                f'If an account exists for {email}, a login link has been sent.'
            )
            return redirect('parents:login_sent')
        
        return self.get(request, *args, **kwargs)


class LoginSentView(TemplateView):
    """Page shown after login email sent"""
    template_name = 'parents/portal/login_sent.html'


class MagicLinkView(View):
    """Handle magic link login"""
    
    def get(self, request, session_key):
        parent = AccessService.validate_magic_link(
            session_key,
            request.META.get('REMOTE_ADDR')
        )
        
        if parent:
            # Set session cookie
            response = redirect('parents:dashboard')
            response.set_cookie(
                'parent_session',
                session_key,
                max_age=24*60*60,  # 24 hours
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Lax'
            )
            
            messages.success(request, f'Welcome back, {parent.full_name}!')
            return response
        else:
            messages.error(request, 'This login link has expired or is invalid.')
            return redirect('parents:login')


class LogoutView(View):
    """Parent portal logout"""
    
    def get(self, request):
        session_key = request.COOKIES.get('parent_session')
        
        if session_key:
            AccessService.logout(session_key)
        
        response = redirect('parents:login')
        response.delete_cookie('parent_session')
        messages.info(request, 'You have been logged out.')
        return response


class DashboardView(ParentPortalMixin, TemplateView):
    """Parent portal dashboard"""
    template_name = 'parents/portal/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get dashboard data
        dashboard = PortalDashboardSelector.get_dashboard_data(self.parent.id)
        context.update(dashboard)
        
        return context


class ChildrenView(ParentPortalMixin, TemplateView):
    """View all children"""
    template_name = 'parents/portal/children.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['children'] = self.parent_data['children']
        return context


class ChildDetailView(ParentPortalMixin, TemplateView):
    """View details for a specific child"""
    template_name = 'parents/portal/child_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        student_id = kwargs.get('student_id')
        
        # Verify access
        if not PortalService.verify_child_access(self.parent.id, student_id, 'view_results'):
            messages.error(self.request, 'You do not have access to this student\'s information')
            return redirect('parents:children')
        
        # Get student data
        student = StudentSelector.get_by_id(student_id)
        if not student:
            messages.error(self.request, 'Student not found')
            return redirect('parents:children')
        
        context['student'] = student
        
        # ADD THIS: Get application status
        from apps.admissions.selectors import ApplicationSelector
        application = ApplicationSelector.get_by_student_id(student_id)
        if application:
            context['application'] = application
        
        # Get financial data
        from apps.finance.selectors import InvoiceSelector
        context['balance'] = InvoiceSelector.get_student_balance(student_id)
        context['exam_clearance'] = FinancialStatusSelector.is_student_cleared_for_exams(student_id)
        context['invoices'] = InvoiceSelector.list_invoices(student_id=student_id, limit=10)
        
        return context


class FeesView(ParentPortalMixin, TemplateView):
    """View fee statements"""
    template_name = 'parents/portal/fees.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        student_id = self.request.GET.get('student_id')
        
        if student_id:
            # Verify access
            if not PortalService.verify_child_access(self.parent.id, int(student_id), 'view_fees'):
                messages.error(self.request, 'Access denied')
                return redirect('parents:fees')
            
            # Get invoices for specific student
            context['invoices'] = InvoiceSelector.list_invoices(
                student_id=int(student_id),
                limit=50
            )
            context['selected_student'] = StudentSelector.get_by_id(int(student_id))
        else:
            # Get all invoices for all children
            all_invoices = []
            for child in self.parent_data['children']:
                # Check permission safely
                if child.get('permissions', {}).get('view_fees', True):
                    invoices = InvoiceSelector.list_invoices(
                        student_id=child['student_id'],
                        limit=20
                    )
                    all_invoices.extend(invoices)
            
            # Sort by date
            all_invoices.sort(key=lambda x: x.get('issue_date', ''), reverse=True)
            context['invoices'] = all_invoices[:50]
        
        return context

class PaymentsView(ParentPortalMixin, TemplateView):
    """View payment history"""
    template_name = 'parents/portal/payments.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from apps.finance.selectors import PaymentSelector
        
        student_id = self.request.GET.get('student_id')
        
        if student_id:
            # Verify access
            if not PortalService.verify_child_access(self.parent.id, int(student_id), 'view_fees'):
                messages.error(self.request, 'Access denied')
                return redirect('parents:payments')
            
            # Get payments for specific student
            context['payments'] = PaymentSelector.list_payments(
                student_id=int(student_id),
                limit=50
            )
            context['selected_student'] = StudentSelector.get_by_id(int(student_id))
        else:
            # Get all payments for all children
            all_payments = []
            for child in self.parent_data['children']:
                if child['permissions']['view_fees']:
                    payments = PaymentSelector.list_payments(
                        student_id=child['student_id'],
                        limit=20
                    )
                    all_payments.extend(payments)
            
            # Sort by date
            all_payments.sort(key=lambda x: x['payment_date'] or '', reverse=True)
            context['payments'] = all_payments[:50]
        
        return context


class NotificationsView(ParentPortalMixin, TemplateView):
    """View all notifications"""
    template_name = 'parents/portal/notifications.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['notifications'] = NotificationSelector.get_for_parent(
            self.parent.id,
            limit=100
        )
        
        return context


class MarkNotificationReadView(ParentPortalMixin, View):
    """Mark a notification as read"""
    
    def post(self, request, notification_id):
        success = NotificationService.mark_as_read(notification_id, self.parent.id)
        
        if request.headers.get('HX-Request'):
            # HTMX request - return updated count
            unread_count = NotificationSelector.get_unread_count(self.parent.id)
            return HttpResponse(f'<span class="notification-count">{unread_count}</span>')
        
        return redirect('parents:notifications')


class MarkAllNotificationsReadView(ParentPortalMixin, View):
    """Mark all notifications as read"""
    
    def post(self, request):
        count = NotificationService.mark_all_as_read(self.parent.id)
        messages.success(request, f'Marked {count} notifications as read.')
        return redirect('parents:notifications')


class MessagesView(ParentPortalMixin, TemplateView):
    """View message conversations"""
    template_name = 'parents/portal/messages.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['conversations'] = MessageSelector.get_conversations(self.parent.id)
        
        return context


class MessageThreadView(ParentPortalMixin, TemplateView):
    """View message thread for a student"""
    template_name = 'parents/portal/message_thread.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        student_id = kwargs.get('student_id')
        
        # Verify access
        if not PortalService.verify_child_access(self.parent.id, int(student_id), 'communicate'):
            messages.error(self.request, 'You do not have permission to message about this student')
            return redirect('parents:messages')
        
        student = StudentSelector.get_by_id(int(student_id))
        if not student:
            messages.error(self.request, 'Student not found')
            return redirect('parents:messages')
        
        context['student'] = student
        context['messages'] = MessageSelector.get_messages_for_student(
            self.parent.id,
            int(student_id)
        )
        
        return context


class SendMessageView(ParentPortalMixin, View):
    """Send a new message"""
    
    def post(self, request):
        student_id = request.POST.get('student_id')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        if not all([student_id, subject, message]):
            messages.error(request, 'All fields are required')
            return redirect('parents:messages')
        
        # Verify access
        if not PortalService.verify_child_access(self.parent.id, int(student_id), 'communicate'):
            messages.error(request, 'You do not have permission to send messages about this student')
            return redirect('parents:messages')
        
        student = StudentSelector.get_by_id(int(student_id))
        if not student:
            messages.error(request, 'Student not found')
            return redirect('parents:messages')
        
        # Create message
        msg = Message.objects.create(
            sender_parent_id=self.parent.id,
            subject=subject,
            body=message,
            student_id=int(student_id),
            student_name=student['full_name']
        )
        
        # TODO: Notify teachers via notification service
        
        messages.success(request, 'Message sent successfully')
        return redirect('parents:message_thread', student_id=student_id)


class ProfileView(ParentPortalMixin, TemplateView):
    """View and edit parent profile"""
    template_name = 'parents/portal/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification_preferences'] = self.parent.notification_preferences
        return context
    
    def post(self, request):
        # Update notification preferences
        preferences = {}
        for key in request.POST:
            if key.startswith('notify_'):
                channel = key.replace('notify_', '')
                notification_type = request.POST.get(f'type_{channel}')
                if notification_type:
                    if notification_type not in preferences:
                        preferences[notification_type] = []
                    preferences[notification_type].append(channel)
        
        self.parent.notification_preferences = preferences
        self.parent.save(update_fields=['notification_preferences'])
        
        messages.success(request, 'Preferences updated successfully')
        return redirect('parents:profile')
"""
Staff Authentication Views
"""

from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.views.generic import FormView, TemplateView
from django import forms
from django.conf import settings
import logging

logger = logging.getLogger(__name__)



class StaffLoginForm(forms.Form):
    """Staff login form"""
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'placeholder': 'teacher@school.com',
            'class': 'w-full px-3 py-2 border rounded-md'
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'class': 'w-full px-3 py-2 border rounded-md'
        })
    )


class StaffLoginView(FormView):
    """Staff login page with email + password"""
    template_name = 'staffs/portal/login.html'
    form_class = StaffLoginForm
    success_url = reverse_lazy('staffs:portal_dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Check if user has a staff profile
            if hasattr(request.user, 'staff_profile'):
                return redirect('staffs:portal_dashboard')
            else:
                messages.warning(request, 'This account is not linked to a staff profile.')
                return redirect('corecode:dashboard')
        return super().dispatch(request, *args, **kwargs)
    

    def form_valid(self, form):
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        
        logger.debug(f"Login attempt for email: {email}")
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(email=email)
            logger.debug(f"User found: {user.username}, is_staff={user.is_staff}")
            
            authenticated_user = authenticate(
                self.request,
                username=user.username,
                password=password
            )
            
            if authenticated_user is not None:
                login(self.request, authenticated_user)
                messages.success(self.request, f'Welcome back!')
                return redirect(self.success_url)
            else:
                logger.warning(f"Authentication failed for email: {email}")
                messages.error(self.request, 'Invalid password. Please try again.')
                return self.form_invalid(form)
                
        except User.DoesNotExist:
            logger.warning(f"Login attempt for non-existent email: {email}")
            messages.error(self.request, 'No account found with this email address.')
            return self.form_invalid(form)

    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Staff Login'
        context['company_name'] = getattr(settings, 'COMPANY_NAME', 'DETs Toolkit')
        return context


class StaffLogoutView(LogoutView):
    """Staff logout"""
    next_page = reverse_lazy('staffs:portal_login')
    
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, 'You have been logged out.')
        return super().dispatch(request, *args, **kwargs)


class StaffPasswordResetRequestView(FormView):
    """Request password reset email"""
    template_name = 'staffs/portal/password_reset_request.html'
    
    class PasswordResetForm(forms.Form):
        email = forms.EmailField(label="Email Address")
    
    form_class = PasswordResetForm
    success_url = reverse_lazy('staffs:password_reset_sent')
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        
        from django.contrib.auth import get_user_model
        from ..models import Staff
        from ..services.invite import StaffInviteService
        
        User = get_user_model()
        
        try:
            user = User.objects.get(email=email)
            if hasattr(user, 'staff_profile'):
                # Send password reset (reuse invite service to send magic link)
                StaffInviteService.send_magic_link(user.staff_profile.id)
                messages.success(self.request, f'Password reset link sent to {email}')
            else:
                messages.error(self.request, 'No staff account found with this email.')
        except User.DoesNotExist:
            # Don't reveal if email exists for security
            messages.success(self.request, f'If an account exists for {email}, a reset link has been sent.')
        
        return super().form_valid(form)


class PasswordResetSentView(TemplateView):
    """Page shown after password reset email sent"""
    template_name = 'staffs/portal/password_reset_sent.html'


class StaffPasswordResetConfirmView(FormView):
    """Confirm password reset and set new password"""
    template_name = 'staffs/portal/password_reset_confirm.html'
    success_url = reverse_lazy('staffs:portal_login')
    
    class SetPasswordForm(forms.Form):
        password = forms.CharField(
            label="New Password",
            widget=forms.PasswordInput(attrs={'class': 'w-full px-3 py-2 border rounded-md'})
        )
        password_confirm = forms.CharField(
            label="Confirm Password",
            widget=forms.PasswordInput(attrs={'class': 'w-full px-3 py-2 border rounded-md'})
        )
        
        def clean(self):
            cleaned_data = super().clean()
            password = cleaned_data.get('password')
            password_confirm = cleaned_data.get('password_confirm')
            
            if password and password_confirm and password != password_confirm:
                raise forms.ValidationError("Passwords do not match")
            
            if password and len(password) < 8:
                raise forms.ValidationError("Password must be at least 8 characters")
            
            return cleaned_data
    
    form_class = SetPasswordForm
    
    def dispatch(self, request, *args, **kwargs):
        token = kwargs.get('token')
        from ..models import PortalSession
        
        try:
            session = PortalSession.objects.get(token=token, is_used=False)
            if not session.is_valid():
                messages.error(request, 'This password reset link has expired.')
                return redirect('staffs:portal_login')
            self.session = session
        except PortalSession.DoesNotExist:
            messages.error(request, 'Invalid password reset link.')
            return redirect('staffs:portal_login')
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        new_password = form.cleaned_data['password']
        
        # Update user's password
        user = self.session.staff.user
        user.set_password(new_password)
        user.save()
        
        # Mark session as used
        self.session.is_used = True
        self.session.save()
        
        messages.success(self.request, 'Password reset successful. Please login with your new password.')
        return super().form_valid(form)
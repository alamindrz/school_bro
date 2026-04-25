"""
Staff Invite Views
"""

from django.views.generic import FormView, TemplateView, View
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth import login
from django import forms

from ..services.invite import StaffInviteService
from ..models import Staff


class AcceptInviteForm(forms.Form):
    """Form for accepting invite and setting password"""
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Password",
        help_text="Leave blank to use magic link login instead"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Confirm Password"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password != password_confirm:
            raise forms.ValidationError("Passwords do not match")
        
        if password and len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters")
        
        return cleaned_data


class AcceptInviteView(FormView):
    """Accept invite and set up account"""
    template_name = 'staffs/portal/accept_invite.html'
    form_class = AcceptInviteForm
    success_url = reverse_lazy('staffs:portal_dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        token = kwargs.get('token')
        if not StaffInviteService.is_invite_valid(token):
            messages.error(request, 'Invalid or expired invitation link.')
            return redirect('staffs:portal_login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = self.kwargs.get('token')
        staff = get_object_or_404(Staff, invite_token=token)
        context['staff_name'] = staff.get_full_name
        context['staff_email'] = staff.email
        context['token'] = token
        return context
        
        
    def form_valid(self, form):
        token = self.kwargs.get('token')
        password = form.cleaned_data.get('password')
        
        user, error = StaffInviteService.accept_invite(token, password)
        
        if error:
            messages.error(self.request, error)
            return self.form_invalid(form)
        
        # Log the user in
        from django.contrib.auth import login
        login(self.request, user)
        messages.success(self.request, f'Welcome! Your account has been set up successfully.')
        
        return super().form_valid(form)


class MagicLinkLoginView(View):
    """Send magic link for passwordless login"""
    
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        
        try:
            staff = Staff.objects.get(email=email, is_active=True)
            
            # Generate magic link (reuse invite token or create session)
            from ..services.magic_link import MagicLinkService
            MagicLinkService.send_magic_link(staff)
            
            messages.success(request, f'Login link sent to {email}. Check your email.')
        except Staff.DoesNotExist:
            # Don't reveal if email exists
            messages.success(request, f'If an account exists for {email}, a login link has been sent.')
        
        return redirect('staffs:portal_login')
        

class MagicLinkLoginView(View):
    """Handle magic link click and login"""
    
    def get(self, request, token):
        from ..models import PortalSession
        
        try:
            session = PortalSession.objects.get(token=token, is_used=False)
            
            if not session.is_valid():
                messages.error(request, 'This login link has expired.')
                return redirect('staffs:portal_login')
            
            # Mark as used
            session.is_used = True
            session.save()
            
            # Login the user
            from django.contrib.auth import login
            login(request, session.staff.user)
            
            messages.success(request, f'Welcome back, {session.staff.get_full_name}!')
            return redirect('staffs:portal_dashboard')
            
        except PortalSession.DoesNotExist:
            messages.error(request, 'Invalid login link.')
            return redirect('staffs:portal_login')
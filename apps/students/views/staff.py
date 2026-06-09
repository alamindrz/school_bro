

"""
Staff views for student management
UPDATED: Now using proper form classes, no inline fields
DEPENDS ON: students/forms.py
"""

from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, FormView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required


from django.views.generic.edit import DeleteView
from django.db import models  
from django.core.exceptions import ValidationError  


import logging
logger = logging.getLogger(__name__)

from ..models import Student, Guardian, StudentHistory
from ..selectors import StudentSelector, GuardianSelector, StudentHistorySelector

from ..services import (
    StudentService, 
    GuardianService,
    AdmissionNumberService,
    StudentUserService
)

from ..services.user_integration import StudentUserService
from ..services.admission_number import AdmissionNumberService
from ..forms import (
    StudentCreateForm, StudentUpdateForm, StudentStatusForm,
    GuardianForm, BulkStudentImportForm, StudentSearchForm
)
from ..exceptions import (
    StudentError, StudentNotFoundError, InvalidStatusTransitionError,
    AdmissionNumberCollisionError
)

# ✅ CORRECT: Import selectors from selectors.py, services from services.py
from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector
from apps.corecode.services import SystemLogService  # ✅ Service
from apps.corecode.models import SystemLog


class StudentListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List all students with filtering - USING FORM"""
    model = Student
    template_name = 'students/pages/student_list.html'
    context_object_name = 'students'
    permission_required = 'students.view_student'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Student.objects.select_related(
            'current_class', 'enrollment_session', 'user'
        ).prefetch_related('guardians')
        
        # Use form for filtering
        self.search_form = StudentSearchForm(self.request.GET)
        
        if self.search_form.is_valid():
            data = self.search_form.cleaned_data
            
            # Search query
            q = data.get('q')
            if q:
                queryset = queryset.filter(
                    models.Q(admission_number__icontains=q) |
                    models.Q(first_name__icontains=q) |
                    models.Q(last_name__icontains=q) |
                    models.Q(email__icontains=q)
                )
            
            # Class filter
            class_id = data.get('class_id')
            if class_id:
                queryset = queryset.filter(current_class_id=class_id)
            
            # Status filter
            status = data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            # Gender filter
            gender = data.get('gender')
            if gender:
                queryset = queryset.filter(gender=gender)
            
            # Session filter
            session_id = data.get('session_id')
            if session_id:
                queryset = queryset.filter(enrollment_session_id=session_id)
        
        return queryset.order_by('admission_number')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = self.search_form
        context['total_count'] = self.get_queryset().count()
        return context


class StudentCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Manual student creation - USING PROPER FORM"""
    model = Student
    template_name = 'students/pages/student_form.html'
    form_class = StudentCreateForm
    permission_required = 'students.add_student'
    success_url = reverse_lazy('students:list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            
            messages.success(
                self.request,
                f'Student {self.object.get_full_name} created successfully. '
                f'Admission Number: {self.object.admission_number}'
            )
            
            # Log the action
            SystemLogService.log_action(
                user=self.request.user,
                action=SystemLog.ActionType.CREATE,
                app_label=SystemLog.AppLabel.STUDENTS,
                model_name='Student',
                object_id=str(self.object.id),
                object_repr=self.object.admission_number,
                changes={'created_via': 'manual'},
                request=self.request
            )
            
            return response
            
        except Exception as e:
            messages.error(self.request, f'Error creating student: {str(e)}')
            logger.error(f"Student creation failed: {e}", exc_info=True)
            return self.form_invalid(form)


class StudentUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Update student information - USING PROPER FORM"""
    model = Student
    template_name = 'students/pages/student_form.html'
    form_class = StudentUpdateForm
    permission_required = 'students.change_student'
    
    def get_success_url(self):
        return reverse_lazy('students:detail', kwargs={'pk': self.object.pk})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        messages.success(self.request, 'Student information updated successfully.')
        
        # Log changes
        if form.changed_data:
            SystemLogService.log_action(
                user=self.request.user,
                action=SystemLog.ActionType.UPDATE,
                app_label=SystemLog.AppLabel.STUDENTS,
                model_name='Student',
                object_id=str(self.object.id),
                object_repr=self.object.admission_number,
                changes={'changed_fields': form.changed_data},
                request=self.request
            )
        
        return response


class StudentStatusUpdateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Update student status - USING PROPER FORM"""
    template_name = 'students/pages/status_update.html'
    form_class = StudentStatusForm
    permission_required = 'students.change_student'
    
    def dispatch(self, request, *args, **kwargs):
        self.student = get_object_or_404(Student, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['student'] = self.student
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = self.student
        return context
    
    def form_valid(self, form):
        try:
            new_status = form.cleaned_data['status']
            reason = form.cleaned_data['reason']
            
            student = StudentService.update_student_status(
                student_id=self.student.id,
                new_status=new_status,
                reason=reason,
                performed_by_id=self.request.user.id
            )
            
            messages.success(
                self.request,
                f'Student status updated to {student.get_status_display()}'
            )
            
            return redirect('students:detail', pk=self.student.id)
            
        except InvalidStatusTransitionError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Status update failed for student {self.student.id}: {e}", exc_info=True)
            messages.error(self.request, f'Error updating status: {str(e)}')
            return self.form_invalid(form)


class GuardianCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Add guardian to student - USING PROPER FORM"""
    model = Guardian
    template_name = 'students/pages/guardian_form.html'
    form_class = GuardianForm
    permission_required = 'students.add_guardian'
    
    def dispatch(self, request, *args, **kwargs):
        self.student = get_object_or_404(Student, pk=kwargs['student_id'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['student'] = self.student
        return kwargs
    
    def form_valid(self, form):
        form.instance.student = self.student
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            f'Guardian {self.object.get_full_name} added successfully.'
        )
        
        # Create parent portal account if email provided
        if self.object.email and form.cleaned_data.get('create_portal_account', False):
            try:
                StudentUserService.create_parent_portal_account(
                    guardian=self.object,
                    send_welcome_email=True,
                    created_by_id=self.request.user.id
                )
                messages.info(self.request, 'Parent portal account created.')
            except Exception as e:
                messages.warning(self.request, f'Guardian saved but portal account creation failed: {e}')
        
        return response
    
    def get_success_url(self):
        return reverse_lazy('students:detail', kwargs={'pk': self.student.pk})


class StudentBulkImportView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Bulk import students from CSV - USING PROPER FORM"""
    template_name = 'students/pages/bulk_import.html'
    form_class = BulkStudentImportForm
    permission_required = 'students.bulk_import_students'
    success_url = reverse_lazy('students:list')
    
    def form_valid(self, form):
        import csv
        import io
        from datetime import datetime
        
        csv_file = form.cleaned_data['csv_file']
        create_users = form.cleaned_data['create_user_accounts']
        send_emails = form.cleaned_data['send_welcome_emails']
        
        success_count = 0
        error_rows = []
        
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    with transaction.atomic():
                        # Create student using service
                        student_data = {
                            'first_name': row['first_name'],
                            'last_name': row['last_name'],
                            'date_of_birth': row['date_of_birth'],
                            'gender': row['gender'],
                            'current_class_id': self._get_class_id(row['current_class']),
                            'email': row.get('email', ''),
                            'phone': row.get('phone', ''),
                            'address': row.get('address', ''),
                            'created_via': 'bulk_import',
                            'created_by_id': self.request.user.id,
                        }
                        
                        student = StudentService.create_from_admission(student_data)
                        success_count += 1
                        
                        # Create user account if requested
                        if create_users and student.email:
                            StudentUserService.create_user_for_student(
                                student=student,
                                send_welcome_email=send_emails,
                                created_by_id=self.request.user.id
                            )
                            
                except Exception as e:
                    error_rows.append({
                        'row': row_num,
                        'data': row,
                        'error': str(e)
                    })
            
            if error_rows:
                messages.warning(
                    self.request,
                    f'Imported {success_count} students with {len(error_rows)} errors.'
                )
                # Store errors in session for display
                self.request.session['bulk_import_errors'] = error_rows[:50]
            else:
                messages.success(self.request, f'Successfully imported {success_count} students.')
                
        except Exception as e:
            logger.error(f"Bulk import failed: {e}", exc_info=True)
            messages.error(self.request, f'Bulk import failed: {str(e)}')
        
        return super().form_valid(form)
    
    def _get_class_id(self, class_name):
        """Helper to get class ID by name"""
        from apps.corecode.models import StudentClass
        try:
            return StudentClass.objects.get(name=class_name).id
        except StudentClass.DoesNotExist:
            raise ValidationError(f"Class '{class_name}' not found")


@method_decorator(require_POST, name='dispatch')
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('students.change_student', raise_exception=True), name='dispatch')
class StudentGenerateUserView(TemplateView):
    """Generate user account for existing student"""
    
    def post(self, request, *args, **kwargs):
        student_id = kwargs.get('pk')
        student = get_object_or_404(Student, pk=student_id)
        
        try:
            user = StudentUserService.create_user_for_student(
                student=student,
                send_welcome_email=True,
                created_by_id=request.user.id
            )
            
            messages.success(
                request,
                f'User account created for {student.get_full_name}. Username: {user.username}'
            )
        except Exception as e:
            logger.error(f"User account creation failed for student {student_id}: {e}", exc_info=True)
            messages.error(request, f'Failed to create user account: {str(e)}')
        
        return redirect('students:detail', pk=student_id)
        
class StudentDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detailed student profile view"""
    model = Student
    template_name = 'students/pages/student_detail.html'
    context_object_name = 'student'
    permission_required = 'students.view_student'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get additional data via selectors
        context['guardians'] = GuardianSelector.get_student_guardians(self.object.id)
        context['timeline'] = StudentHistorySelector.get_student_timeline(self.object.id)
    
        # Safe way to get next class
        try:
            next_class = self.object.current_class.next_class if self.object.current_class else None
        except StudentClass.MultipleObjectsReturned:
            next_class = None
        
        # Get class progression info
        context['next_class'] = next_class
        
        context['is_graduating'] = self.object.current_class.is_graduating_class if self.object.current_class else False
        
        # Check if user account exists
        context['has_user_account'] = self.object.user is not None
        
        return context


class StudentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Delete student (soft delete by changing status)"""
    model = Student
    template_name = 'students/pages/student_confirm_delete.html'
    permission_required = 'students.delete_student'
    success_url = reverse_lazy('students:list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Soft delete - change status to withdrawn instead of actual delete
        old_status = self.object.status
        self.object.status = 'withdrawn'
        self.object.save(update_fields=['status'])
        
        # Record in history
        StudentHistory.objects.create(
            student=self.object,
            academic_session=self.object.enrollment_session,
            term=1,  # Will be updated with current term
            class_at_time=self.object.current_class,
            status_at_time='withdrawn',
            action='WITHDRAWN',
            notes=f"Student withdrawn by {request.user.get_full_name() or request.user.username}",
            performed_by=request.user
        )
        
        # Log the action
        SystemLogService.log_action(
            user=request.user,
            action=SystemLog.ActionType.DELETE,
            app_label=SystemLog.AppLabel.STUDENTS,
            model_name='Student',
            object_id=str(self.object.id),
            object_repr=self.object.admission_number,
            changes={'old_status': old_status, 'new_status': 'withdrawn'},
            request=request
        )
        
        messages.success(request, f'Student {self.object.get_full_name} has been withdrawn.')
        return redirect(self.success_url)


class GuardianUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Update guardian information"""
    model = Guardian
    template_name = 'students/pages/guardian_form.html'
    form_class = GuardianForm
    permission_required = 'students.change_guardian'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['student'] = self.object.student
        return kwargs
    
    def get_success_url(self):
        return reverse_lazy('students:detail', kwargs={'pk': self.object.student.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Guardian information updated successfully.')
        return response


class GuardianDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Delete guardian"""
    model = Guardian
    permission_required = 'students.delete_guardian'
    
    def get_success_url(self):
        return reverse_lazy('students:detail', kwargs={'pk': self.object.student.pk})
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        student_pk = self.object.student.pk
        guardian_name = self.object.get_full_name
        
        # Check if this is the only primary guardian
        if self.object.is_primary:
            other_primary = Guardian.objects.filter(
                student=self.object.student,
                is_primary=True
            ).exclude(pk=self.object.pk).exists()
            
            if not other_primary:
                # Make another guardian primary if available
                other_guardian = Guardian.objects.filter(
                    student=self.object.student
                ).exclude(pk=self.object.pk).first()
                
                if other_guardian:
                    other_guardian.is_primary = True
                    other_guardian.save(update_fields=['is_primary'])
                    messages.info(request, f'{other_guardian.get_full_name} has been set as primary guardian.')
        
        self.object.delete()
        
        messages.success(request, f'Guardian {guardian_name} deleted successfully.')
        return redirect('students:detail', pk=student_pk)


class StudentPromotionView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Bulk student promotion"""
    template_name = 'students/pages/promotion.html'
    permission_required = 'students.promote_student'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['classes'] = StudentClassSelector.active_classes()
        context['current_session'] = AcademicSessionSelector.get_current_session()
        return context
    
    def post(self, request, *args, **kwargs):
        from_class_id = request.POST.get('from_class')
        to_class_id = request.POST.get('to_class')
        student_ids = request.POST.getlist('students')
        
        if not student_ids:
            messages.error(request, 'No students selected for promotion')
            return redirect('students:promotion')
        
        # Import here to avoid circular import
        from ..services.promotion import PromotionService
        
        try:
            successful, failed = PromotionService.bulk_promote_students(
                student_ids=[int(id) for id in student_ids],
                to_class_id=int(to_class_id),
                promoted_by_id=request.user.id
            )
            
            if failed:
                messages.warning(
                    request,
                    f'Promoted {len(successful)} students. {len(failed)} failed.'
                )
                # Store failures in session for display
                request.session['promotion_failures'] = failed[:10]
            else:
                messages.success(request, f'Successfully promoted {len(successful)} students.')
                
        except Exception as e:
            logger.error(f"Promotion failed: {e}", exc_info=True)
            messages.error(request, f'Promotion failed: {str(e)}')
        
        return redirect('students:list')


class StudentAjaxView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """AJAX endpoints for student data"""
    permission_required = 'students.view_student'
    
    def get(self, request, *args, **kwargs):
        action = request.GET.get('action')
        
        if action == 'search':
            query = request.GET.get('q', '')
            students = StudentSelector.search_students(query)
            return JsonResponse({'students': students})
        
        elif action == 'class_students':
            class_id = request.GET.get('class_id')
            session_id = request.GET.get('session_id')
            if session_id:
                session_id = int(session_id) if session_id else None
            students = StudentSelector.get_class_students(class_id, session_id)
            return JsonResponse({'students': students})
        
        elif action == 'counts':
            counts = StudentSelector.get_student_counts_by_class()
            return JsonResponse({'class_counts': counts})
        
        elif action == 'promotion_candidates':
            class_id = request.GET.get('class_id')
            from ..services.promotion import PromotionService
            candidates = PromotionService.get_promotion_candidates(int(class_id))
            return JsonResponse({'candidates': candidates})
        
        return JsonResponse({'error': 'Invalid action'}, status=400)
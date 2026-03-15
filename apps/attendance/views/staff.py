"""
Staff views for attendance management
"""

from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, View, FormView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import date, timedelta, datetime
import logging

from ..models import AttendanceRegister, AttendanceRecord, AttendanceSummary, QRCode
from ..selectors import (
    AttendanceRegisterSelector, AttendanceRecordSelector,
    AttendanceSummarySelector, QRCodeSelector
)
from ..services import AttendanceService, ReportService, BulkAttendanceService
from ..constants import AttendanceStatus, SessionType, MarkingMethod
from ..exceptions import (
    AttendanceRecordNotFoundError, DuplicateAttendanceError,
    InvalidAttendanceStatusError, BulkOperationError
)

from apps.corecode.selectors import (
    StudentClassSelector, AcademicSessionSelector, AcademicTermSelector
)
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog
from apps.students.selectors import StudentSelector

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Attendance dashboard"""
    template_name = 'attendance/pages/dashboard.html'
    permission_required = 'attendance.view_attendanceregister'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Today's summary
        today = date.today()
        context['today'] = today
        context['today_registers'] = AttendanceRegisterSelector.get_for_date(today)
        context['today_summary'] = AttendanceRecordSelector.get_daily_summary(today)

        # Alerts
        context['alerts'] = AttendanceSummarySelector.get_alerts(threshold='all')[:10]

        # Quick stats
        current_session = AcademicSessionSelector.get_current_session()
        if current_session:
            context['current_session'] = current_session.name
            context['summary_stats'] = {
                'total_students': AttendanceSummary.objects.filter(
                    academic_session=current_session
                ).count(),
                'alert_count': AttendanceSummary.objects.filter(
                    academic_session=current_session,
                    attendance_alert=True
                ).count(),
            }

        return context


class RegisterListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List attendance registers"""
    template_name = 'attendance/pages/register_list.html'
    context_object_name = 'registers'
    permission_required = 'attendance.view_attendanceregister'
    paginate_by = 25

    def get_queryset(self):
        class_id = self.request.GET.get('class_id')
        session_id = self.request.GET.get('session_id')
        term_id = self.request.GET.get('term_id')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        return AttendanceRegisterSelector.list_registers(
            class_id=class_id,
            session_id=session_id,
            term_id=term_id,
            start_date=start_date,
            end_date=end_date
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['classes'] = StudentClassSelector.get_all_classes()
        context['sessions'] = AcademicSessionSelector.list_sessions(limit=5)
        context['session_types'] = SessionType.CHOICES

        # Get terms for current session
        current_session = AcademicSessionSelector.get_current_session()
        if current_session:
            from apps.corecode.selectors import AcademicTermSelector
            context['terms'] = AcademicTermSelector.get_terms_for_session(current_session.id)

        return context


class RegisterDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Attendance register detail"""
    model = AttendanceRegister
    template_name = 'attendance/pages/register_detail.html'
    context_object_name = 'register'
    permission_required = 'attendance.view_attendanceregister'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['register_data'] = AttendanceRegisterSelector.get_by_id(self.object.id)

        # Get list of students in this class (for marking)
        students = StudentSelector.get_class_students(
            class_id=self.object.student_class_id,
            academic_session_id=self.object.academic_session_id
        )
        context['students'] = students

        return context


class RegisterCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create attendance register"""
    model = AttendanceRegister
    template_name = 'attendance/pages/register_form.html'
    fields = ['student_class', 'date', 'session_type', 'academic_session', 'academic_term']
    permission_required = 'attendance.add_attendanceregister'
    success_url = reverse_lazy('attendance:register_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Use selectors instead of direct model access
        from apps.corecode.selectors import StudentClassSelector, AcademicSessionSelector, AcademicTermSelector
        
        # Student class choices - using selector
        form.fields['student_class'].queryset = StudentClassSelector.get_queryset_for_forms(active_only=True)
        
        # Academic session choices - using selector instead of direct model access
        # For new registers, we typically only want the current session
        form.fields['academic_session'].queryset = AcademicSessionSelector.get_current_session_queryset()
        
        # Set default date to today
        form.fields['date'].initial = date.today()
        
        # If there's a current session, pre-select it
        current_session = AcademicSessionSelector.get_current_session()
        if current_session:
            form.fields['academic_session'].initial = current_session.id
            
            # Also load terms for this session
            terms = AcademicTermSelector.get_terms_for_session(current_session.id)
            if terms:
                # You might want to set the first term as default
                form.fields['academic_term'].queryset = AcademicTerm.objects.filter(session_id=current_session.id)
                form.fields['academic_term'].initial = terms[0].id if terms else None

        return form

    def form_valid(self, form):
        try:
            from ..services import AttendanceService
            register = AttendanceService.create_register(
                class_id=form.cleaned_data['student_class'].id,
                date=form.cleaned_data['date'],
                session_type=form.cleaned_data['session_type'],
                session_id=form.cleaned_data['academic_session'].id,
                term_id=form.cleaned_data['academic_term'].id if form.cleaned_data['academic_term'] else None,
                marked_by_id=self.request.user.id
            )

            messages.success(self.request, f'Register created for {register.date}')
            return redirect('attendance:register_detail', pk=register.id)

        except DuplicateAttendanceError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'Error creating register: {str(e)}')
            return self.form_invalid(form)


class MarkAttendanceView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Mark attendance for a student"""
    permission_required = 'attendance.add_attendancerecord'

    def post(self, request, *args, **kwargs):
        register_id = kwargs.get('pk')
        student_id = request.POST.get('student_id')
        status = request.POST.get('status')
        remarks = request.POST.get('remarks', '')

        try:
            record = AttendanceService.mark_attendance(
                register_id=register_id,
                student_id=int(student_id),
                status=status,
                remarks=remarks,
                marked_by_id=request.user.id
            )

            if request.headers.get('HX-Request'):
                # HTMX request - return updated row
                return render(request, 'attendance/partials/attendance_row.html', {
                    'record': record,
                    'student': StudentSelector.get_by_id(int(student_id))
                })

            messages.success(request, f'Attendance marked for {record.student_name}')
            return redirect('attendance:register_detail', pk=register_id)

        except Exception as e:
            messages.error(request, str(e))
            return redirect('attendance:register_detail', pk=register_id)


class BulkMarkView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Bulk attendance marking page"""
    template_name = 'attendance/pages/bulk_mark.html'
    permission_required = 'attendance.add_attendancerecord'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        register_id = self.kwargs.get('pk')
        register = AttendanceRegisterSelector.get_by_id(register_id)

        if not register:
            messages.error(self.request, 'Register not found')
            return context

        context['register'] = register

        # Get students
        students = StudentSelector.get_class_students(
            class_id=register['student_class']['id'],
            academic_session_id=register['academic_session']['id']
        )
        context['students'] = students

        return context

    def post(self, request, *args, **kwargs):
        register_id = self.kwargs.get('pk')
        bulk_status = request.POST.get('bulk_status')

        try:
            # Get all students
            register = AttendanceRegisterSelector.get_by_id(register_id)
            students = StudentSelector.get_class_students(
                class_id=register['student_class']['id'],
                academic_session_id=register['academic_session']['id']
            )

            count = 0
            for student in students:
                try:
                    AttendanceService.mark_attendance(
                        register_id=register_id,
                        student_id=student['id'],
                        status=bulk_status,
                        marked_by_id=request.user.id
                    )
                    count += 1
                except DuplicateAttendanceError:
                    # Skip duplicates
                    continue
                except Exception as e:
                    logger.error(f"Failed to mark {student['id']}: {e}")

            messages.success(request, f'Marked {count} students as {bulk_status}')

        except Exception as e:
            messages.error(request, str(e))

        return redirect('attendance:register_detail', pk=register_id)


class CloseRegisterView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Close attendance register"""
    permission_required = 'attendance.change_attendanceregister'

    def post(self, request, *args, **kwargs):
        register_id = kwargs.get('pk')

        try:
            register = AttendanceService.close_register(
                register_id=register_id,
                closed_by_id=request.user.id
            )

            messages.success(request, f'Register closed')

        except Exception as e:
            messages.error(request, str(e))

        return redirect('attendance:register_detail', pk=register_id)


class QRCodeView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """QR code management view"""
    template_name = 'attendance/pages/qrcodes.html'
    permission_required = 'attendance.view_qrcode'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        student_id = self.request.GET.get('student_id')
        if student_id:
            context['qr_code'] = QRCodeSelector.get_for_student(int(student_id))

        return context


class GenerateQRCodeView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Generate QR code for a student"""
    permission_required = 'attendance.add_qrcode'

    def post(self, request, *args, **kwargs):
        student_id = request.POST.get('student_id')

        student = StudentSelector.get_by_id(int(student_id))
        if not student:
            messages.error(request, 'Student not found')
            return redirect('attendance:qrcodes')

        # Check if QR code already exists
        existing = QRCode.objects.filter(student_id=student_id).first()
        if existing:
            messages.info(request, 'QR code already exists for this student')
            return redirect('attendance:qrcodes')

        # Generate QR code
        import qrcode
        from io import BytesIO
        from django.core.files.base import ContentFile
        import uuid

        # Generate unique code
        code = str(uuid.uuid4())

        # Create QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Save to BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        # Create QR code record
        qr_obj = QRCode.objects.create(
            student_id=int(student_id),
            student_name=student['full_name'],
            code=code,
        )

        # Save image
        filename = f"qr_{student_id}_{code[:8]}.png"
        qr_obj.qr_image.save(filename, ContentFile(buffer.getvalue()))

        messages.success(request, f'QR code generated for {student["full_name"]}')
        return redirect('attendance:qrcodes')


class ReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Attendance reports"""
    template_name = 'attendance/pages/reports.html'
    permission_required = 'attendance.view_attendancereport'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        report_type = self.request.GET.get('type', 'daily')
        context['report_type'] = report_type

        if report_type == 'daily':
            report_date = self.request.GET.get('date', date.today().isoformat())
            context['report'] = ReportService.generate_daily_report(
                report_date=date.fromisoformat(report_date),
                class_id=self.request.GET.get('class_id')
            )

        elif report_type == 'weekly':
            start_date = self.request.GET.get('start_date')
            if not start_date:
                start_date = (date.today() - timedelta(days=date.today().weekday())).isoformat()

            context['report'] = ReportService.generate_weekly_report(
                start_date=date.fromisoformat(start_date),
                class_id=self.request.GET.get('class_id')
            )

        elif report_type == 'monthly':
            year = int(self.request.GET.get('year', date.today().year))
            month = int(self.request.GET.get('month', date.today().month))

            context['report'] = ReportService.generate_monthly_report(
                year=year,
                month=month,
                class_id=self.request.GET.get('class_id')
            )

        elif report_type == 'student':
            student_id = self.request.GET.get('student_id')
            if student_id:
                context['student_report'] = ReportService.generate_student_report(
                    student_id=int(student_id)
                )

        return context
        
class UpdateAttendanceView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Update an attendance record"""
    permission_required = 'attendance.change_attendancerecord'
    
    def post(self, request, *args, **kwargs):
        record_id = kwargs.get('pk')
        status = request.POST.get('status')
        remarks = request.POST.get('remarks', '')
        
        try:
            record = AttendanceService.update_attendance(
                record_id=record_id,
                status=status,
                remarks=remarks,
                updated_by_id=request.user.id
            )
            
            if request.headers.get('HX-Request'):
                # Return updated row
                from apps.students.selectors import StudentSelector
                student = StudentSelector.get_by_id(record.student_id)
                return render(request, 'attendance/partials/attendance_row.html', {
                    'record': record,
                    'student': student,
                    'register': record.register,
                })
            
            messages.success(request, 'Attendance updated successfully')
            return redirect('attendance:register_detail', pk=record.register_id)
            
        except Exception as e:
            messages.error(request, str(e))
            return redirect('attendance:register_detail', pk=record.register_id)


class ScanQRCodeView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """QR code scanner page"""
    template_name = 'attendance/pages/scan_qrcode.html'
    permission_required = 'attendance.add_attendancerecord'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['session_types'] = SessionType.CHOICES
        return context


class ExportReportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Export attendance report as CSV"""
    permission_required = 'attendance.view_attendancereport'
    
    def get(self, request, *args, **kwargs):
        import csv
        from django.http import HttpResponse
        
        report_type = request.GET.get('type', 'daily')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="attendance_{report_type}_{date.today()}.csv"'
        
        writer = csv.writer(response)
        
        if report_type == 'daily':
            report_date = request.GET.get('date', date.today().isoformat())
            report = ReportService.generate_daily_report(date.fromisoformat(report_date))
            
            if report['has_data']:
                writer.writerow(['Class', 'Total', 'Present', 'Absent', 'Late', 'Percentage'])
                for class_data in report['by_class']:
                    writer.writerow([
                        class_data['class_name'],
                        class_data['total'],
                        class_data['present'],
                        class_data['absent'],
                        class_data['late'],
                        f"{class_data['percentage']:.1f}%",
                    ])
        
        elif report_type == 'student':
            student_id = request.GET.get('student_id')
            if student_id:
                report = ReportService.generate_student_report(int(student_id))
                if report['has_data']:
                    writer.writerow(['Date', 'Status', 'Check In', 'Session'])
                    for record in report['recent']:
                        writer.writerow([
                            record['date'],
                            record['status'],
                            record.get('check_in', ''),
                            record.get('session', ''),
                        ])
        
        return response
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Student, Guardian, StudentHistory


class GuardianInline(admin.TabularInline):
    model = Guardian
    extra = 1
    fields = ['first_name', 'last_name', 'relationship', 'phone', 'email', 'is_primary']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['admission_number', 'get_full_name', 'current_class', 'status', 'enrollment_session', 'created_at']
    list_filter = ['status', 'current_class', 'enrollment_session', 'gender', 'created_via']
    search_fields = ['admission_number', 'first_name', 'last_name', 'email']
    date_hierarchy = 'enrollment_date'
    
    fieldsets = (
        ('Identity', {
            'fields': ('admission_number', 'user', 'first_name', 'last_name', 'middle_name', 'gender', 'date_of_birth')
        }),
        ('Contact', {
            'fields': ('email', 'phone', 'address', 'city', 'state_of_origin', 'nationality')
        }),
        ('Academic', {
            'fields': ('current_class', 'enrollment_date', 'enrollment_session', 'status')
        }),
        ('Medical', {
            'fields': ('blood_group', 'medical_notes', 'has_special_needs', 'special_needs_notes'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_via', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'admission_number']
    inlines = [GuardianInline]
    
    def get_full_name(self, obj):
        return obj.get_full_name
    get_full_name.short_description = 'Full Name'
    get_full_name.admin_order_field = 'last_name'
    
    def view_history_link(self, obj):
        url = reverse('admin:students_studenthistory_changelist') + f'?student__id__exact={obj.id}'
        return format_html('<a href="{}">View History</a>', url)
    view_history_link.short_description = 'History'


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'relationship', 'student', 'phone', 'email', 'is_primary']
    list_filter = ['relationship', 'is_primary', 'is_emergency_contact']
    search_fields = ['first_name', 'last_name', 'email', 'student__admission_number']
    
    def get_full_name(self, obj):
        return obj.get_full_name
    get_full_name.short_description = 'Name'


@admin.register(StudentHistory)
class StudentHistoryAdmin(admin.ModelAdmin):
    list_display = ['student', 'action', 'class_at_time', 'academic_session', 'term', 'performed_at']
    list_filter = ['action', 'academic_session', 'term']
    search_fields = ['student__admission_number', 'student__first_name', 'student__last_name']
    readonly_fields = ['performed_at']
    date_hierarchy = 'performed_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
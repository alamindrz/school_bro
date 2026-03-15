from django.contrib import admin
from django.utils.html import format_html
from .models import AcademicSession, AcademicTerm, StudentClass, SiteConfig, SystemLog


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'start_date', 'end_date', 'is_current', 'created_at']
    list_filter = ['is_current', 'start_date']
    search_fields = ['name', 'code']
    date_hierarchy = 'start_date'
    actions = ['make_current']
    
    def make_current(self, request, queryset):
        queryset.update(is_current=False)
        queryset.filter(id=queryset.first().id).update(is_current=True)
        self.message_user(request, f"Set {queryset.first().name} as current session")
    make_current.short_description = "Set selected as current session"


@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ['name', 'session', 'term', 'start_date', 'end_date', 'is_current']
    list_filter = ['session', 'term', 'is_current']
    search_fields = ['name', 'session__name']
    date_hierarchy = 'start_date'


@admin.register(StudentClass)
class StudentClassAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'education_level', 'max_students', 'sort_order', 'is_active']
    list_filter = ['education_level', 'is_active']
    search_fields = ['name', 'display_name']
    list_editable = ['max_students', 'sort_order', 'is_active']
    
    actions = ['activate_classes', 'deactivate_classes']
    
    def activate_classes(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} classes activated")
    
    def deactivate_classes(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} classes deactivated")


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ['key', 'value_preview', 'updated_at', 'updated_by', 'is_public']
    list_filter = ['is_public', 'updated_at']
    search_fields = ['key', 'value']
    readonly_fields = ['updated_at', 'updated_by']
    
    def value_preview(self, obj):
        if len(str(obj.value)) > 50:
            return format_html('{}...', str(obj.value)[:50])
        return obj.value
    value_preview.short_description = 'Value'
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'app_label', 'model_name', 'object_repr']
    list_filter = ['action', 'app_label', 'model_name', 'timestamp']
    search_fields = ['username', 'object_repr', 'changes']
    readonly_fields = ['timestamp', 'user', 'username', 'changes', 'ip_address', 'user_agent']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
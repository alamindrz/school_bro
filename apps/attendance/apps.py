from django.apps import AppConfig


class AttendanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.attendance'
    label = 'attendance'
    verbose_name = 'Attendance Management'
    
    def ready(self):
        import apps.attendance.signals.handlers  # noqa
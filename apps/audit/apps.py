"""
Audit App Configuration
"""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    label = 'audit'
    verbose_name = 'Audit Trail System'

    def ready(self):
        import apps.audit.signals.handlers  # noqa
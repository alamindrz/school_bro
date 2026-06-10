"""
Unit tests for the audit app models.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.audit.models import AuditLog, AuditRetentionPolicy
from apps.audit.constants import AuditAction, AuditStatus, AuditCategory

User = get_user_model()


@pytest.mark.django_db
class TestAuditLogModel:
    """Tests for AuditLog model."""

    def _create_audit_log(self, user=None, **kwargs):
        defaults = {
            'action': AuditAction.CREATE,
            'category': AuditCategory.DATA_MODIFICATION,
            'status': AuditStatus.SUCCESS,
            'app_label': 'students',
            'model_name': 'Student',
            'object_id': '1',
            'object_repr': 'Student #1',
            'ip_address': '127.0.0.1',
        }
        defaults.update(kwargs)
        if user:
            defaults['user'] = user
        return AuditLog(**defaults)

    def test_create_audit_log(self, user):
        log = self._create_audit_log(user=user)
        log.save()
        assert log.pk is not None
        assert log.audit_id is not None

    def test_str_representation(self, user):
        log = self._create_audit_log(user=user)
        log.save()
        assert str(user) in str(log)
        assert AuditAction.CREATE in str(log)

    def test_immutable_audit_log(self, user):
        log = self._create_audit_log(user=user)
        log.save()
        with pytest.raises(ValueError, match="cannot be modified"):
            log.action = AuditAction.UPDATE
            log.save()

    def test_auto_populates_username_from_user(self, user):
        log = self._create_audit_log(user=user)
        log.save()
        assert log.username == user.get_username()
        assert log.user_email == user.email

    def test_audit_id_is_unique(self, user):
        log1 = self._create_audit_log(user=user)
        log1.save()
        log2 = self._create_audit_log(user=user)
        log2.save()
        assert log1.audit_id != log2.audit_id

    def test_json_fields_default_to_empty_dict(self, user):
        log = self._create_audit_log(user=user)
        log.save()
        assert log.old_value == {}
        assert log.new_value == {}
        assert log.changes == {}

    def test_ordering_by_timestamp_desc(self, user):
        log1 = self._create_audit_log(user=user, object_id='1')
        log1.save()
        log2 = self._create_audit_log(user=user, object_id='2')
        log2.save()
        logs = list(AuditLog.objects.all())
        assert logs[0].pk == log2.pk

    def test_optional_user(self):
        """Audit log can be created without a user (system actions)."""
        log = AuditLog(
            action=AuditAction.CREATE,
            category=AuditCategory.SYSTEM,
            status=AuditStatus.SUCCESS,
            app_label='corecode',
            model_name='SiteConfig',
            ip_address='127.0.0.1',
        )
        log.save()
        assert log.pk is not None
        assert log.user is None


@pytest.mark.django_db
class TestAuditRetentionPolicyModel:

    def test_create_retention_policy(self, db):
        policy = AuditRetentionPolicy.objects.create(
            app_label='students',
            model_name='Student',
            retention_days=365,
        )
        assert policy.pk is not None
        assert policy.is_active is True

    def test_str_representation(self, db):
        policy = AuditRetentionPolicy.objects.create(
            app_label='finance',
            model_name='Payment',
            retention_days=730,
        )
        assert 'finance' in str(policy)
        assert '730' in str(policy)

    def test_unique_together(self, db):
        AuditRetentionPolicy.objects.create(
            app_label='students',
            model_name='Student',
            retention_days=365,
        )
        with pytest.raises(Exception):
            AuditRetentionPolicy.objects.create(
                app_label='students',
                model_name='Student',
                retention_days=180,
            )

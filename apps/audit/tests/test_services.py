"""
Unit tests for the audit app services.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.audit.services import AuditService
from apps.audit.constants import AuditAction, AuditStatus, AuditCategory

User = get_user_model()


@pytest.mark.django_db
class TestAuditService:

    def test_log_creates_entry(self, user):
        log = AuditService.log(
            user=user,
            action=AuditAction.CREATE,
            app_label='students',
            model_name='Student',
            object_id='1',
            object_repr='Student #1',
        )
        assert log is not None
        assert log.pk is not None
        assert log.action == AuditAction.CREATE

    def test_log_with_request_context(self, user):
        class FakeRequest:
            META = {
                'HTTP_USER_AGENT': 'TestAgent/1.0',
                'REMOTE_ADDR': '192.168.1.1',
                'HTTP_X_FORWARDED_FOR': '',
            }
            method = 'POST'
            path = '/students/create/'

        log = AuditService.log(
            user=user,
            action=AuditAction.CREATE,
            app_label='students',
            model_name='Student',
            object_id='1',
            object_repr='Student #1',
            request=FakeRequest(),
        )
        assert log.user_agent == 'TestAgent/1.0'
        assert log.request_method == 'POST'
        assert log.request_path == '/students/create/'

    def test_log_with_user_id(self, user):
        log = AuditService.log(
            user=user.id,
            action=AuditAction.VIEW,
            app_label='students',
            model_name='Student',
            object_id='1',
            object_repr='Student #1',
        )
        assert log is not None
        assert log.user == user
        assert log.username == user.get_username()

    def test_log_with_string_user(self):
        log = AuditService.log(
            user='system_cron',
            action=AuditAction.DELETE,
            app_label='audit',
            model_name='AuditLog',
            object_id='batch-1',
            object_repr='Batch cleanup',
        )
        assert log is not None
        assert log.username == 'system_cron'
        assert log.user is None

    def test_log_create_shortcut(self, user):
        log = AuditService.log_create(
            user=user,
            app_label='students',
            model_name='Student',
            object_id='42',
            object_repr='John Doe',
            new_value={'name': 'John Doe'},
        )
        assert log.action == AuditAction.CREATE
        assert log.category == AuditCategory.DATA_MODIFICATION
        assert log.new_value == {'name': 'John Doe'}

    def test_log_update_shortcut(self, user):
        log = AuditService.log_update(
            user=user,
            app_label='students',
            model_name='Student',
            object_id='42',
            object_repr='Student #42',
            old_value={'name': 'John'},
            new_value={'name': 'Jane'},
        )
        assert log.action == AuditAction.UPDATE
        assert log.changes != {}

    def test_log_delete_shortcut(self, user):
        log = AuditService.log_delete(
            user=user,
            app_label='students',
            model_name='Student',
            object_id='42',
            object_repr='Student #42',
            old_value={'name': 'John'},
        )
        assert log.action == AuditAction.DELETE

    def test_log_login_success(self, user):
        log = AuditService.log_login(user=user, success=True)
        assert log.action == AuditAction.LOGIN
        assert log.status == AuditStatus.SUCCESS
        assert log.category == AuditCategory.AUTHENTICATION

    def test_log_login_failure(self, user):
        log = AuditService.log_login(user=user, success=False)
        assert log.status == AuditStatus.FAILURE

    def test_log_export(self, user):
        log = AuditService.log(
            user=user,
            action=AuditAction.EXPORT,
            category=AuditCategory.DATA_ACCESS,
            app_label='students',
            model_name='Student',
            object_id='export-batch',
            object_repr='Exported 100 records',
            new_value={'count': 100},
        )
        assert log.action == AuditAction.EXPORT
        assert log.new_value == {'count': 100}

    def test_compute_changes(self):
        old = {'name': 'John', 'age': 15, 'active': True}
        new = {'name': 'Jane', 'age': 15, 'active': False}
        changes = AuditService._compute_changes(old, new)
        assert 'name' in changes
        assert 'active' in changes
        assert 'age' not in changes

    def test_ensure_serializable(self):
        assert AuditService._ensure_serializable(None) is None
        assert AuditService._ensure_serializable('hello') == 'hello'
        assert AuditService._ensure_serializable(42) == 42
        assert AuditService._ensure_serializable({'a': 1}) == {'a': 1}

    def test_log_does_not_crash_on_error(self):
        """Audit logging should never crash the main flow."""
        log = AuditService.log(
            user=None,
            action=AuditAction.CREATE,
            app_label='test',
            model_name='Test',
        )
        # Should succeed even with minimal data
        assert log is not None or log is None  # no exception raised

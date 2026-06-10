"""
Unit tests for the notifications app validators.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.notifications.validators import NotificationValidator, TemplateValidator
from apps.notifications.constants import (
    NotificationChannel, NotificationType, NotificationPriority, RecipientType,
)


class TestNotificationValidator:

    def test_validate_valid_channel(self):
        assert NotificationValidator.validate_channel(NotificationChannel.EMAIL) is True
        assert NotificationValidator.validate_channel(NotificationChannel.SMS) is True
        assert NotificationValidator.validate_channel(NotificationChannel.IN_APP) is True

    def test_validate_invalid_channel(self):
        with pytest.raises(ValidationError, match="Invalid channel"):
            NotificationValidator.validate_channel('telegram')

    def test_validate_valid_type(self):
        assert NotificationValidator.validate_notification_type(
            NotificationType.PAYMENT_RECEIPT,
        ) is True

    def test_validate_invalid_type(self):
        with pytest.raises(ValidationError, match="Invalid notification type"):
            NotificationValidator.validate_notification_type('nonexistent')

    def test_validate_valid_priority(self):
        assert NotificationValidator.validate_priority(NotificationPriority.HIGH) is True
        assert NotificationValidator.validate_priority(NotificationPriority.LOW) is True

    def test_validate_invalid_priority(self):
        with pytest.raises(ValidationError, match="Invalid priority"):
            NotificationValidator.validate_priority('critical')

    def test_validate_recipient_valid_student(self):
        assert NotificationValidator.validate_recipient(
            RecipientType.STUDENT, recipient_id=1,
        ) is True

    def test_validate_recipient_missing_id(self):
        with pytest.raises(ValidationError, match="Recipient ID required"):
            NotificationValidator.validate_recipient(RecipientType.STAFF)

    def test_validate_recipient_invalid_type(self):
        with pytest.raises(ValidationError, match="Invalid recipient type"):
            NotificationValidator.validate_recipient('unknown')

    def test_validate_recipient_broadcast_no_id_needed(self):
        assert NotificationValidator.validate_recipient(
            RecipientType.ALL_STUDENTS,
        ) is True


class TestTemplateValidator:

    def test_validate_template_name_valid(self):
        assert TemplateValidator.validate_template_name('payment_receipt') is True
        assert TemplateValidator.validate_template_name('term_begins_2025') is True

    def test_validate_template_name_too_short(self):
        with pytest.raises(ValidationError, match="at least 3 characters"):
            TemplateValidator.validate_template_name('ab')

    def test_validate_template_name_invalid_chars(self):
        with pytest.raises(ValidationError, match="only contain"):
            TemplateValidator.validate_template_name('invalid name!')

    def test_validate_variables_all_declared(self):
        template = 'Dear {{ name }}, your payment of {{ amount }} was received.'
        declared = ['name', 'amount']
        assert TemplateValidator.validate_variables(template, declared) is True

    def test_validate_variables_missing(self):
        template = 'Dear {{ name }}, your balance is {{ balance }}.'
        declared = ['name']
        with pytest.raises(ValidationError, match="Undefined variables.*balance"):
            TemplateValidator.validate_variables(template, declared)

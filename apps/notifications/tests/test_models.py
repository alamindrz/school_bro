"""
Unit tests for the notifications app models.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.notifications.models import (
    Notification, NotificationTemplate, NotificationPreference, NotificationLog,
)
from apps.notifications.constants import (
    NotificationType, NotificationChannel, NotificationPriority,
    NotificationStatus, RecipientType,
)

User = get_user_model()


@pytest.mark.django_db
class TestNotificationTemplateModel:

    def test_create_template(self, db):
        template = NotificationTemplate.objects.create(
            name='payment_receipt',
            notification_type=NotificationType.PAYMENT_RECEIPT,
            email_subject='Payment Received',
            email_template='<p>Your payment of {{ amount }} was received.</p>',
            sms_template='Payment of {{ amount }} received.',
        )
        assert template.pk is not None
        assert template.is_active is True

    def test_str_representation(self, db):
        template = NotificationTemplate.objects.create(
            name='test_template',
            notification_type=NotificationType.GENERAL_ANNOUNCEMENT,
            email_template='Hello',
        )
        assert str(template) == 'test_template'

    def test_unique_name(self, db):
        NotificationTemplate.objects.create(
            name='unique_name',
            notification_type=NotificationType.TERM_BEGINS,
            email_template='Hello',
        )
        with pytest.raises(Exception):
            NotificationTemplate.objects.create(
                name='unique_name',
                notification_type=NotificationType.TERM_ENDS,
                email_template='World',
            )


@pytest.mark.django_db
class TestNotificationModel:

    def _create_notification(self, **kwargs):
        defaults = {
            'notification_type': NotificationType.GENERAL_ANNOUNCEMENT,
            'title': 'Test Notification',
            'message': 'This is a test notification.',
            'recipient_type': RecipientType.STUDENT,
            'recipient_id': 1,
            'priority': NotificationPriority.NORMAL,
            'channels': [NotificationChannel.IN_APP],
        }
        defaults.update(kwargs)
        return Notification.objects.create(**defaults)

    def test_create_notification(self, db):
        notif = self._create_notification()
        assert notif.pk is not None
        assert notif.notification_id is not None
        assert notif.status == NotificationStatus.PENDING

    def test_str_representation(self, db):
        notif = self._create_notification(title='Important Alert')
        assert 'Important Alert' in str(notif)

    def test_mark_as_sent(self, db):
        notif = self._create_notification()
        notif.mark_as_sent()
        notif.refresh_from_db()
        assert notif.status == NotificationStatus.SENT
        assert notif.sent_at is not None

    def test_mark_as_delivered(self, db):
        notif = self._create_notification()
        notif.mark_as_delivered()
        notif.refresh_from_db()
        assert notif.status == NotificationStatus.DELIVERED
        assert notif.delivered_at is not None

    def test_mark_as_read(self, db):
        notif = self._create_notification()
        notif.mark_as_read()
        notif.refresh_from_db()
        assert notif.status == NotificationStatus.READ
        assert notif.read_at is not None

    def test_mark_as_failed(self, db):
        notif = self._create_notification()
        notif.mark_as_failed('Connection timeout')
        notif.refresh_from_db()
        assert notif.status == NotificationStatus.FAILED
        assert notif.error_message == 'Connection timeout'

    def test_ordering_newest_first(self, db):
        self._create_notification(title='First')
        n2 = self._create_notification(title='Second')
        notifs = list(Notification.objects.all())
        assert notifs[0].pk == n2.pk


@pytest.mark.django_db
class TestNotificationPreferenceModel:

    def test_create_preferences(self, user):
        pref = NotificationPreference.objects.create(
            user=user,
            preferences={
                NotificationType.PAYMENT_RECEIPT: [
                    NotificationChannel.EMAIL,
                    NotificationChannel.SMS,
                ],
            },
        )
        assert pref.pk is not None
        assert pref.email_enabled is True
        assert pref.sms_enabled is True

    def test_str_representation(self, user):
        pref = NotificationPreference.objects.create(user=user)
        assert user.email in str(pref)

    def test_get_channels_for_type(self, user):
        channels = [NotificationChannel.EMAIL, NotificationChannel.IN_APP]
        pref = NotificationPreference.objects.create(
            user=user,
            preferences={NotificationType.RESULT_PUBLISHED: channels},
        )
        assert pref.get_channels_for_type(NotificationType.RESULT_PUBLISHED) == channels
        assert pref.get_channels_for_type(NotificationType.PAYMENT_RECEIPT) == []


@pytest.mark.django_db
class TestNotificationLogModel:

    def test_create_log(self, db):
        notif = Notification.objects.create(
            notification_type=NotificationType.GENERAL_ANNOUNCEMENT,
            title='Test',
            message='Test message',
            recipient_type=RecipientType.ALL_STUDENTS,
            channels=[NotificationChannel.EMAIL],
        )
        log = NotificationLog.objects.create(
            notification=notif,
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.SENT,
        )
        assert log.pk is not None

    def test_str_representation(self, db):
        notif = Notification.objects.create(
            notification_type=NotificationType.ATTENDANCE_ALERT,
            title='Alert',
            message='Low attendance',
            recipient_type=RecipientType.PARENT,
            recipient_id=1,
            channels=[NotificationChannel.SMS],
        )
        log = NotificationLog.objects.create(
            notification=notif,
            channel=NotificationChannel.SMS,
            status=NotificationStatus.DELIVERED,
        )
        assert 'Alert' in str(log)
        assert NotificationChannel.SMS in str(log)

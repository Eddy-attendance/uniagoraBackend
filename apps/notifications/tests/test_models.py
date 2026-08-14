from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.notifications.models import (
    DevicePlatform,
    DeviceToken,
    Notification,
    NotificationType,
)
from apps.users.models import User


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="testpass123", full_name="Test User"
        )

    def test_str_returns_title(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="New message from vendor",
        )
        self.assertEqual(str(notification), "New message from vendor")

    def test_default_data_is_empty_dict(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.PLATFORM_ANNOUNCEMENT,
            title="Welcome",
        )
        self.assertEqual(notification.data, {})

    def test_default_body_is_empty_string(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.PLATFORM_ANNOUNCEMENT,
            title="Welcome",
        )
        self.assertEqual(notification.body, "")

    def test_is_read_false_when_read_at_null(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_REVIEW,
            title="New review",
        )
        self.assertFalse(notification.is_read)

    def test_is_read_true_when_read_at_set(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_REVIEW,
            title="New review",
            read_at=timezone.now(),
        )
        self.assertTrue(notification.is_read)

    def test_invalid_notification_type_rejected_by_full_clean(self):
        notification = Notification(
            recipient=self.user,
            notification_type="NOT_A_REAL_TYPE",
            title="Bad type",
        )
        with self.assertRaises(ValidationError):
            notification.full_clean()

    def test_recipient_relationship(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Hi",
        )
        self.assertIn(notification, self.user.notifications.all())

    def test_data_accepts_structured_json(self):
        payload = {"conversation_id": "abc-123", "deep_link": "/chat/abc-123"}
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="New message",
            data=payload,
        )
        notification.refresh_from_db()
        self.assertEqual(notification.data, payload)

    def test_soft_delete_regression(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Hi",
        )
        notification.delete()
        self.assertTrue(Notification.objects.get(pk=notification.pk).is_deleted)
        self.assertFalse(
            Notification.objects.alive().filter(pk=notification.pk).exists()
        )

    def test_default_ordering_is_newest_first(self):
        first = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="First",
        )
        second = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Second",
        )
        results = list(Notification.objects.alive().filter(recipient=self.user))
        self.assertEqual(results, [second, first])

    def test_cascade_delete_with_user_hard_delete(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Hi",
        )
        self.user.delete(hard=True)
        self.assertFalse(Notification.objects.filter(pk=notification.pk).exists())


class DeviceTokenModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="dtuser@example.com", password="testpass123", full_name="Device User"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", password="testpass123", full_name="Other User"
        )

    def test_str_representation(self):
        token = DeviceToken.objects.create(
            user=self.user, token="tok-1", platform=DevicePlatform.ANDROID
        )
        self.assertIn("ANDROID", str(token))

    def test_token_uniqueness(self):
        DeviceToken.objects.create(
            user=self.user, token="dup-token", platform=DevicePlatform.IOS
        )
        with self.assertRaises(IntegrityError):
            DeviceToken.objects.create(
                user=self.other_user, token="dup-token", platform=DevicePlatform.ANDROID
            )

    def test_multiple_devices_per_user(self):
        DeviceToken.objects.create(
            user=self.user, token="tok-a", platform=DevicePlatform.IOS
        )
        DeviceToken.objects.create(
            user=self.user, token="tok-b", platform=DevicePlatform.WEB
        )
        self.assertEqual(self.user.device_tokens.count(), 2)

    def test_invalid_platform_rejected_by_full_clean(self):
        token = DeviceToken(user=self.user, token="tok-bad", platform="WINDOWS_PHONE")
        with self.assertRaises(ValidationError):
            token.full_clean()

    def test_is_active_default_true(self):
        token = DeviceToken.objects.create(
            user=self.user, token="tok-c", platform=DevicePlatform.WEB
        )
        self.assertTrue(token.is_active)

    def test_deactivation_toggle(self):
        token = DeviceToken.objects.create(
            user=self.user, token="tok-d", platform=DevicePlatform.WEB
        )
        token.is_active = False
        token.save(update_fields=["is_active"])
        token.refresh_from_db()
        self.assertFalse(token.is_active)

    def test_ownership_relationship(self):
        token = DeviceToken.objects.create(
            user=self.user, token="tok-e", platform=DevicePlatform.IOS
        )
        self.assertEqual(token.user, self.user)
        self.assertNotEqual(token.user, self.other_user)

    def test_soft_delete_regression(self):
        token = DeviceToken.objects.create(
            user=self.user, token="tok-soft", platform=DevicePlatform.WEB
        )
        token.delete()
        self.assertTrue(DeviceToken.objects.get(pk=token.pk).is_deleted)
        self.assertFalse(DeviceToken.objects.alive().filter(pk=token.pk).exists())

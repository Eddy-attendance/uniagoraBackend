from unittest import mock

from django.test import TestCase
from django.utils import timezone

from apps.common.exceptions import PermissionDeniedError
from apps.notifications.models import DevicePlatform, DeviceToken, NotificationType
from apps.notifications.services import DeviceTokenService, NotificationService
from apps.users.models import User


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="a@example.com", password="pw123456", full_name="A"
        )
        self.other = User.objects.create_user(
            email="b@example.com", password="pw123456", full_name="B"
        )

    def test_create_notification_persists_and_dispatches(self):
        notification = NotificationService.create_notification(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="You have a new message",
            body="Someone messaged you.",
            data={"conversation_id": "123"},
        )
        self.assertIsNotNone(notification.pk)
        self.assertEqual(notification.data, {"conversation_id": "123"})
        self.assertEqual(notification.body, "Someone messaged you.")

    def test_create_notification_defaults_body_and_data(self):
        notification = NotificationService.create_notification(
            recipient=self.user,
            notification_type=NotificationType.PLATFORM_ANNOUNCEMENT,
            title="Welcome",
        )
        self.assertEqual(notification.body, "")
        self.assertEqual(notification.data, {})

    def test_get_for_user_scopes_to_recipient(self):
        NotificationService.create_notification(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Mine",
        )
        NotificationService.create_notification(
            recipient=self.other,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Theirs",
        )
        results = NotificationService.get_for_user(self.user)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().title, "Mine")

    def test_get_for_user_unread_only(self):
        n1 = NotificationService.create_notification(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Unread",
        )
        n2 = NotificationService.create_notification(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Read",
        )
        NotificationService.mark_read(notification=n2, user=self.user)
        unread = NotificationService.get_for_user(self.user, unread_only=True)
        self.assertEqual(list(unread), [n1])

    def test_unread_count(self):
        NotificationService.create_notification(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="1",
        )
        NotificationService.create_notification(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="2",
        )
        self.assertEqual(NotificationService.unread_count(self.user), 2)

    def test_mark_read_sets_read_at(self):
        notification = NotificationService.create_notification(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Hi",
        )
        self.assertIsNone(notification.read_at)
        updated = NotificationService.mark_read(
            notification=notification, user=self.user
        )
        self.assertIsNotNone(updated.read_at)

    def test_mark_read_is_idempotent(self):
        notification = NotificationService.create_notification(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Hi",
        )
        first = NotificationService.mark_read(notification=notification, user=self.user)
        first_read_at = first.read_at
        second = NotificationService.mark_read(
            notification=notification, user=self.user
        )
        self.assertEqual(second.read_at, first_read_at)

    def test_mark_read_rejects_non_owner(self):
        notification = NotificationService.create_notification(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Hi",
        )
        with self.assertRaises(PermissionDeniedError):
            NotificationService.mark_read(notification=notification, user=self.other)

    def test_mark_all_read(self):
        NotificationService.create_notification(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="1",
        )
        NotificationService.create_notification(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="2",
        )
        marked = NotificationService.mark_all_read(self.user)
        self.assertEqual(marked, 2)
        self.assertEqual(NotificationService.unread_count(self.user), 0)

    def test_mark_all_read_only_affects_own_notifications(self):
        NotificationService.create_notification(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Mine",
        )
        NotificationService.create_notification(
            recipient=self.other,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Theirs",
        )
        NotificationService.mark_all_read(self.user)
        self.assertEqual(NotificationService.unread_count(self.other), 1)

    def test_dispatch_is_deferred_until_transaction_commit(self):
        """Regression test for Correction 3: dispatch must not fire until
        the persisting transaction actually commits, and must fire exactly
        once when it does.
        """
        calls = []

        class RecordingDispatcher:
            def dispatch(self, notification):
                calls.append(notification.id)

        with mock.patch(
            "apps.notifications.services.get_dispatcher",
            return_value=RecordingDispatcher(),
        ):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                notification = NotificationService.create_notification(
                    recipient=self.user,
                    notification_type=NotificationType.NEW_MESSAGE,
                    title="Deferred dispatch",
                )

        self.assertEqual(len(callbacks), 1)
        self.assertEqual(calls, [notification.id])


class DeviceTokenServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="dt1@example.com", password="pw123456", full_name="A"
        )
        self.other = User.objects.create_user(
            email="dt2@example.com", password="pw123456", full_name="B"
        )

    def test_register_creates_new_token(self):
        token, created = DeviceTokenService.register(
            user=self.user, token="new-token", platform=DevicePlatform.IOS
        )
        self.assertTrue(created)
        self.assertEqual(token.user, self.user)
        self.assertTrue(token.is_active)

    def test_register_is_idempotent_for_same_user(self):
        DeviceTokenService.register(
            user=self.user, token="same-token", platform=DevicePlatform.IOS
        )
        token, created = DeviceTokenService.register(
            user=self.user, token="same-token", platform=DevicePlatform.ANDROID
        )
        self.assertFalse(created)
        self.assertEqual(token.platform, DevicePlatform.ANDROID)
        self.assertEqual(DeviceToken.objects.filter(token="same-token").count(), 1)

    def test_register_reassigns_and_reactivates_existing_token(self):
        existing = DeviceToken.objects.create(
            user=self.other,
            token="shared-token",
            platform=DevicePlatform.ANDROID,
            is_active=False,
        )
        token, created = DeviceTokenService.register(
            user=self.user, token="shared-token", platform=DevicePlatform.IOS
        )
        self.assertFalse(created)
        existing.refresh_from_db()
        self.assertEqual(existing.user, self.user)
        self.assertTrue(existing.is_active)
        self.assertEqual(existing.platform, DevicePlatform.IOS)
        self.assertEqual(token.pk, existing.pk)

    def test_get_for_user_active_only_by_default(self):
        DeviceToken.objects.create(
            user=self.user, token="t1", platform=DevicePlatform.WEB, is_active=True
        )
        DeviceToken.objects.create(
            user=self.user, token="t2", platform=DevicePlatform.WEB, is_active=False
        )
        active = DeviceTokenService.get_for_user(self.user)
        self.assertEqual(active.count(), 1)

    def test_get_for_user_all_when_active_only_false(self):
        DeviceToken.objects.create(
            user=self.user, token="t3", platform=DevicePlatform.WEB, is_active=True
        )
        DeviceToken.objects.create(
            user=self.user, token="t4", platform=DevicePlatform.WEB, is_active=False
        )
        all_tokens = DeviceTokenService.get_for_user(self.user, active_only=False)
        self.assertEqual(all_tokens.count(), 2)

    def test_deactivate_sets_inactive(self):
        token = DeviceToken.objects.create(
            user=self.user, token="t5", platform=DevicePlatform.WEB
        )
        updated = DeviceTokenService.deactivate(device_token=token, user=self.user)
        self.assertFalse(updated.is_active)

    def test_deactivate_is_idempotent(self):
        token = DeviceToken.objects.create(
            user=self.user, token="t6", platform=DevicePlatform.WEB, is_active=False
        )
        updated = DeviceTokenService.deactivate(device_token=token, user=self.user)
        self.assertFalse(updated.is_active)

    def test_deactivate_rejects_non_owner(self):
        token = DeviceToken.objects.create(
            user=self.user, token="t7", platform=DevicePlatform.WEB
        )
        with self.assertRaises(PermissionDeniedError):
            DeviceTokenService.deactivate(device_token=token, user=self.other)

    def test_register_sets_last_used_at_on_create(self):
        """Regression test for Correction 2."""
        before = timezone.now()
        token, created = DeviceTokenService.register(
            user=self.user, token="fresh-token", platform=DevicePlatform.IOS
        )
        self.assertTrue(created)
        self.assertGreaterEqual(token.last_used_at, before)

    def test_register_updates_last_used_at_on_reactivation(self):
        """Regression test for Correction 2."""
        token, _ = DeviceTokenService.register(
            user=self.user, token="reactivate-token", platform=DevicePlatform.IOS
        )
        stale_time = timezone.now() - timezone.timedelta(days=1)
        DeviceToken.objects.filter(pk=token.pk).update(last_used_at=stale_time)

        updated, created = DeviceTokenService.register(
            user=self.user, token="reactivate-token", platform=DevicePlatform.ANDROID
        )
        self.assertFalse(created)
        self.assertGreater(updated.last_used_at, stale_time)

    def test_deactivate_does_not_update_last_used_at(self):
        """Regression test for Correction 2 — the specific bug flagged:
        deactivation must not implicitly mean "used."
        """
        token, _ = DeviceTokenService.register(
            user=self.user, token="deact-token", platform=DevicePlatform.WEB
        )
        stale_time = timezone.now() - timezone.timedelta(days=1)
        DeviceToken.objects.filter(pk=token.pk).update(last_used_at=stale_time)
        token.refresh_from_db()

        DeviceTokenService.deactivate(device_token=token, user=self.user)
        token.refresh_from_db()
        self.assertEqual(token.last_used_at, stale_time)

    def test_touch_last_used_updates_timestamp(self):
        """Regression test for Correction 2 — the reserved future-dispatch
        hook works as documented.
        """
        token, _ = DeviceTokenService.register(
            user=self.user, token="touch-token", platform=DevicePlatform.WEB
        )
        stale_time = timezone.now() - timezone.timedelta(days=1)
        DeviceToken.objects.filter(pk=token.pk).update(last_used_at=stale_time)
        token.refresh_from_db()

        DeviceTokenService.touch_last_used(device_token=token)
        token.refresh_from_db()
        self.assertGreater(token.last_used_at, stale_time)

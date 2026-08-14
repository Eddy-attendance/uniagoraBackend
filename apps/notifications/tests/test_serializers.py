from django.test import TestCase

from apps.notifications.models import (
    DevicePlatform,
    DeviceToken,
    Notification,
    NotificationType,
)
from apps.notifications.serializers import (
    DeviceTokenRegisterSerializer,
    DeviceTokenSerializer,
    NotificationSerializer,
)
from apps.users.models import User


class NotificationSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="s1@example.com", password="pw123456", full_name="S"
        )

    def test_expected_fields_present(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_REVIEW,
            title="Title",
        )
        data = NotificationSerializer(notification).data
        for field in [
            "id",
            "notification_type",
            "notification_type_display",
            "title",
            "body",
            "data",
            "is_read",
            "read_at",
            "created_at",
        ]:
            self.assertIn(field, data)

    def test_recipient_not_exposed(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_REVIEW,
            title="Title",
        )
        self.assertNotIn("recipient", NotificationSerializer(notification).data)

    def test_is_read_computed_field(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_REVIEW,
            title="Title",
        )
        self.assertFalse(NotificationSerializer(notification).data["is_read"])


class DeviceTokenSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="s2@example.com", password="pw123456", full_name="S2"
        )

    def test_read_fields(self):
        token = DeviceToken.objects.create(
            user=self.user, token="tok", platform=DevicePlatform.WEB
        )
        data = DeviceTokenSerializer(token).data
        self.assertEqual(data["token"], "tok")
        self.assertEqual(data["platform"], "WEB")

    def test_user_not_exposed(self):
        token = DeviceToken.objects.create(
            user=self.user, token="tok2", platform=DevicePlatform.WEB
        )
        self.assertNotIn("user", DeviceTokenSerializer(token).data)


class DeviceTokenRegisterSerializerTests(TestCase):
    def test_valid_payload(self):
        serializer = DeviceTokenRegisterSerializer(
            data={"token": "abc", "platform": "IOS"}
        )
        self.assertTrue(serializer.is_valid())

    def test_blank_token_rejected(self):
        serializer = DeviceTokenRegisterSerializer(
            data={"token": "   ", "platform": "IOS"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("token", serializer.errors)

    def test_invalid_platform_rejected(self):
        serializer = DeviceTokenRegisterSerializer(
            data={"token": "abc", "platform": "SMOKE_SIGNAL"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("platform", serializer.errors)

    def test_missing_fields_rejected(self):
        serializer = DeviceTokenRegisterSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("token", serializer.errors)
        self.assertIn("platform", serializer.errors)

    def test_token_is_trimmed(self):
        serializer = DeviceTokenRegisterSerializer(
            data={"token": "  abc  ", "platform": "WEB"}
        )
        serializer.is_valid()
        self.assertEqual(serializer.validated_data["token"], "abc")

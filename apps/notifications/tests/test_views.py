from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.models import (
    DevicePlatform,
    DeviceToken,
    Notification,
    NotificationType,
)
from apps.users.models import User


class NotificationViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="v1@example.com", password="pw123456", full_name="V1"
        )
        self.other = User.objects.create_user(
            email="v2@example.com", password="pw123456", full_name="V2"
        )

    def test_list_requires_authentication(self):
        response = self.client.get("/api/v1/notifications/")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_list_returns_only_own_notifications(self):
        Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Mine",
        )
        Notification.objects.create(
            recipient=self.other,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Theirs",
        )
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Mine")

    def test_list_envelope_shape(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/notifications/")
        self.assertIn("success", response.data)
        self.assertIn("data", response.data)
        self.assertIn("results", response.data["data"])

    def test_unread_filter(self):
        n1 = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Unread",
        )
        n2 = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Read",
        )
        n2.read_at = timezone.now()
        n2.save(update_fields=["read_at"])
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/notifications/?unread=true")
        titles = [item["title"] for item in response.data["data"]["results"]]
        self.assertEqual(titles, [n1.title])

    def test_unread_count_endpoint(self):
        Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="1",
        )
        Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="2",
        )
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["unread_count"], 2)

    def test_unread_count_requires_authentication(self):
        response = self.client.get("/api/v1/notifications/unread-count/")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_mark_read_success(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Hi",
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(f"/api/v1/notifications/{notification.id}/read/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["data"]["read_at"])

    def test_mark_read_on_other_users_notification_is_not_found(self):
        notification = Notification.objects.create(
            recipient=self.other,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Hi",
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(f"/api/v1/notifications/{notification.id}/read/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_all_read(self):
        Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="1",
        )
        Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="2",
        )
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/v1/notifications/read-all/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["marked_read"], 2)


class DeviceTokenViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="dv1@example.com", password="pw123456", full_name="D1"
        )
        self.other = User.objects.create_user(
            email="dv2@example.com", password="pw123456", full_name="D2"
        )

    def test_register_requires_authentication(self):
        response = self.client.post(
            "/api/v1/notifications/device-tokens/", {"token": "x", "platform": "IOS"}
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_register_creates_token_for_authenticated_user(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/notifications/device-tokens/",
            {"token": "abc-123", "platform": "ANDROID"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            DeviceToken.objects.filter(token="abc-123", user=self.user).exists()
        )

    def test_register_idempotent_returns_200(self):
        self.client.force_authenticate(self.user)
        self.client.post(
            "/api/v1/notifications/device-tokens/",
            {"token": "re-reg", "platform": "IOS"},
        )
        response = self.client.post(
            "/api/v1/notifications/device-tokens/",
            {"token": "re-reg", "platform": "ANDROID"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_register_validation_failure(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/notifications/device-tokens/", {"token": "", "platform": "ANDROID"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_list_returns_only_own_tokens(self):
        DeviceToken.objects.create(
            user=self.user, token="mine", platform=DevicePlatform.WEB
        )
        DeviceToken.objects.create(
            user=self.other, token="theirs", platform=DevicePlatform.WEB
        )
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/notifications/device-tokens/")
        tokens = [item["token"] for item in response.data["data"]]
        self.assertEqual(tokens, ["mine"])

    def test_deactivate_own_token(self):
        token = DeviceToken.objects.create(
            user=self.user, token="deact", platform=DevicePlatform.WEB
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(
            f"/api/v1/notifications/device-tokens/{token.id}/deactivate/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token.refresh_from_db()
        self.assertFalse(token.is_active)

    def test_deactivate_other_users_token_is_not_found(self):
        token = DeviceToken.objects.create(
            user=self.other, token="not-mine", platform=DevicePlatform.WEB
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(
            f"/api/v1/notifications/device-tokens/{token.id}/deactivate/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_response_envelope_shape(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/notifications/device-tokens/",
            {"token": "env-check", "platform": "WEB"},
        )
        self.assertIn("success", response.data)
        self.assertIn("message", response.data)
        self.assertIn("data", response.data)

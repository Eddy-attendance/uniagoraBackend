from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import PermissionDeniedError

from .dispatch import get_dispatcher
from .models import DeviceToken, Notification


class NotificationService:
    """Owns Notification persistence, retrieval, and read-state."""

    @staticmethod
    @transaction.atomic
    def create_notification(*, recipient, notification_type, title, body="", data=None):
        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            body=body or "",
            data=data if data is not None else {},
        )
        transaction.on_commit(lambda: get_dispatcher().dispatch(notification))
        return notification

    @staticmethod
    def get_for_user(user, *, unread_only=False):
        """A user's notifications, newest first."""
        queryset = Notification.objects.alive().filter(recipient=user)
        if unread_only:
            queryset = queryset.filter(read_at__isnull=True)
        return queryset

    @staticmethod
    def unread_count(user):
        """Unread notifications badge query pattern."""
        return (
            Notification.objects.alive()
            .filter(recipient=user, read_at__isnull=True)
            .count()
        )

    @staticmethod
    @transaction.atomic
    def mark_read(*, notification, user):
        if notification.recipient_id != user.id:
            raise PermissionDeniedError("You do not own this notification.")
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at", "updated_at"])
        return notification

    @staticmethod
    @transaction.atomic
    def mark_all_read(user):
        """Bulk mark-read for every currently-unread notification the user
        owns. Returns the number of rows updated.
        """
        return (
            Notification.objects.alive()
            .filter(recipient=user, read_at__isnull=True)
            .update(read_at=timezone.now())
        )


class DeviceTokenService:
    """Owns DeviceToken registration/deactivation."""

    @staticmethod
    @transaction.atomic
    def register(*, user, token, platform):
        now = timezone.now()
        device_token, created = DeviceToken.objects.select_for_update().get_or_create(
            token=token,
            defaults={
                "user": user,
                "platform": platform,
                "is_active": True,
                "last_used_at": now,
            },
        )
        if not created:
            device_token.user = user
            device_token.platform = platform
            device_token.is_active = True
            device_token.last_used_at = now
            device_token.save(
                update_fields=[
                    "user",
                    "platform",
                    "is_active",
                    "last_used_at",
                    "updated_at",
                ]
            )
        return device_token, created

    @staticmethod
    def get_for_user(user, *, active_only=True):
        queryset = DeviceToken.objects.alive().filter(user=user)
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset

    @staticmethod
    @transaction.atomic
    def deactivate(*, device_token, user):
        if device_token.user_id != user.id:
            raise PermissionDeniedError("You do not own this device token.")
        if device_token.is_active:
            device_token.is_active = False
            device_token.save(update_fields=["is_active", "updated_at"])
        return device_token

    @staticmethod
    @transaction.atomic
    def touch_last_used(*, device_token):
        device_token.last_used_at = timezone.now()
        device_token.save(update_fields=["last_used_at", "updated_at"])
        return device_token

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class NotificationType(models.TextChoices):
    NEW_MESSAGE = "NEW_MESSAGE", "New Message"
    VENDOR_VERIFICATION_UPDATE = (
        "VENDOR_VERIFICATION_UPDATE",
        "Vendor Verification Update",
    )
    PRODUCT_MODERATION_UPDATE = "PRODUCT_MODERATION_UPDATE", "Product Moderation Update"
    NEW_REVIEW = "NEW_REVIEW", "New Review"
    PLATFORM_ANNOUNCEMENT = "PLATFORM_ANNOUNCEMENT", "Platform Announcement"


class DevicePlatform(models.TextChoices):
    IOS = "IOS", "iOS"
    ANDROID = "ANDROID", "Android"
    WEB = "WEB", "Web"


class Notification(BaseModel):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=30, choices=NotificationType.choices
    )
    title = models.CharField(max_length=150)
    body = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True, null=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["recipient", "read_at"],
                name="notif_recipient_unread_idx",
                condition=models.Q(read_at__isnull=True),
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def is_read(self):
        return self.read_at is not None


class DeviceToken(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens",
    )
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=10, choices=DevicePlatform.choices)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "is_active"], name="devicetoken_user_active_idx"
            ),
        ]

    def __str__(self):
        return f"{self.platform} token for {self.user}"

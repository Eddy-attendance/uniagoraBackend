"""Notification / DeviceToken models — DDS §4.15, §4.16, §5, §6.

No managers.py exists in this app: DDS names no custom query-shape method
for either model beyond BaseModel's inherited `.alive()`/`.dead()` — the same
"no manager beyond what's DDS-named" precedent already established by
`vendors`, `stores`, and `categories`. The one recognizable read patterns
("a user's notifications", "active tokens for a user") are simple enough to
express inline in the service layer (see services.py) without a dedicated
QuerySet subclass.

No exceptions.py exists either: every failure mode this app needs
(non-owner attempting to mark-read/deactivate) fits `common.exceptions
.PermissionDeniedError` (403) exactly — no new ApplicationError subclass is
warranted, per `common` EDD §27's "only add a new type once the existing
three don't fit" rule, the same reasoning `chat`/`reviews` already applied.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class NotificationType(models.TextChoices):
    """DDS §5 — `NotificationType` (`Notification.notification_type`)."""

    NEW_MESSAGE = "NEW_MESSAGE", "New Message"
    VENDOR_VERIFICATION_UPDATE = (
        "VENDOR_VERIFICATION_UPDATE",
        "Vendor Verification Update",
    )
    PRODUCT_MODERATION_UPDATE = "PRODUCT_MODERATION_UPDATE", "Product Moderation Update"
    NEW_REVIEW = "NEW_REVIEW", "New Review"
    PLATFORM_ANNOUNCEMENT = "PLATFORM_ANNOUNCEMENT", "Platform Announcement"


class DevicePlatform(models.TextChoices):
    """DDS §5 — `DevicePlatform` (`DeviceToken.platform`)."""

    IOS = "IOS", "iOS"
    ANDROID = "ANDROID", "Android"
    WEB = "WEB", "Web"


class Notification(BaseModel):
    """DDS §4.15 — a persisted notification record, decoupled from delivery.

    `read_at IS NULL` means unread; a non-null value means read (§4.15,
    `is_read` property below). `data` is structured JSON for client-side
    deep-linking, defaulting to an empty dict (§4.15). Notifications are
    meaningless without, and legitimately purged with, their recipient
    (`on_delete=CASCADE`, DDS §8) — this is the one hard-delete-adjacent
    cascade in this app, and it is a real Django `CASCADE`, not a soft-delete
    convention (see `common` EDD §22.2 for why the two are different
    mechanics).
    """

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
        # Restated explicitly — a model defining its own Meta does not
        # automatically inherit BaseModel's abstract Meta.ordering (see
        # EDD_users_authentication.md §5 / common EDD §22.3 for the same
        # MRO/Meta nuance applied here).
        ordering = ["-created_at"]
        indexes = [
            # DDS §6: composite partial index — "Unread badge/count per
            # user". This single index covers both the `recipient` and
            # `read_at` "Indexed" markers in DDS §4.15's field table; they
            # describe one index, not two (confirmed against DDS §6's
            # single explicit table row for Notification).
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
    """DDS §4.16 — a registered push-notification device token.

    A user may have multiple devices (no uniqueness on `user`). `token` is
    globally unique (DDS §4.16 Constraints: `UNIQUE(token)`). Deactivated
    rather than hard-deleted on invalidation, "for audit trail" (DDS §4.16
    Notes) — this app exposes no delete endpoint or admin action for
    DeviceToken at all, only deactivation.

    `last_used_at` semantics (CTO-corrected): this field is deliberately
    **not** `auto_now=True`. `auto_now` updates on every `.save()` call
    regardless of `update_fields`, which would make routine, unrelated
    writes (e.g. deactivation) silently misrepresent themselves as "usage."
    Instead, `last_used_at` defaults to the registration timestamp and is
    thereafter only ever advanced by an explicit write in the service layer
    (`DeviceTokenService.register()` on (re)registration,
    `DeviceTokenService.touch_last_used()` reserved for a future confirmed-
    delivery dispatcher). `DeviceTokenService.deactivate()` never touches
    it.

    Flagged DDS deviation (CTO confirmation requested): DDS §4.16 names
    this field's Default literally as `auto_now`. This implementation uses
    `default=timezone.now` with explicit service-layer writes instead,
    because a literal `auto_now=True` cannot satisfy the same DDS row's own
    Notes text ("refreshed on each successful dispatch/registration ping")
    — `auto_now` refreshes on every save, not on a specific event. See
    NOTIFICATIONS_EDD.md §4, Correction 2 for the full reasoning.
    """

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
            # DDS §6: "(user, is_active) | Composite B-tree | Active-token
            # lookup at dispatch time".
            models.Index(
                fields=["user", "is_active"], name="devicetoken_user_active_idx"
            ),
        ]

    def __str__(self):
        return f"{self.platform} token for {self.user}"

"""Service layer — DDS §10: "Notification | NotificationService | Record
creation; dispatch delegated to NotificationDispatcher strategy" and
"DeviceToken | NotificationService (device registration sub-concern) |
Registration/deactivation".

Split into two classes (`NotificationService`, `DeviceTokenService`) rather
than one, mirroring the `products` app's own precedent of splitting one
DDS-named "owning service" into several focused classes when doing so keeps
each class single-responsibility — DDS §10's single "NotificationService"
row is the *ownership* statement, not a mandate that both models share one
class body.
"""

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
        """Persist a Notification, then schedule dispatch for *after* the
        surrounding transaction commits.

        CTO-corrected transaction boundary: dispatch is registered via
        `transaction.on_commit()` rather than invoked inline inside this
        atomic block. This guarantees the Notification row is durably
        persisted before any external side effect (present: none, via
        `NoOpDispatcher`; future: an FCM push) is attempted, and — just as
        importantly — guarantees a dispatcher is never invoked for a
        Notification whose own transaction ultimately rolled back. If this
        method is called from within an already-open outer transaction,
        `on_commit` defers to that outer transaction's own commit, which is
        the correct behavior (still "after persistence is durable," not
        "after this specific nested block exits").
        """
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
        """A user's notifications, newest first. DDS §11 query pattern."""
        queryset = Notification.objects.alive().filter(recipient=user)
        if unread_only:
            queryset = queryset.filter(read_at__isnull=True)
        return queryset

    @staticmethod
    def unread_count(user):
        """DDS §11: "Unread notifications badge" query pattern."""
        return (
            Notification.objects.alive()
            .filter(recipient=user, read_at__isnull=True)
            .count()
        )

    @staticmethod
    @transaction.atomic
    def mark_read(*, notification, user):
        """Mark a single notification read. Idempotent — re-marking an
        already-read notification is not an error (DDS §9.8's lifecycle
        has exactly one forward transition, unread -> read).

        Ownership is re-verified here (defense-in-depth) even though the
        view already scopes its queryset to `request.user`.
        """
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
        """Register (or re-register) a device token for `user`.

        Idempotent upsert-by-token: if the token already exists (same
        device re-registering, or the same physical device previously
        registered under a different account), it is reassigned to the
        requesting user, reactivated, and its platform updated, rather than
        raising a conflict — this Engineering Decision is unchanged from
        the prior review.

        CTO-corrected `last_used_at` handling: registration is explicitly
        treated as a usage event on *both* branches (initial create and
        reactivation), stamped once as `now` and reused for both the
        `defaults` dict and the update path, so the create/reactivate
        timestamps can't drift from each other within a single call.

        Row-locked via `select_for_update()` to keep concurrent
        registration attempts for the same token from racing.
        """
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
        """A user's device tokens. `active_only=True` is the dispatch-time
        shape (DDS §11: "Active push targets for a user"); `active_only=False`
        supports a client wanting to see its full registration history.
        """
        queryset = DeviceToken.objects.alive().filter(user=user)
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset

    @staticmethod
    @transaction.atomic
    def deactivate(*, device_token, user):
        """Deactivate a device token. Idempotent — deactivating an
        already-inactive token is not an error.

        Deliberately does NOT touch `last_used_at` — deactivation is not a
        usage event, and (now that the field is no longer `auto_now`) this
        exclusion is actually effective rather than silently overridden.
        """
        if device_token.user_id != user.id:
            raise PermissionDeniedError("You do not own this device token.")
        if device_token.is_active:
            device_token.is_active = False
            device_token.save(update_fields=["is_active", "updated_at"])
        return device_token

    @staticmethod
    @transaction.atomic
    def touch_last_used(*, device_token):
        """Advance `last_used_at` to now.

        Reserved for a future dispatcher (e.g. `FCMDispatcher`) to call
        after a *confirmed* successful delivery to this specific device
        token. Not called anywhere in this MVP delivery — `NoOpDispatcher`
        performs no real delivery and must not misrepresent that a push
        occurred by advancing this timestamp on its behalf. Exposed now so
        that wiring a future dispatcher requires no change to this service
        or to `DeviceToken`'s schema.
        """
        device_token.last_used_at = timezone.now()
        device_token.save(update_fields=["last_used_at", "updated_at"])
        return device_token

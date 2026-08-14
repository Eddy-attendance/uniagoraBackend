"""Notification dispatch abstraction — Strategy pattern per Architecture §6.

Architecture §6, verbatim: "Strategy pattern — `NotificationDispatcher`
interface with swappable implementations (`NoOpDispatcher` now,
`FCMDispatcher` later) behind one settings-driven binding."

Architecture §13: "Push notifications | `Notification`, `DeviceToken`
models; `NotificationDispatcher` interface with `NoOpDispatcher` |
Implement `FCMDispatcher`, swap the settings binding."

The dispatcher is deliberately dumb about persistence: `NotificationService
.create_notification()` always persists the `Notification` row *first*,
inside its own transaction, and only calls `dispatch()` afterward — the
dispatcher never becomes the owner of the notification record (per the
task brief's explicit requirement). A dispatcher raising, timing out, or
doing nothing at all (as `NoOpDispatcher` does) can never cause a
notification to fail to be recorded in-app.
"""

from django.conf import settings
from django.utils.module_loading import import_string


class NotificationDispatcher:
    """Interface every dispatch strategy implements."""

    def dispatch(self, notification):
        """Attempt external delivery for an already-persisted Notification.

        Implementations must not raise for expected delivery failures (a
        dead token, a provider outage) — those are the dispatcher's own
        concern, not something that should propagate into the caller's
        request/response cycle. `NotificationService` does not wrap this
        call in a try/except; a well-behaved dispatcher swallows its own
        transient errors internally (logging them), consistent with how
        `NoOpDispatcher` trivially satisfies this by doing nothing.
        """
        raise NotImplementedError


class NoOpDispatcher(NotificationDispatcher):
    """MVP dispatcher. Performs no external push delivery.

    The persisted `Notification` row is the complete, correct MVP behavior
    (in-app notifications, per PRD §14's "Push notifications include..."
    list — MVP delivery is the in-app record itself; real FCM push is
    explicitly future infrastructure per the task brief). This class exists
    solely to satisfy the `NotificationDispatcher` interface until
    `FCMDispatcher` is implemented.
    """

    def dispatch(self, notification):
        return None


def get_dispatcher():
    """Resolve the configured dispatcher, defaulting to `NoOpDispatcher`.

    `NOTIFICATION_DISPATCHER_CLASS` is an optional Django setting holding a
    dotted import path (e.g. `"apps.notifications.dispatch.FCMDispatcher"`
    once that class exists). Leaving the setting unset is the correct MVP
    configuration — no setting needs to be added for this delivery to work.
    """
    dispatcher_path = getattr(settings, "NOTIFICATION_DISPATCHER_CLASS", None)
    if not dispatcher_path:
        return NoOpDispatcher()
    dispatcher_cls = import_string(dispatcher_path)
    return dispatcher_cls()

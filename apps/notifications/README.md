# `notifications` App

**Build order position:** 10th (`... → reports → notifications → admin_dashboard`)

## Purpose

Owns persisted `Notification` records, `DeviceToken`
registration, and the `NotificationDispatcher` delivery-abstraction — but
**not** the business events that trigger a notification. Domain apps call
into this app; this app never calls into them.

## Models

- **`Notification`** — a persisted, in-app notification for one recipient.
  `read_at IS NULL` = unread. `data` is structured JSON for client-side
  deep-linking. Five `notification_type` values (DDS §5): `NEW_MESSAGE`,
  `VENDOR_VERIFICATION_UPDATE`, `PRODUCT_MODERATION_UPDATE`, `NEW_REVIEW`,
  `PLATFORM_ANNOUNCEMENT`.
- **`DeviceToken`** — an FCM registration token belonging to a user. A user
  may register multiple devices. `is_active` is deactivated (never
  deleted) on invalidation, for audit trail (DDS §4.16). `last_used_at` is
  explicitly stamped by the service layer on registration/reactivation —
  see `NOTIFICATIONS_EDD.md` §4, Correction 2 for the corrected semantics.

## Service Layer

- **`NotificationService`** — `create_notification()`, `get_for_user()`,
  `unread_count()`, `mark_read()`, `mark_all_read()`.
- **`DeviceTokenService`** — `register()` (idempotent upsert-by-token),
  `get_for_user()`, `deactivate()`, `touch_last_used()` (reserved for a
  future dispatcher on confirmed delivery, not called in MVP).

Both classes fulfil the single DDS §10 "NotificationService" ownership row
— see `NOTIFICATIONS_EDD.md` §1 for why they're split into two classes.

## Dispatcher Architecture

```
Domain Event (chat / vendors / products / reviews)
    │
    ▼
NotificationService.create_notification()
    │
    ▼
Notification row persisted (always first, inside its own transaction)
    │
    ▼
transaction.on_commit(...)  ← dispatch deferred until commit
    │
    ▼
NotificationDispatcher.dispatch()
    │
    ▼
NoOpDispatcher   ← MVP, bound by default, no external delivery
FCMDispatcher    ← future, swapped in via NOTIFICATION_DISPATCHER_CLASS setting
```

**MVP:** `NoOpDispatcher` performs no external push delivery. The
persisted `Notification` row *is* the MVP notification — the in-app
record, listable/markable-read via the API below. Dispatch is scheduled
via `transaction.on_commit()` so a rolled-back transaction never triggers
a dispatcher call (see `NOTIFICATIONS_EDD.md` §4, Correction 3).

**Future:** implement `FCMDispatcher(NotificationDispatcher)` anywhere
importable, and set:
```python
NOTIFICATION_DISPATCHER_CLASS = "apps.notifications.dispatch.FCMDispatcher"
```
No change to `NotificationService`, any calling domain app, or the
`Notification`/`DeviceToken` models is required. A future `FCMDispatcher`
that confirms successful delivery to a specific device may call
`DeviceTokenService.touch_last_used()` to advance `last_used_at` — this
hook exists now precisely so that wiring requires no further schema or
service change.

## API Overview

All routes under `/api/v1/notifications/`, standard envelope, JWT auth
(`IsAuthenticatedCustomer`) required on every endpoint.

| Method | Path | Notes |
|---|---|---|
| `GET` | `/notifications/` | Own notifications, paginated, newest-first. `?unread=true` filters to unread-only. |
| `GET` | `/notifications/unread-count/` | `{"unread_count": <int>}` |
| `POST` | `/notifications/{id}/read/` | Idempotent; 404 if not the requester's own notification |
| `POST` | `/notifications/read-all/` | `{"marked_read": <int>}` |
| `GET` | `/notifications/device-tokens/` | Own device tokens (active + inactive), unpaginated |
| `POST` | `/notifications/device-tokens/` | Register/upsert `{"token": "...", "platform": "IOS\|ANDROID\|WEB"}`. `201` new, `200` idempotent update |
| `POST` | `/notifications/device-tokens/{id}/deactivate/` | Idempotent; 404 if not the requester's own token |

## Calling This App From Another Domain App

```python
from apps.notifications.services import NotificationService
from apps.notifications.models import NotificationType

NotificationService.create_notification(
    recipient=some_user,
    notification_type=NotificationType.NEW_MESSAGE,
    title="New message from Example Store",
    body="You have a new message about your listing.",
    data={"conversation_id": str(conversation.id)},
)
```

This app is never imported by, and never imports, another domain app's
`views.py`/`serializers.py`/service internals — only `User` (via
`settings.AUTH_USER_MODEL`) and `common`/`core`'s shared infrastructure.

## MVP vs. Future FCM

This delivery implements **no real push delivery**. `NoOpDispatcher` is
the only bound dispatcher; it performs no external side effect. Real FCM
delivery, retry/backoff, and delivery-confirmation-driven
`touch_last_used()` calls are explicitly out of scope until an
`FCMDispatcher` is implemented and bound via `NOTIFICATION_DISPATCHER_CLASS`.

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """AppConfig for the notifications app.

    Owns Notification records and DeviceToken registration per DDS §3/§4.15/§4.16.
    Owns no business logic that triggers notifications — that belongs to each
    domain app's own service layer (chat, vendors, products, reviews, ...),
    which call into NotificationService.create_notification(). See README.md.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "Notifications"

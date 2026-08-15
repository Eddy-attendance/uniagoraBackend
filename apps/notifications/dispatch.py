from django.conf import settings
from django.utils.module_loading import import_string


class NotificationDispatcher:
    """Interface every dispatch strategy implements."""

    def dispatch(self, notification):
        """Attempt external delivery for an already-persisted Notification."""
        raise NotImplementedError


class NoOpDispatcher(NotificationDispatcher):
    """MVP dispatcher. Performs no external push delivery."""

    def dispatch(self, notification):
        return None


def get_dispatcher():
    """Resolve the configured dispatcher, defaulting to `NoOpDispatcher`."""
    dispatcher_path = getattr(settings, "NOTIFICATION_DISPATCHER_CLASS", None)
    if not dispatcher_path:
        return NoOpDispatcher()
    dispatcher_cls = import_string(dispatcher_path)
    return dispatcher_cls()

from django.test import TestCase, override_settings

from apps.notifications.dispatch import (
    NoOpDispatcher,
    NotificationDispatcher,
    get_dispatcher,
)
from apps.notifications.models import Notification, NotificationType
from apps.users.models import User


class DispatchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="dispatch@example.com",
            password="testpass123",
            full_name="Dispatch User",
        )

    def test_default_dispatcher_is_noop(self):
        self.assertIsInstance(get_dispatcher(), NoOpDispatcher)

    def test_noop_dispatcher_returns_none_and_raises_nothing(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.NEW_MESSAGE,
            title="Hi",
        )
        dispatcher = NoOpDispatcher()
        self.assertIsNone(dispatcher.dispatch(notification))

    def test_base_dispatcher_interface_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            NotificationDispatcher().dispatch(None)

    @override_settings(
        NOTIFICATION_DISPATCHER_CLASS="apps.notifications.dispatch.NoOpDispatcher"
    )
    def test_dispatcher_resolved_from_settings_binding(self):
        self.assertIsInstance(get_dispatcher(), NoOpDispatcher)

    @override_settings(NOTIFICATION_DISPATCHER_CLASS=None)
    def test_unset_setting_falls_back_to_noop(self):
        self.assertIsInstance(get_dispatcher(), NoOpDispatcher)

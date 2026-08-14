from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification-list"),
    path(
        "unread-count/",
        views.NotificationUnreadCountView.as_view(),
        name="notification-unread-count",
    ),
    path(
        "read-all/",
        views.NotificationMarkAllReadView.as_view(),
        name="notification-mark-all-read",
    ),
    path(
        "<uuid:pk>/read/",
        views.NotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),
    path(
        "device-tokens/",
        views.DeviceTokenListCreateView.as_view(),
        name="device-token-list-create",
    ),
    path(
        "device-tokens/<uuid:pk>/deactivate/",
        views.DeviceTokenDeactivateView.as_view(),
        name="device-token-deactivate",
    ),
]

from django.contrib import admin

from apps.common.admin import SoftDeleteAdminMixin

from .models import DeviceToken, Notification


@admin.register(Notification)
class NotificationAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    """DDS §9.8: notifications have no further lifecycle and are not
    deleted in MVP. Deletion (soft or hard) is intentionally not exposed
    through this admin — neither the per-object action nor the bulk
    "delete_selected" action is available. This is the simplest,
    project-consistent way to prevent an admin-only deletion path from
    silently contradicting the documented lifecycle; it introduces no new
    model behavior.
    """

    list_display = (
        "id",
        "recipient",
        "notification_type",
        "title",
        "is_read",
        "created_at",
    )
    list_filter = ("notification_type",)
    search_fields = ("title", "recipient__email")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        for action_name in list(actions.keys()):
            if "delete" in action_name:
                actions.pop(action_name, None)
        return actions


@admin.register(DeviceToken)
class DeviceTokenAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    """DDS §4.16/§9.9: device tokens are deactivated, never deleted, "for
    audit trail". Deletion is intentionally not exposed here for the same
    reason and via the same mechanism as NotificationAdmin above — use the
    `is_active` toggle (via the app's own API/service, not this admin) to
    invalidate a token.
    """

    list_display = ("id", "user", "platform", "is_active", "last_used_at", "created_at")
    list_filter = ("platform", "is_active")
    search_fields = ("token", "user__email")
    readonly_fields = ("created_at", "updated_at", "last_used_at")
    ordering = ("-created_at",)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        for action_name in list(actions.keys()):
            if "delete" in action_name:
                actions.pop(action_name, None)
        return actions

from django.contrib import admin

from apps.common.admin import SoftDeleteAdminMixin

from .models import DeviceToken, Notification


@admin.register(Notification)
class NotificationAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
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

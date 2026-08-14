from rest_framework import serializers

from .models import DevicePlatform, DeviceToken, Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Read-only — every Notification response body."""

    notification_type_display = serializers.CharField(
        source="get_notification_type_display", read_only=True
    )
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "notification_type_display",
            "title",
            "body",
            "data",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Read-only — every DeviceToken response body."""

    platform_display = serializers.CharField(
        source="get_platform_display", read_only=True
    )

    class Meta:
        model = DeviceToken
        fields = [
            "id",
            "token",
            "platform",
            "platform_display",
            "is_active",
            "last_used_at",
            "created_at",
        ]
        read_only_fields = fields


class DeviceTokenRegisterSerializer(serializers.Serializer):
    """The only input-accepting serializer in this app.

    `user` is never accepted from the client — it is always
    `request.user`, derived server-side in the view, never a client-
    supplied identifier (matching Architecture §8's "never trusts a
    vendor/store ID from the request body" principle, applied here to
    device-token ownership).
    """

    token = serializers.CharField(
        max_length=255, allow_blank=False, trim_whitespace=True
    )
    platform = serializers.ChoiceField(choices=DevicePlatform.choices)

    def validate_token(self, value):
        if not value.strip():
            raise serializers.ValidationError("token must not be blank.")
        return value.strip()

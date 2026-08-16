from rest_framework import serializers

from .models import DevicePlatform, DeviceToken, Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Read-only — every Notification response body."""

    notification_type_display = serializers.CharField(
        source="get_notification_type_display",
        read_only=True,
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
        source="get_platform_display",
        read_only=True,
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
    token = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )
    platform = serializers.ChoiceField(choices=DevicePlatform.choices)

    def validate_token(self, value):
        if not value.strip():
            raise serializers.ValidationError("token must not be blank.")
        return value.strip()


# ---------------------------------------------------------------------------
# OpenAPI response serializers
# ---------------------------------------------------------------------------


class UnreadCountDataSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


class MarkAllReadDataSerializer(serializers.Serializer):
    marked_read = serializers.IntegerField()


class UnreadCountResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = UnreadCountDataSerializer()


class MarkAllReadResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = MarkAllReadDataSerializer()


class NotificationResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = NotificationSerializer()


class DeviceTokenResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = DeviceTokenSerializer()


class DeviceTokenListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = DeviceTokenSerializer(many=True)


class NotificationPaginationDataSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    current_page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = NotificationSerializer(many=True)


class NotificationListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = NotificationPaginationDataSerializer()

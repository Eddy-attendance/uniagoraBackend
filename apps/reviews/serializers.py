from rest_framework import serializers

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="conversation.customer.full_name", read_only=True
    )
    conversation_id = serializers.UUIDField(source="conversation.id", read_only=True)
    store_id = serializers.UUIDField(source="store.id", read_only=True)
    store_slug = serializers.CharField(source="store.slug", read_only=True)
    store_display_name = serializers.CharField(
        source="store.display_name", read_only=True
    )
    is_edited = serializers.BooleanField(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "conversation_id",
            "store_id",
            "store_slug",
            "store_display_name",
            "customer_name",
            "rating",
            "comment",
            "is_edited",
            "edited_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ReviewCreateSerializer(serializers.ModelSerializer):
    """The only input-accepting serializer for creation. `conversation`
    (URL) and `store` (service-derived) are never fields here — this is
    the structural guarantee behind "client cannot control Store"."""

    rating = serializers.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        extra_kwargs = {
            "comment": {"required": False, "allow_null": True, "allow_blank": True}
        }


class ReviewUpdateSerializer(serializers.ModelSerializer):
    """Partial-update serializer for `PATCH /reviews/{id}/`. Ownership is
    enforced by `IsReviewOwner` + `ReviewService.update`, never here."""

    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        extra_kwargs = {
            "comment": {"required": False, "allow_null": True, "allow_blank": True}
        }

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one of rating or comment must be provided."
            )
        return attrs

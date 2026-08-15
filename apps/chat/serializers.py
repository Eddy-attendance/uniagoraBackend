from rest_framework import serializers

from apps.chat.models import Conversation, Message
from apps.products.models import Product
from apps.vendors.models import VendorProfile


class ConversationSerializer(serializers.ModelSerializer):
    """Read-only. Used for list/retrieve/create-echo/complete-echo."""

    vendor_store_name = serializers.CharField(
        source="vendor.store_name", read_only=True
    )
    product_name = serializers.CharField(
        source="product.name", read_only=True, default=None
    )
    unread_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "customer",
            "vendor",
            "vendor_store_name",
            "product",
            "product_name",
            "transaction_status",
            "completed_at",
            "unread_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ConversationCreateSerializer(serializers.Serializer):
    vendor = serializers.PrimaryKeyRelatedField(queryset=VendorProfile.objects.alive())
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.alive(), required=False, allow_null=True
    )

    def validate(self, attrs):
        product = attrs.get("product")
        vendor = attrs.get("vendor")
        if product is not None and product.store.vendor_profile_id != vendor.id:
            raise serializers.ValidationError(
                {"product": "The selected product does not belong to this vendor."}
            )
        return attrs


class MessageSerializer(serializers.ModelSerializer):
    """Read-only. Used for message list and create-echo."""

    is_own = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender",
            "content_type",
            "body",
            "read_at",
            "is_own",
            "created_at",
        ]
        read_only_fields = fields

    def get_is_own(self, obj):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        return obj.sender_id == request.user.id


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(allow_blank=False, trim_whitespace=True)

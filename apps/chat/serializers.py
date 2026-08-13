"""
apps/chat/serializers.py

Serializers handle input validation and output representation only —
no business logic (Django Standards: "Serializers handle serialization
and validation only"). Server-controlled fields (`customer`, `sender`,
`transaction_status`, `completed_at`, `read_at`) are never accepted from
client input at this layer; every write-serializer below deliberately
excludes them from its field set rather than merely marking them
read-only, so there is no field a client could ever populate for them
(mirrors the pattern `stores`' `StoreWriteSerializer` already
establishes for `slug`/`is_active`).
"""

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
    # CTO review fix: no longer a SerializerMethodField running one query
    # per conversation (N+1 on a list of N conversations). The view's
    # queryset (`ConversationViewSet.get_queryset`) annotates each row
    # with `unread_count` directly via a conditional `Count` — this
    # field just surfaces that already-computed value. `default=0`
    # covers the two call sites that serialize a single, freshly
    # created/updated instance rather than a row pulled from the
    # annotated queryset (`create`/`complete` — see `views.py`, which
    # re-fetches through the annotated queryset before serializing
    # specifically so this default is never actually exercised in
    # normal flow; it remains only as a defensive fallback, e.g. for a
    # serializer used directly against a bare instance in a test).
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
    """
    The only input-accepting conversation serializer. `customer` is never
    a field here — it is always derived from `request.user` in the view,
    which is precisely what makes "Vendors cannot initiate conversations"
    structurally true (PRD §10) rather than merely permission-gated.

    `vendor` validates only that the referenced `VendorProfile` exists
    and is alive (not soft-deleted) — CTO review fix: verification
    eligibility (`status == VERIFIED`) is a business rule, not an input-
    shape concern, and belongs solely to `ConversationService.initiate()`
    (DDS §7.2 vs §7.3's own layering distinction). Restricting this
    queryset to `VERIFIED` vendors previously meant an unverified vendor
    was rejected here with `400` before the request ever reached the
    service, while the service's own identical check would have raised
    `409` — two different HTTP semantics for the same rule. The
    queryset now only enforces "this vendor exists", so every request
    reaches the service, and `409 Conflict` is the single, consistent
    outcome for a non-verified vendor.
    """

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
    """
    The only input-accepting message serializer. `content_type` is always
    TEXT server-side in MVP (not even accepted as a field, so the IMAGE
    enum value stays genuinely unreachable); `sender`/`conversation` are
    always derived server-side.
    """

    body = serializers.CharField(allow_blank=False, trim_whitespace=True)

"""
apps/products/serializers.py

Separate serializers for read / create / update / inventory mutation / image
operations / category assignment (instruction §19). Clients can never
populate `university`, `status`, `listed_at`, `expires_at`, `views_count`,
`search_vector`, or store ownership through any of these — those fields are
either absent from every writable serializer's field list, or (for `store`)
never accepted as client input at all (derived from `request.user`).
"""

from decimal import Decimal

from rest_framework import serializers

from apps.categories.models import Category

from .models import Product, ProductCondition, ProductImage


def _reject_duplicate_category_ids(value):
    """Shared field-level validator for every `category_ids` input surface
    (create / update / category-assignment). Rejects duplicates with a clean
    serializer `ValidationError` before the value ever reaches
    `ProductService.set_categories()` — CTO correction: previously a
    duplicate could reach `bulk_create()` and surface as a raw DB
    `IntegrityError` against `UNIQUE(product, category)`.
    """
    if len(value) != len(set(value)):
        raise serializers.ValidationError("Duplicate category IDs are not allowed.")


class CategoryBriefSerializer(serializers.ModelSerializer):
    """Minimal, self-contained nested representation — deliberately not
    importing `categories.serializers.CategorySerializer` directly, to avoid
    coupling to its exact (undocumented-to-this-session) field set."""

    class Meta:
        model = Category
        fields = ["id", "name", "slug"]
        read_only_fields = fields


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "is_primary", "display_order"]
        read_only_fields = fields


class ProductSerializer(serializers.ModelSerializer):
    """Read-only, full representation — used for every response body (list
    results, retrieve, and the echoed object after every mutating action)."""

    store = serializers.SerializerMethodField()
    university = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()
    condition_display = serializers.CharField(
        source="get_condition_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "slug",
            "name",
            "description",
            "price",
            "condition",
            "condition_display",
            "quantity",
            "availability",
            "campus_location",
            "status",
            "status_display",
            "views_count",
            "listed_at",
            "expires_at",
            "store",
            "university",
            "categories",
            "images",
            "primary_image",
        ]
        read_only_fields = fields

    def get_store(self, obj):
        return {
            "id": str(obj.store_id),
            "slug": obj.store.slug,
            "display_name": obj.store.display_name,
        }

    def get_university(self, obj):
        return {
            "id": str(obj.university_id),
            "name": obj.university.name,
            "short_name": obj.university.short_name,
        }

    def get_categories(self, obj):
        links = obj.category_links.select_related("category").filter(
            category__is_active=True
        )
        return CategoryBriefSerializer(
            [link.category for link in links], many=True
        ).data

    def get_images(self, obj):
        images = obj.images.alive().order_by("display_order")
        return ProductImageSerializer(images, many=True).data

    def get_primary_image(self, obj):
        image = obj.primary_image
        return ProductImageSerializer(image).data if image else None

    def get_availability(self, obj):
        """DDS §5: out-of-stock is a derived condition (`quantity == 0`),
        never a `Product.status` value. Exposed as a self-documenting string
        rather than a boolean to avoid the inverted-naming ambiguity of
        `is_out_of_stock` (CTO correction — replaces that field). Backed by
        `Product.is_out_of_stock`; `status`/inventory semantics are
        unchanged."""
        return "OUT_OF_STOCK" if obj.is_out_of_stock else "IN_STOCK"


class ProductCreateSerializer(serializers.Serializer):
    """The only serializer that accepts client input for product creation.

    A primary image is required at creation time because the PRD/DDS require
    every persisted listing to have at least one image and exactly one primary
    image.

    `store`/`university`/`status`/`slug`/`listed_at`/`expires_at`/
    `views_count`/`search_vector` are absent entirely — store ownership is
    derived from `request.user.vendor_profile` at the view/service layer,
    never from client input.
    """

    name = serializers.CharField(max_length=200)
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
    )
    condition = serializers.ChoiceField(choices=ProductCondition.choices)
    quantity = serializers.IntegerField(
        required=False,
        min_value=0,
        default=1,
    )
    campus_location = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=150,
    )
    category_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        validators=[_reject_duplicate_category_ids],
    )
    primary_image = serializers.ImageField(required=True)


class ProductUpdateSerializer(serializers.Serializer):
    """Partial update. Deliberately excludes `quantity` — inventory mutation
    is owned by `InventoryUpdateSerializer`/`InventoryService` — and every
    lifecycle/derived/ownership field."""

    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
    )
    condition = serializers.ChoiceField(
        choices=ProductCondition.choices, required=False
    )
    campus_location = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=150,
    )
    category_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        validators=[_reject_duplicate_category_ids],
    )


class ProductListQuerySerializer(serializers.Serializer):
    """Validates marketplace browse/search query parameters.

    Query parameters are API input and therefore must be validated before
    reaching the queryset composition helpers in products/search/.
    """

    q = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    category = serializers.SlugField(
        required=False,
        allow_blank=True,
    )
    min_price = serializers.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=10,
        decimal_places=2,
    )
    max_price = serializers.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=10,
        decimal_places=2,
    )
    condition = serializers.ChoiceField(
        required=False,
        choices=ProductCondition.choices,
    )
    ordering = serializers.ChoiceField(
        required=False,
        choices=(
            ("newest", "Newest"),
            ("price_asc", "Lowest Price"),
            ("price_desc", "Highest Price"),
        ),
    )

    def validate(self, attrs):
        min_price = attrs.get("min_price")
        max_price = attrs.get("max_price")

        if min_price is not None and max_price is not None and min_price > max_price:
            raise serializers.ValidationError(
                {"min_price": ("min_price must be less than or equal to max_price.")}
            )

        return attrs


class InventoryUpdateSerializer(serializers.Serializer):
    """Absolute quantity set — the only inventory-mutating input surface
    exposed at the API layer; `InventoryService` also exposes
    increase/decrease for future/internal use (instruction §22)."""

    quantity = serializers.IntegerField(min_value=0)


class ProductCategoryAssignmentSerializer(serializers.Serializer):
    """Full-replace category assignment payload for `PUT .../categories/`."""

    category_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
        validators=[_reject_duplicate_category_ids],
    )


class ProductImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()
    is_primary = serializers.BooleanField(required=False)
    display_order = serializers.IntegerField(required=False, min_value=0)

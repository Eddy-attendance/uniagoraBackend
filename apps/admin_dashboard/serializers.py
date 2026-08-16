"""Admin Dashboard Serializers"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


class DashboardSummarySerializer(serializers.Serializer):
    users = serializers.DictField()
    vendors = serializers.DictField()
    products = serializers.DictField()
    categories = serializers.DictField()
    reports = serializers.DictField()


class AdminUserSerializer(serializers.Serializer):
    """Read-only. is_active is presented here but is never writable
    through this serializer — the activate/deactivate actions are
    dedicated endpoints backed by UserService, not a PATCH field."""

    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    phone_number = serializers.CharField(read_only=True, allow_null=True)
    is_active = serializers.BooleanField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    active_university = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    @extend_schema_field(
        {
            "type": "object",
            "nullable": True,
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "name": {"type": "string"},
                "short_name": {"type": "string"},
            },
        }
    )
    def get_active_university(self, obj):
        if obj.active_university_id is None:
            return None
        return {
            "id": str(obj.active_university_id),
            "name": obj.active_university.name,
            "short_name": obj.active_university.short_name,
        }


class AdminVendorSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(read_only=True)
    store_name = serializers.CharField(read_only=True)
    vendor_type = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    university_id = serializers.UUIDField(read_only=True)
    submitted_at = serializers.DateTimeField(read_only=True)
    reviewed_at = serializers.DateTimeField(read_only=True, allow_null=True)


class AdminProductSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    name = serializers.CharField(read_only=True)
    store_id = serializers.UUIDField(read_only=True)
    university_id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    listed_at = serializers.DateTimeField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)


class AdminCategorySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    parent_id = serializers.UUIDField(read_only=True, allow_null=True)
    display_order = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)


class AdminCategoryWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    parent = serializers.SlugField(required=False, allow_null=True)
    display_order = serializers.IntegerField(required=False, default=0, min_value=0)


class AdminCategoryUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)


class AdminResolutionSerializer(serializers.Serializer):
    resolution_notes = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    def validate_resolution_notes(self, value):
        if value is not None and not isinstance(value, str):
            raise serializers.ValidationError("resolution_notes must be a string.")
        return value

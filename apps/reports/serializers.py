from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Report, ReportReason


class ReportSerializer(serializers.ModelSerializer):
    """Customer-facing report representation."""

    target_type = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "target_type",
            "target_id",
            "reason",
            "description",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_target_type(self, obj) -> str:
        return "PRODUCT" if obj.product_id else "VENDOR"

    @extend_schema_field(serializers.UUIDField())
    def get_target_id(self, obj) -> str:
        target_id = obj.product_id or obj.vendor_profile_id
        return str(target_id)


class ReportAdminSerializer(ReportSerializer):
    """Admin-facing report representation."""

    reporter_name = serializers.CharField(
        source="reporter.full_name",
        read_only=True,
    )
    resolved_by_name = serializers.CharField(
        source="resolved_by.full_name",
        read_only=True,
        default=None,
    )

    class Meta(ReportSerializer.Meta):
        fields = ReportSerializer.Meta.fields + [
            "reporter",
            "reporter_name",
            "resolved_by",
            "resolved_by_name",
            "resolved_at",
            "resolution_notes",
        ]
        read_only_fields = fields


class ReportCreateSerializer(serializers.ModelSerializer):
    """
    Input serializer for creating reports.

    The target is resolved from the URL and is deliberately not accepted
    from the request body.
    """

    class Meta:
        model = Report
        fields = [
            "reason",
            "description",
        ]

    def validate(self, attrs):
        if (
            attrs.get("reason") == ReportReason.OTHER
            and not (attrs.get("description") or "").strip()
        ):
            raise serializers.ValidationError(
                {"description": ("Description is required when reason is 'OTHER'.")}
            )

        return attrs


class ReportResolutionSerializer(serializers.Serializer):
    """Input serializer for Admin report resolution/rejection."""

    resolution_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def to_internal_value(self, data):
        if "resolution_notes" in data:
            value = data["resolution_notes"]

            if value is not None and not isinstance(value, str):
                raise serializers.ValidationError(
                    {"resolution_notes": ("Resolution notes must be a string.")}
                )

        return super().to_internal_value(data)

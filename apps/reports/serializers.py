from rest_framework import serializers

from .models import Report, ReportReason


class ReportSerializer(serializers.ModelSerializer):
    """Customer-facing shape — used for creation responses and the
    reporter's own /reports/mine/ + /reports/{id}/ views. Omits internal
    admin/resolution fields."""

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

    def get_target_type(self, obj):
        return "PRODUCT" if obj.product_id else "VENDOR"

    def get_target_id(self, obj):
        target_id = obj.product_id or obj.vendor_profile_id
        return str(target_id)


class ReportAdminSerializer(ReportSerializer):
    """Admin-facing shape — every admin endpoint, and /reports/{id}/ when
    the requester is staff/superuser. Adds resolution metadata."""

    reporter_name = serializers.CharField(source="reporter.full_name", read_only=True)
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
    The only input-accepting serializer. `product`/`vendor_profile` are
    never fields here — the target is resolved server-side from the URL
    path (product_id/vendor_id), never from client-supplied identifiers,
    per the task brief's explicit ownership-authorization instruction.
    """

    class Meta:
        model = Report
        fields = ["reason", "description"]

    def validate(self, attrs):
        # Serializer-level mirror of the service/DB rule (DDS §5,
        # ReportReason.OTHER note) — gives a friendly 400 field error
        # ahead of the CheckConstraint, matching DDS §7.2's stated pattern.
        if (
            attrs.get("reason") == ReportReason.OTHER
            and not (attrs.get("description") or "").strip()
        ):
            raise serializers.ValidationError(
                {"description": "Description is required when reason is 'OTHER'."}
            )
        return attrs


class ReportResolutionSerializer(serializers.Serializer):
    resolution_notes = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    def to_internal_value(self, data):
        if "resolution_notes" in data:
            value = data["resolution_notes"]
            if value is not None and not isinstance(value, str):
                raise serializers.ValidationError(
                    {"resolution_notes": "Resolution notes must be a string."}
                )
        return super().to_internal_value(data)

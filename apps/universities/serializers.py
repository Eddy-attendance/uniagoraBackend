from rest_framework import serializers

from .models import University


class UniversitySerializer(serializers.ModelSerializer):
    """Public/customer-facing representation."""

    class Meta:
        model = University
        fields = [
            "id",
            "name",
            "short_name",
            "slug",
            "logo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UniversityAdminWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ["name", "short_name", "logo"]

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers


def success_response_schema(
    name: str,
    data_serializer: serializers.Serializer,
):
    return inline_serializer(
        name=name,
        fields={
            "success": serializers.BooleanField(default=True),
            "message": serializers.CharField(default=""),
            "data": data_serializer,
        },
    )


def paginated_response_schema(
    name: str,
    item_serializer: serializers.Serializer,
):
    return inline_serializer(
        name=name,
        fields={
            "success": serializers.BooleanField(default=True),
            "message": serializers.CharField(default=""),
            "data": inline_serializer(
                name=f"{name}Data",
                fields={
                    "count": serializers.IntegerField(),
                    "total_pages": serializers.IntegerField(),
                    "current_page": serializers.IntegerField(),
                    "page_size": serializers.IntegerField(),
                    "next": serializers.URLField(allow_null=True),
                    "previous": serializers.URLField(allow_null=True),
                    "results": item_serializer(many=True),
                },
            ),
        },
    )


ErrorResponse = inline_serializer(
    name="ErrorResponse",
    fields={
        "success": serializers.BooleanField(default=False),
        "message": serializers.CharField(default=""),
        "errors": serializers.DictField(),
    },
)

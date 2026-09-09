from drf_spectacular.utils import inline_serializer
from rest_framework import serializers


def success_response_schema(
    name: str,
    data_serializer_class: type[serializers.Serializer],
) -> type[serializers.Serializer]:
    """
    Build the standard UniAGORA success response envelope.

    Runtime shape:
        {
            "success": true,
            "message": "",
            "data": {...}
        }
    """
    return inline_serializer(
        name=name,
        fields={
            "success": serializers.BooleanField(default=True),
            "message": serializers.CharField(default=""),
            "data": data_serializer_class(),
        },
    )


def list_response_schema(
    name: str,
    item_serializer_class: type[serializers.Serializer],
) -> type[serializers.Serializer]:
    """
    Build the standard UniAGORA success response envelope
    for a non-paginated list response.

    Runtime shape:
        {
            "success": true,
            "message": "",
            "data": [...]
        }

    Example:
        list_response_schema("ProductImageListResponse", ProductImageSerializer)
    """
    return inline_serializer(
        name=name,
        fields={
            "success": serializers.BooleanField(default=True),
            "message": serializers.CharField(default=""),
            "data": item_serializer_class(many=True),
        },
    )


def paginated_response_schema(
    name: str,
    item_serializer_class: type[serializers.Serializer],
) -> type[serializers.Serializer]:
    """
    Build the standard UniAGORA paginated success response envelope.

    Runtime shape:
        {
            "success": true,
            "message": "",
            "data": {
                "count": 0,
                "total_pages": 0,
                "current_page": 1,
                "page_size": 0,
                "next": null,
                "previous": null,
                "results": [...]
            }
        }
    """
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
                    "results": item_serializer_class(many=True),
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

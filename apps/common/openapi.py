from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import OpenApiResponse, inline_serializer
from rest_framework import serializers


class EnvelopeAutoSchema(AutoSchema):
    """
    Project-wide AutoSchema (wired via
    `REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"]`) that documents the shared
    failure envelope on every operation.

    The runtime guarantees (via `common.exceptions.custom_exception_handler`
    plus the `EnvelopeJSONRenderer` backstop) that every 4xx response has
    the exact `{success, message, errors}` shape. Documenting it once,
    here, via the `ErrorResponse` component keeps the schema aligned with
    the API-standards requirement (Backend Responsibility doc §8: every
    endpoint documents its error responses) without an `ErrorResponse`
    annotation per view.
    """

    def _get_response_bodies(self, direction="response"):
        responses = super()._get_response_bodies(direction)
        if direction == "response" and "4XX" not in responses:
            responses["4XX"] = self._get_response_for_code(
                OpenApiResponse(
                    response=ErrorResponse,
                    description=(
                        "Failure envelope for all 4xx responses (validation, "
                        "authentication, authorization, business-rule conflicts)."
                    ),
                ),
                "4XX",
                direction=direction,
            )
        return responses


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


class EmptyDataSerializer(serializers.Serializer):
    """Empty `data` payload for message-only success responses."""


EmptyResponseData = EmptyDataSerializer()


ErrorResponse = inline_serializer(
    name="ErrorResponse",
    fields={
        "success": serializers.BooleanField(default=False),
        "message": serializers.CharField(default=""),
        "errors": serializers.DictField(),
    },
)

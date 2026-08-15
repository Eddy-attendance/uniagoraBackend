"""
Response envelope helpers implementing the PRD's mandated API contract.

API Principles:
    Success: {"success": true, "message": "", "data": {}}
    Failure: {"success": false, "message": "", "errors": {}}

Every view across every app builds its responses through these two
functions (or receives the same shape automatically via
`exceptions.custom_exception_handler` / `renderers.EnvelopeJSONRenderer`
on the failure/fallback paths) so the contract never depends on each view
remembering the exact shape.
"""

from typing import Any

from rest_framework import status as http_status
from rest_framework.response import Response


def success_response(
    data: Any = None,
    message: str = "",
    status: int = http_status.HTTP_200_OK,
) -> Response:
    """Builds a success envelope"""
    return Response(
        {
            "success": True,
            "message": message,
            "data": data if data is not None else {},
        },
        status=status,
    )


def error_response(
    message: str = "",
    errors: dict | None = None,
    status: int = http_status.HTTP_400_BAD_REQUEST,
) -> Response:
    """Builds a failure envelope"""
    return Response(
        {
            "success": False,
            "message": message,
            "errors": errors if errors is not None else {},
        },
        status=status,
    )

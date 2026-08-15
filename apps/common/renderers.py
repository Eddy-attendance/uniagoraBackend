"""
Global renderer enforcing the response envelope as a backstop.
"""

from typing import Any

from rest_framework.renderers import JSONRenderer


class EnvelopeJSONRenderer(JSONRenderer):
    def render(
        self,
        data: Any,
        accepted_media_type: str | None = None,
        renderer_context: dict | None = None,
    ) -> bytes:
        if isinstance(data, dict) and "success" in data:
            payload = data
        else:
            response = (renderer_context or {}).get("response")
            status_code = getattr(response, "status_code", 200)
            is_success = status_code < 400

            if is_success:
                payload = {
                    "success": True,
                    "message": "",
                    "data": data if data is not None else {},
                }
            else:
                payload = {
                    "success": False,
                    "message": "",
                    "errors": data if data is not None else {},
                }

        return super().render(payload, accepted_media_type, renderer_context)

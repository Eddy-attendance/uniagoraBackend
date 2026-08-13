"""
apps/chat/routing.py — Channels websocket_urlpatterns for this app.
Included from the project's root ASGI application (see Required
Integration Changes: config/asgi.py).
"""

from django.urls import re_path

from apps.chat import consumers

websocket_urlpatterns = [
    re_path(
        r"^ws/chat/(?P<conversation_id>[0-9a-fA-F-]{36})/$",
        consumers.ChatConsumer.as_asgi(),
    ),
]

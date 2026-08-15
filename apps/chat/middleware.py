from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _get_user_from_token(token):
    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.tokens import AccessToken

    from apps.users.models import User

    if not token:
        return AnonymousUser()
    try:
        validated = AccessToken(token)
        user_id = validated["user_id"]
        return User.objects.alive().get(id=user_id, is_active=True)
    except (TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware:
    """Populates `scope["user"]` from a `?token=` query parameter."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]
        scope["user"] = await _get_user_from_token(token)
        return await self.app(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)

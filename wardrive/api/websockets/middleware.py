"""ASGI middleware: JWT from query string (?token=) for WebSocket scope."""

from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


@sync_to_async(thread_sensitive=False)
def _user_from_token(token_key: str):
    try:
        access = AccessToken(token_key)
        uid = access["user_id"]
        return User.objects.get(pk=uid)
    except (InvalidToken, TokenError, User.DoesNotExist, KeyError, TypeError):
        return AnonymousUser()


class JWTAuthMiddleware:
    """Populate scope[\"user\"] from ?token= (same access JWT as Authorization: Bearer)."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] != "websocket":
            return await self.inner(scope, receive, send)
        query_string = scope.get("query_string", b"") or b""
        query = parse_qs(query_string.decode())
        token = (query.get("token") or [None])[0]
        if token:
            scope = dict(scope)
            scope["user"] = await _user_from_token(token)
        else:
            scope = dict(scope)
            scope["user"] = AnonymousUser()
        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)

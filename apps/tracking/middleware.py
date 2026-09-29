"""
Django Channels has no built-in support for DRF's JWT auth, so we implement
a small middleware that reads the access token from the WebSocket
connection's query string (?token=...) and attaches the resolved user to
the connection scope, the same way AuthMiddlewareStack attaches a
session-based user for regular HTTP requests.

Usage: connect to  ws://host/ws/orders/<order_id>/?token=<access_token>
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError


@database_sync_to_async
def get_user_from_token(token_str):
    from apps.accounts.models import User
    try:
        access_token = AccessToken(token_str)
        user = User.objects.get(id=access_token['user_id'])
        return user
    except (TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware:
    """Custom middleware that authenticates WebSocket connections via a
    Simple JWT access token passed as a query parameter."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = parse_qs(scope.get('query_string', b'').decode())
        token = query_string.get('token', [None])[0]

        scope['user'] = await get_user_from_token(token) if token else AnonymousUser()
        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Named to mirror Channels' AuthMiddlewareStack convention. Kept as a
    thin wrapper (rather than composing with AuthMiddlewareStack) because
    stacking session-based auth on top would let a stale/absent session
    silently override our JWT-resolved user with AnonymousUser."""
    return JWTAuthMiddleware(inner)

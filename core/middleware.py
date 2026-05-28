from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


@sync_to_async
def get_user_for_token(token):
    jwt_authentication = JWTAuthentication()

    try:
        validated_token = jwt_authentication.get_validated_token(token)
        return jwt_authentication.get_user(validated_token)
    except (InvalidToken, TokenError):
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_params = parse_qs(scope.get("query_string", b"").decode())
        token = (query_params.get("token") or [None])[0]
        scope["user"] = (
            await get_user_for_token(token)
            if token
            else AnonymousUser()
        )

        return await super().__call__(scope, receive, send)

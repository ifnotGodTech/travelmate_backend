from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.http import HttpRequest
import logging
import traceback

logger = logging.getLogger(__name__)

class JWTMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Import here to avoid apps not loaded error
        from django.contrib.auth.models import AnonymousUser

        logger.debug(f"JWT Middleware processing: {scope.get('path')}")

        # Extract token from query string
        query_string = scope.get("query_string", b"").decode()
        token = None
        for param in query_string.split("&"):
            if param.startswith("token="):
                token = param.split("=")[1]
                break

        if token:
            try:
                scope["user"] = await self.get_user(token, scope)
                logger.debug(f"JWT authentication: Token={token[:10]}..., User={scope['user']}, Path={scope.get('path')}")
            except Exception as e:
                logger.error(f"JWT middleware error: {str(e)}")
                logger.error(traceback.format_exc())
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()
            logger.warning(f"JWT authentication: No token provided for path {scope.get('path')}")

        try:
            return await super().__call__(scope, receive, send)
        except Exception as e:
            logger.error(f"Error in JWT middleware call: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    @database_sync_to_async
    def get_user(self, token, scope):
        from django.contrib.auth.models import AnonymousUser
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
        from core.helpers.authentication import CustomJWTAuthentication

        logger.debug(f"Authenticating token: {token[:10]}...")

        # Create a dummy request object
        dummy_request = HttpRequest()

        # Get headers from scope
        headers = dict(scope.get('headers', []))
        host = headers.get(b'host', b'').decode('utf-8').split(':')[0] or 'localhost'

        # Get scheme (ws:// or wss://)
        scheme = 'https' if scope.get('scheme') == 'wss' else 'http'

        dummy_request.META = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "SERVER_NAME": host,
            "SERVER_PORT": headers.get(b'port', b'443' if scheme == 'https' else b'80').decode('utf-8'),
            "HTTP_HOST": host,
            "REMOTE_ADDR": scope.get('client', ['0.0.0.0'])[0],
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.url_scheme": scheme,
        }

        jwt_auth = CustomJWTAuthentication()
        try:
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token, request=dummy_request)
            logger.debug(f"Authentication successful - User: {user.username if hasattr(user, 'username') else 'AnonymousUser'}")
            return user
        except (InvalidToken, TokenError) as e:
            logger.error(f"JWT authentication: Invalid token - {str(e)}")
            return AnonymousUser()

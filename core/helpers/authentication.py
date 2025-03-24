import logging
from django.utils.translation import gettext_lazy as _
from rest_framework import HTTP_HEADER_ENCODING
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings

logger = logging.getLogger(__name__)

AUTH_HEADER_TYPES = api_settings.AUTH_HEADER_TYPES

if not isinstance(api_settings.AUTH_HEADER_TYPES, (list, tuple)):
    AUTH_HEADER_TYPES = (AUTH_HEADER_TYPES,)

AUTH_HEADER_TYPE_BYTES = {h.encode(HTTP_HEADER_ENCODING) for h in AUTH_HEADER_TYPES}


class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request: Request):
        logger.debug("Attempting to authenticate with CustomJWTAuthentication")
        header = self.get_header(request)
        if header is None:
            logger.debug("No Authorization header found")
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            logger.debug("No raw token found in header")
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            logger.debug(f"Token validated successfully: {validated_token}")
        except InvalidToken as e:
            logger.error(f"Token validation failed: {e}")
            raise

        user = self.get_user(validated_token, request)
        logger.debug(f"User authenticated successfully: {user}")
        return user, validated_token

    def get_validated_token(self, raw_token):
        """
        Validates an encoded JSON web token and returns a validated token
        wrapper object.
        """
        messages = []
        for AuthToken in api_settings.AUTH_TOKEN_CLASSES:
            try:
                return AuthToken(raw_token)
            except TokenError as e:
                messages.append(
                    {
                        "token_class": AuthToken.__name__,
                        "token_type": AuthToken.token_type,
                        "message": e.args[0],
                    },
                )

        raise InvalidToken(
            {
                "detail": _("Your session has expired. Please log in again to continue"),
                "messages": messages,
            },
        )

    def get_user(self, validated_token, request: Request):
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
            logger.debug(f"Extracted user ID from token: {user_id}")
        except KeyError:
            logger.error("Token contained no recognizable user identification")
            raise InvalidToken(_("Token contained no recognizable user identification"))

        try:
            user = self.user_model.objects.get(**{api_settings.USER_ID_FIELD: user_id})
            logger.debug(f"User found: {user}")
        except self.user_model.DoesNotExist:
            logger.error("User not found")
            raise AuthenticationFailed(_("User not found"), code="user_not_found")

        if not user.is_active:
            logger.error("User is inactive")
            raise AuthenticationFailed(_("User is inactive"), code="user_inactive")

        return user

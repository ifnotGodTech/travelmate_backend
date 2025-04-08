# ruff: noqa
from smtplib import SMTPRecipientsRefused
from core.applications.users.email import OTPRegistrationEmail
import pyotp
from django.core.cache import cache
from rest_framework import viewsets, permissions, status
from rest_framework.filters import OrderingFilter
from rest_framework.filters import SearchFilter
from drf_spectacular.utils import extend_schema_view

from django.contrib.auth import logout
import csv
from django.http import HttpResponse
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import user_logged_out
from django.utils.module_loading import import_string
from django.utils.timezone import now
from djoser import signals
from djoser import utils
from djoser.compat import get_user_email
from djoser.conf import settings
from djoser.email import ActivationEmail
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser
from rest_framework.parsers import JSONParser
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import AUTH_HEADER_TYPES
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.viewsets import ViewSet

from core.applications.users.models import AccountDeletionReason, Profile, User
from core.applications.users.token import default_token_generator
from core.helpers.custom_exceptions import CustomError
from core.applications.users.api.serializers import AdminRegistrationSerializer, AdminUserDetailSerializer, AdminUserSerializer, CustomUserCreateSerializer, EmailSubmissionSerializer, OTPVerificationSerializer, PasswordRetypeSerializer, PasswordSetSerializer, ProfileSerializers, UserDeleteSerializer, UserSerializer, VerifyOTPSerializer
from core.helpers.authentication import CustomJWTAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
import logging
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from django_filters.rest_framework import DjangoFilterBackend
from core.applications.users.api.schemas import(
    submit_email_schema, verify_otp_schema, verify_admin_schema,
    resend_otp_schema, admin_list_user_schema, admin_deactivate_user_schema,
    admin_export_user_schema, set_password_schema, login_validate_email_schema,
    login_validate_password_schema
)
from django.conf import settings as django_settings
from django.db.models import Count
from rest_framework.views import APIView
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
    OpenApiExample,
)

logger = logging.getLogger(__name__)

class AuthView(ModelViewSet):
    model = ActivationEmail


class TokenViewBase(generics.GenericAPIView):
    permission_classes = ()
    authentication_classes = ()
    parser_classes = [MultiPartParser, JSONParser]

    serializer_class = None
    _serializer_class = ""

    www_authenticate_realm = "api"

    def get_serializer_class(self):
        """
        If serializer_class is set, use it directly. Otherwise get the class from settings.
        """

        if self.serializer_class:
            return self.serializer_class
        try:
            return import_string(self._serializer_class)
        except ImportError:
            msg = "Could not import serializer '%s'" % self._serializer_class
            raise ImportError(msg)

    def get_authenticate_header(self, request):
        return f'{AUTH_HEADER_TYPES[0]} realm="{self.www_authenticate_realm}"'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


# class TokenObtainPairView(TokenViewBase):
#     """
#     Takes a set of user credentials and returns an access and refresh JSON web
#     token pair to prove the authentication of those credentials.
#     """

#     _serializer_class = api_settings.TOKEN_OBTAIN_SERIALIZER


# token_obtain_pair = TokenObtainPairView.as_view()

class ValidateEmailView(APIView):
    permission_classes = [AllowAny]


    @login_validate_email_schema
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"detail": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "Email exists."},
                status=status.HTTP_200_OK
            )

        return Response(
            {"detail": "Email not found."},
            status=status.HTTP_400_BAD_REQUEST
        )


class ValidatePasswordView(APIView):
    """
    Validates the email and password, and returns access/refresh tokens using
    the same serializer used by TokenObtainPairView.
    """
    permission_classes = [AllowAny]
    def get_serializer_class(self):
        """
        Resolves the TOKEN_OBTAIN_SERIALIZER setting,
        whether it's a class or a string path.
        """
        serializer = api_settings.TOKEN_OBTAIN_SERIALIZER
        if isinstance(serializer, str):
            return import_string(serializer)
        return serializer

    @login_validate_password_schema
    def post(self, request, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data, context={'request': request}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response(
                {
                    "detail": "The password you entered doesn't match our records. "
                              "Try again or click on 'Forgot password'."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)



class TokenObtainSlidingView(TokenViewBase):
    """
    Takes a set of user credentials and returns a sliding JSON web token to
    prove the authentication of those credentials.
    """

    _serializer_class = api_settings.SLIDING_TOKEN_OBTAIN_SERIALIZER


token_obtain_sliding = TokenObtainSlidingView.as_view()


class TokenRefreshSlidingView(TokenViewBase):
    """
    Takes a sliding JSON web token and returns a new, refreshed version if the
    token's refresh period has not expired.
    """

    _serializer_class = api_settings.SLIDING_TOKEN_REFRESH_SERIALIZER


token_refresh_sliding = TokenRefreshSlidingView.as_view()


class TokenRefreshView(TokenViewBase):
    """
    Takes a refresh type JSON web token and returns an access type JSON web
    token if the refresh token is valid.
    """

    _serializer_class = api_settings.TOKEN_REFRESH_SERIALIZER


token_refresh = TokenRefreshView.as_view()


class TokenVerifyView(TokenViewBase):
    """
    Takes a token and indicates if it is valid.  This view provides no
    information about a token's fitness for a particular use.
    """

    _serializer_class = api_settings.TOKEN_VERIFY_SERIALIZER


token_verify = TokenVerifyView.as_view()


class TokenBlacklistView(TokenViewBase):
    """
    Takes a token and blacklists it. Must be used with the
    `rest_framework_simplejwt.token_blacklist` app installed.
    """

    _serializer_class = api_settings.TOKEN_BLACKLIST_SERIALIZER


token_blacklist = TokenBlacklistView.as_view()


class BaseOTPRegistrationViewSet(ViewSet):
    permission_classes = [AllowAny]
    OTP_EXPIRY = 600  # 10 minutes
    OTP_DIGITS = 4
    OTP_SECRET = "JBSWY3DPEHPK3PXP"
    is_admin = False  # to be overridden by AdminRegistrationViewSet

    def generate_otp(self, email):
        otp = pyotp.TOTP(self.OTP_SECRET, digits=self.OTP_DIGITS).now()
        cache.set(email, otp, timeout=self.OTP_EXPIRY)
        return otp

    def send_otp_email(self, request, email, otp):
        OTPRegistrationEmail(request, {"otp": otp}).send([email])
        logger.info(f"OTP email sent to {email}")

    def validate_otp(self, email, otp):
        cached_otp = cache.get(email)
        if cached_otp and cached_otp == otp:
            cache.set(f"{email}_verified", True, timeout=self.OTP_EXPIRY)
            cache.delete(email)
            return True
        return False

    def generate_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}

    @submit_email_schema
    @action(detail=False, methods=["post"])
    def submit_email(self, request):
        serializer = EmailSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]

            if User.objects.filter(email=email).exists():
                return Response(
                    {"message": "A user with this email is already registered."},
                    status=status.HTTP_307_TEMPORARY_REDIRECT
                )

            otp = self.generate_otp(email)
            self.send_otp_email(request, email, otp)
            return Response({"message": "OTP sent to your email."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @verify_otp_schema
    @action(detail=False, methods=["post"])
    def verify_otp(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            otp = serializer.validated_data["otp"]

            if self.validate_otp(email, otp):
                return Response({"message": "OTP verified. Proceed to set your password."}, status=status.HTTP_200_OK)

            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @resend_otp_schema
    @action(detail=False, methods=["post"])
    def resend_otp(self, request):
        serializer = EmailSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]

            if not User.objects.filter(email=email).exists():
                return Response(
                    {"error": "User not found with this email."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            otp = self.generate_otp(email)
            self.send_otp_email(request, email, otp)
            return Response({"message": "A new OTP has been sent to your email."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @set_password_schema
    @action(detail=False, methods=["post"])
    def set_password(self, request):
        serializer = PasswordSetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]

            if not cache.get(f"{email}_verified"):
                return Response({"error": "OTP not verified or expired."}, status=status.HTTP_400_BAD_REQUEST)

            user, created = User.objects.get_or_create(email=email)
            user.set_password(serializer.validated_data["password"])

            if self.is_admin:
                user.is_staff = True
                user.is_admin = True
                user.is_superuser = True

            user.save()
            cache.delete(f"{email}_verified")

            tokens = self.generate_tokens(user)
            return Response(
                {
                    "message": "Admin account created successfully." if self.is_admin else "Password set successfully.",
                    "tokens": tokens,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@extend_schema(tags=["User Register with OTP"])
class UserRegistrationViewSet(BaseOTPRegistrationViewSet):
    """Handles OTP-based user registration."""
    is_admin = False


@extend_schema(tags=["Admin Register with OTP"])
class AdminRegistrationViewSet(BaseOTPRegistrationViewSet):
    """Handles OTP-based admin registration."""
    is_admin = True


@extend_schema(tags=["User"])
@extend_schema_view(
    me=extend_schema(
        methods=["GET"],
        summary="Use this when user wants to Get his account",
        description="Retrieve the profile of the currently authenticated user.",
        responses={
            200: OpenApiResponse(description="User profile retrieved successfully."),
            401: OpenApiResponse(description="Authentication credentials were not provided or are invalid."),
        },
    ),
    me__put=extend_schema(
        methods=["PUT"],
        summary="Use this when user wants to Update his account",
        description="Fully update the current user's profile.",
        request=settings.SERIALIZERS.user,
        responses={
            200: OpenApiResponse(description="User profile updated successfully."),
            400: OpenApiResponse(description="Invalid data."),
            401: OpenApiResponse(description="Authentication required."),
        },
    ),
    me__patch=extend_schema(
        methods=["PATCH"],
        summary="Use this when user wants to Partially Update his account",
        description="Partially update the current user's profile.",
        request=settings.SERIALIZERS.user,
        responses={
            200: OpenApiResponse(description="User profile partially updated successfully."),
            400: OpenApiResponse(description="Invalid data."),
            401: OpenApiResponse(description="Authentication required."),
        },
    ),
    delete=extend_schema(
        methods=["DELETE"],
        summary="Use this when user wants to Delete his account",
        description=(
            "Delete the currently authenticated user's account.\n\n"
            "**Required fields:**\n"
            "- `reason` – one of the following options:\n"
            "  - `Found another app`\n"
            "  - `Too many notifications`\n"
            "  - `Overloaded with content`\n"
            "  - `Security concern`\n"
            "  - `Others`\n\n"
            "- If `reason` is set to `Others`, the `additional_feedback` field **must** be provided.\n"
            "- `additional_feedback` is optional for other reasons.\n\n"
            "Upon successful request:\n"
            "- The account will be deleted.\n"
            "- The user will be logged out.\n"
            "- The deletion reason will be recorded for internal analytics."
        ),
        request=settings.SERIALIZERS.user_delete,
        responses={
            204: OpenApiResponse(description="Account successfully deleted."),
            400: OpenApiResponse(description="Missing or invalid deletion reason or feedback."),
            401: OpenApiResponse(description="Authentication required."),
        },
        examples=[
            OpenApiExample(
                name="Account Deletion with Standard Reason",
                value={
                    "reason": "Too many notifications"
                },
                request_only=True,
            ),
            OpenApiExample(
                name="Account Deletion with 'Others' Reason",
                value={
                    "reason": "Others",
                    "additional_feedback": "I prefer to stay offline for a while."
                },
                request_only=True,
            ),
        ]
    )
)
class UserViewSet(ModelViewSet):
    serializer_class = settings.SERIALIZERS.user
    queryset = User.objects.all()
    permission_classes = settings.PERMISSIONS.user
    token_generator = default_token_generator
    lookup_field = settings.USER_ID_FIELD
    parser_classes = [MultiPartParser, JSONParser, FormParser]

    def permission_denied(self, request, *args, **kwargs):
        if (
            settings.HIDE_USERS
            and request.user.is_authenticated
            and self.action in ["update", "partial_update", "list", "retrieve"]
        ):
            raise NotFound()
        super().permission_denied(request, **kwargs)

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if settings.HIDE_USERS and self.action == "list" and not user.is_staff:
            queryset = queryset.filter(pk=user.pk)
        return queryset

    def get_permissions(self):
        """
        Defines the permission classes for the
        UserViewSet based on the current action.

        The permission classes are set according to the
        following actions:
            - create: settings.PERMISSIONS.user_create
            - activation: settings.PERMISSIONS.activation
            - resend_activation: settings.PERMISSIONS.password_reset
            - list: settings.PERMISSIONS.user_list
            - reset_password: settings.PERMISSIONS.password_reset
            - reset_password_confirm: settings.PERMISSIONS.password_reset_confirm
            - set_password: settings.PERMISSIONS.set_password
            - set_username: settings.PERMISSIONS.set_username
            - reset_username: settings.PERMISSIONS.username_reset
            - reset_username_confirm: settings.PERMISSIONS.username_reset_confirm
            - destroy or me with DELETE method: settings.PERMISSIONS.user_delete

        Returns the permission classes based on the current action.
        """
        if self.action == "create":
            self.permission_classes = settings.PERMISSIONS.user_create
        elif self.action == "activation":
            self.permission_classes = settings.PERMISSIONS.activation
        elif self.action == "resend_activation":
            self.permission_classes = settings.PERMISSIONS.password_reset
        elif self.action == "list":
            self.permission_classes = settings.PERMISSIONS.user_list
        elif self.action == "reset_password":
            self.permission_classes = settings.PERMISSIONS.password_reset
        elif self.action == "reset_password_confirm":
            self.permission_classes = settings.PERMISSIONS.password_reset_confirm
        elif self.action == "set_password":
            self.permission_classes = settings.PERMISSIONS.set_password
        elif self.action == "set_username":
            self.permission_classes = settings.PERMISSIONS.set_username
        elif self.action == "reset_username":
            self.permission_classes = settings.PERMISSIONS.username_reset
        elif self.action == "reset_username_confirm":
            self.permission_classes = settings.PERMISSIONS.username_reset_confirm
        elif self.action == "destroy" or (
            self.action == "me" and self.request and self.request.method == "DELETE"
        ):
            self.permission_classes = settings.PERMISSIONS.user_delete
        return super().get_permissions()

    def get_serializer_class(self):
        """
        Returns the serializer class to use in the view.

        This method returns different serializer classes based
        on the current action.
        The serializer classes are set according to the following actions:
            - create: settings.SERIALIZERS.user_create or
            settings.SERIALIZERS.user_create_password_retype
            - destroy: settings.SERIALIZERS.user_delete
            - activation: settings.SERIALIZERS.activation
            - resend_activation: settings.SERIALIZERS.password_reset
            - reset_password: settings.SERIALIZERS.password_reset
            - reset_password_confirm: settings.SERIALIZERS.password_reset_confirm
            or settings.SERIALIZERS.password_reset_confirm_retype
            - set_password: settings.SERIALIZERS.set_password or
            settings.SERIALIZERS.set_password_retype
            - set_username: settings.SERIALIZERS.set_username or
            settings.SERIALIZERS.set_username_retype
            - reset_username: settings.SERIALIZERS.username_reset
            - reset_username_confirm:
            settings.SERIALIZERS.username_reset_confirm or
            settings.SERIALIZERS.username_reset_confirm_retype
            - me: settings.SERIALIZERS.current_user

        Returns:
            The serializer class to use in the view.
        """
        if self.action == "create":
            if settings.USER_CREATE_PASSWORD_RETYPE:
                return settings.SERIALIZERS.user_create_password_retype
            return settings.SERIALIZERS.user_create
        if self.action == "destroy" or (
            self.action == "me" and self.request and self.request.method == "DELETE"
        ):
            return settings.SERIALIZERS.user_delete
        if self.action == "activation":
            return settings.SERIALIZERS.activation
        if self.action == "resend_activation" or self.action == "reset_password":
            return settings.SERIALIZERS.password_reset
        if self.action == "reset_password_confirm":
            if settings.PASSWORD_RESET_CONFIRM_RETYPE:
                return settings.SERIALIZERS.password_reset_confirm_retype
            return settings.SERIALIZERS.password_reset_confirm
        if self.action == "set_password":
            if settings.SET_PASSWORD_RETYPE:
                return settings.SERIALIZERS.set_password_retype
            return settings.SERIALIZERS.set_password
        if self.action == "set_username":
            if settings.SET_USERNAME_RETYPE:
                return settings.SERIALIZERS.set_username_retype
            return settings.SERIALIZERS.set_username
        if self.action == "reset_username":
            return settings.SERIALIZERS.username_reset
        if self.action == "reset_username_confirm":
            if settings.USERNAME_RESET_CONFIRM_RETYPE:
                return settings.SERIALIZERS.username_reset_confirm_retype
            return settings.SERIALIZERS.username_reset_confirm
        if self.action == "me":
            return settings.SERIALIZERS.current_user

        return self.serializer_class

    def get_instance(self):
        return self.request.user

    def perform_create(self, serializer, *args, **kwargs):
        """
        Handles the creation of a new user instance.

        Saves the user instance using the provided serializer
        and triggers the user_registered signal.

        Parameters:
            serializer (Serializer): The serializer instance
            used to create the user.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            None
        """
        user = serializer.save(*args, **kwargs)
        # Facility.objects.create(user=user, type=account_serializer.validated_data.get("account_type"))
        signals.user_registered.send(
            sender=self.__class__,
            user=user,
            request=self.request,
        )

        context = {"user": user}
        to = [get_user_email(user)]
        print("Sending email...")
        try:
            if settings.SEND_ACTIVATION_EMAIL:
                settings.EMAIL.activation(self.request, context).send(to)
            elif settings.SEND_CONFIRMATION_EMAIL:
                settings.EMAIL.confirmation(self.request, context).send(to)
            print("Email sent!")
        except SMTPRecipientsRefused:
            raise CustomError.BadRequest(
                """
                Sorry, the email you entered appears to be incorrect or invalid.
                Please double-check your email address and try again
                """,
            )

    def perform_update(self, serializer, *args, **kwargs):
        """
        Handles the update of an existing user instance.

        Saves the user instance using the provided serializer
        and triggers the user_updated signal.

        Parameters:
            serializer (Serializer): The serializer instance
            used to update the user.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            None
        """
        super().perform_update(serializer, *args, **kwargs)
        user = serializer.instance
        signals.user_updated.send(
            sender=self.__class__,
            user=user,
            request=self.request,
        )

        # should we send activation email after update?
        if settings.SEND_ACTIVATION_EMAIL and not user.is_active:
            context = {"user": user}
            to = [get_user_email(user)]
            settings.EMAIL.activation(self.request, context).send(to)

    def destroy(self, request, *args, **kwargs):
        """
        Handles the deletion of an existing user instance.

        Parameters:
            request: The request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            A response with a status code of 204 (No Content)
            indicating the deletion was successful.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        if instance == request.user:
            utils.logout_user(self.request)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["get", "put", "patch", "delete"], detail=False)
    def me(self, request, *args, **kwargs):
        """
        Handle authenticated user profile operations:
        - GET: Retrieve profile
        - PUT: Fully update profile
        - PATCH: Partially update profile
        - DELETE: Delete account (requires reason)
        """
        self.get_object = self.get_instance

        if request.method == "GET":
            return self.retrieve(request, *args, **kwargs)

        if request.method == "PUT":
            return self.update(request, *args, **kwargs)

        if request.method == "PATCH":
            return self.partial_update(request, *args, **kwargs)

        if request.method == "DELETE":
            instance = self.get_object()

            serializer = UserDeleteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            AccountDeletionReason.objects.create(
                user=instance,
                reason=serializer.validated_data["reason"],
                additional_feedback=serializer.validated_data.get("additional_feedback", "")
            )

            utils.logout_user(request)
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)


        def retrieve(self, request, *args, **kwargs):
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)

        @action(["post"], detail=False)
        def activation(self, request, *args, **kwargs):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.user
            user.is_active = True
            user.save()

            signals.user_activated.send(
                sender=self.__class__,
                user=user,
                request=self.request,
            )

            if settings.SEND_CONFIRMATION_EMAIL:
                context = {"user": user}
                to = [get_user_email(user)]
                settings.EMAIL.confirmation(self.request, context).send(to)

            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["post"], detail=False)
    def resend_activation(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.get_user(is_active=False)

        if not settings.SEND_ACTIVATION_EMAIL or not user:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        context = {"user": user}
        to = [get_user_email(user)]
        settings.EMAIL.activation(self.request, context).send(to)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["post"], detail=False)
    def set_password(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.request.user.set_password(serializer.data["new_password"])
        self.request.user.save()

        if settings.PASSWORD_CHANGED_EMAIL_CONFIRMATION:
            context = {"user": self.request.user}
            to = [get_user_email(self.request.user)]
            settings.EMAIL.password_changed_confirmation(self.request, context).send(to)

        if settings.LOGOUT_ON_PASSWORD_CHANGE:
            utils.logout_user(self.request)
        elif settings.CREATE_SESSION_ON_LOGIN:
            update_session_auth_hash(self.request, self.request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["post"], detail=False)
    def reset_password(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.get_user()

        if user:
            context = {"user": user}
            to = [get_user_email(user)]
            settings.EMAIL.password_reset(self.request, context).send(to)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["post"], detail=False)
    def reset_password_confirm(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.user.set_password(serializer.data["new_password"])
        if hasattr(serializer.user, "last_login"):
            serializer.user.last_login = now()
        serializer.user.save()

        if settings.PASSWORD_CHANGED_EMAIL_CONFIRMATION:
            context = {"user": serializer.user}
            to = [get_user_email(serializer.user)]
            settings.EMAIL.password_changed_confirmation(self.request, context).send(to)
            print("password reseted")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["post"], detail=False, url_path=f"set_{User.USERNAME_FIELD}")
    def set_username(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.request.user
        new_username = serializer.data["new_" + User.USERNAME_FIELD]

        setattr(user, User.USERNAME_FIELD, new_username)
        user.save()
        if settings.USERNAME_CHANGED_EMAIL_CONFIRMATION:
            context = {"user": user}
            to = [get_user_email(user)]
            settings.EMAIL.username_changed_confirmation(self.request, context).send(to)

    @action(["post"], detail=False, url_path=f"reset_{User.USERNAME_FIELD}")
    def reset_username(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.get_user()

        if user:
            context = {"user": user}
            to = [get_user_email(user)]
            settings.EMAIL.username_reset(self.request, context).send(to)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["post"], detail=False, url_path=f"reset_{User.USERNAME_FIELD}_confirm")
    def reset_username_confirm(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_username = serializer.data["new_" + User.USERNAME_FIELD]

        setattr(serializer.user, User.USERNAME_FIELD, new_username)
        if hasattr(serializer.user, "last_login"):
            serializer.user.last_login = now()
        serializer.user.save()

        if settings.USERNAME_CHANGED_EMAIL_CONFIRMATION:
            context = {"user": serializer.user}
            to = [get_user_email(serializer.user)]
            settings.EMAIL.username_changed_confirmation(self.request, context).send(to)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(tags=["auth", "User Management"])
    @action(["post"], detail=False, authentication_classes=[JWTAuthentication])
    def logout(self, request, *args, **kwargs):
        if settings.TOKEN_MODEL:
            settings.TOKEN_MODEL.objects.filter(user=request.user).delete()
            user_logged_out.send(
                sender=request.user.__class__,
                request=request,
                user=request.user,
            )
        if settings.CREATE_SESSION_ON_LOGIN:
            logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=["auth", "User Management"],
        # request=UserSerializer.PhoneMetadata,  # noqa: ERA001
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    @action(["POST"], detail=False, authentication_classes=[JWTAuthentication])
    def metadatas(self, request: Request, *args, **kwargs):
        serializer = UserSerializer.PhoneMetadata(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user, serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileViewSet(ModelViewSet):
    query_set = Profile.objects.all()
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    profile_serializer_class = ProfileSerializers
    serializer_class = profile_serializer_class.BaseProfileSerializer

    def get_serializer_class(self):
        """
        Return the appropriate serializer class depending on the action.
        """
        if self.action in ["update", "partial_update"]:
            return ProfileSerializers.BaseProfileSerializer
        return ProfileSerializers.BaseProfileSerializer

    def get_serializer(self, *args, **kwargs):
        if self.action in ["update", "retrieve", "partial_update"]:
            return ProfileSerializers.BaseProfileSerializer(*args, **kwargs)
        return ProfileSerializers.BaseProfileSerializer(*args, **kwargs)

    def get_queryset(self):
        """Ensure users can only access their own profile"""
        return Profile.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve the instance of a particular profile
        :param request: The request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: The retrieved profile or an error message if the profile does not exist.
        """

        instance = self.get_object()
        response_serializer = self.serializer_class(instance)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """
        Update an existing profile for the current user.

        :param request: The request object containing updated profile data.
        :return: A response with the updated profile data.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.profile_serializer_class.BaseProfileSerializer(
            instance,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    def partial_update(self, request, *args, **kwargs):
        """
        Update an existing profile for the current user.

        :param request: The request object containing updated profile data.
        :return: A response with the updated profile data.
        """
        partial = kwargs.pop("partial", True)
        instance = self.get_object()
        serializer = self.profile_serializer_class.BaseProfileSerializer(
            instance,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class FacebookLoginView(SocialLoginView):
    """
    Facebook OAuth Login View

    This endpoint allows users to authenticate using a Facebook OAuth access token.
    Users must first obtain an access token from Facebook by signing in via Facebook OAuth.
    Once they receive a valid access token, they can send it to this API to authenticate.

    If the token is valid, the API will return a Django authentication token, which can be
    used for subsequent authenticated requests.
    """

    adapter_class = FacebookOAuth2Adapter

    @extend_schema(
        summary="Facebook OAuth Login",
        description="""
        Authenticate users using Facebook OAuth.

        **How it Works:**
        1. The user selects "Sign in with Facebook" in the frontend application.
        2. Facebook provides an access token upon successful authentication.
        3. The frontend sends this access token to this endpoint.
        4. The API verifies the token with Facebook and, if valid:
            - Creates a user account (if they are new).
            - Returns a Django authentication token for further API requests.

        **Request Format:**
        Send a `POST` request with a valid `access_token` obtained from Facebook.

        **Example Request:**
        ```json
        {
            "access_token": "EAAJZ..."
        }
        ```

        **Response Format:**
        If authentication is successful, the API returns an authentication token.

        **Example Response:**
        ```json
        {
            "key": "7f4e265c8f8c5e64db..."
        }
        ```
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "description": "Facebook OAuth access token obtained after successful login with Facebook."
                    }
                },
                "required": ["access_token"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Django authentication token to be used in future requests."
                    }
                }
            },
            400: {
                "description": "Invalid access token or authentication failed."
            }
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)



class GoogleLoginView(SocialLoginView):
    """
    Google OAuth Login View

    This endpoint allows users to authenticate using a Google OAuth access token.
    Users must first obtain an access token from Google by signing in via Google OAuth.
    Once they receive a valid access token, they can send it to this API to authenticate.

    If the token is valid, the API will return a Django authentication token, which can be
    used for subsequent authenticated requests..
    """

    adapter_class = GoogleOAuth2Adapter

    @extend_schema(
        summary="Google OAuth Login",
        description="""
        Authenticate users using Google OAuth.

        **How it Works:**
        1. The user selects "Sign in with Google" in the frontend application.
        2. Google provides an access token upon successful authentication.
        3. The frontend sends this access token to this endpoint.
        4. The API verifies the token with Google and, if valid:
            - Creates a user account (if they are new).
            - Returns a Django authentication token for further API requests.

        **Request Format:**
        Send a `POST` request with a valid `access_token` obtained from Google.

        **Example Request:**
        ```json
        {
            "access_token": "ya29.a0AfH6SM..."
        }
        ```

        **Response Format:**
        If authentication is successful, the API returns an authentication token.

        **Example Response:**
        ```json
        {
            "key": "7f4e265c8f8c5e64db..."
        }
        ```
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "description": "Google OAuth access token obtained after successful login with Google."
                    }
                },
                "required": ["access_token"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Django authentication token to be used in future requests."
                    }
                }
            },
            400: {
                "description": "Invalid access token or authentication failed."
            }
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class AppleLoginView(SocialLoginView):
    """
    Apple OAuth Login View

    This endpoint allows users to authenticate using an Apple OAuth access token.
    Users must first obtain an access token from Apple by signing in via "Sign in with Apple."
    Once they receive a valid access token, they can send it to this API to authenticate.

    If the token is valid, the API will return a Django authentication token, which can be
    used for subsequent authenticated requests.
    """

    adapter_class = AppleOAuth2Adapter

    @extend_schema(
        summary="Apple OAuth Login",
        description="""
        Authenticate users using Apple OAuth.

        **How it Works:**
        1. The user selects "Sign in with Apple" in the frontend application.
        2. Apple provides an access token upon successful authentication.
        3. The frontend sends this access token to this endpoint.
        4. The API verifies the token with Apple and, if valid:
            - Creates a user account (if they are new).
            - Returns a Django authentication token for further API requests.

        **Request Format:**
        Send a `POST` request with a valid `access_token` obtained from Apple.

        **Example Request:**
        ```json
        {
            "access_token": "eyJraWQiOiJ..."
        }
        ```

        **Response Format:**
        If authentication is successful, the API returns an authentication token.

        **Example Response:**
        ```json
        {
            "key": "7f4e265c8f8c5e64db..."
        }
        ```
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "description": "Apple OAuth access token obtained after successful login with Apple."
                    }
                },
                "required": ["access_token"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Django authentication token to be used in future requests."
                    }
                }
            },
            400: {
                "description": "Invalid access token or authentication failed."
            }
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(tags=["Admins Management"])
# class AdminUserViewSet(ModelViewSet):
#     queryset = User.objects.all()
#     serializer_class = AdminUserSerializer
#     permission_classes = [permissions.IsAdminUser]
#     filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
#     filterset_fields = ["is_active"]
#     search_fields = ["email"]
#     ordering_fields = ["date_joined"]

#     def get_queryset(self):
#         """
#         Returns all users by default.
#         If `booking_type` is provided in query params, filter users based on bookings.
#         """
#         queryset = super().get_queryset()
#         booking_type = self.request.query_params.get("booking_type")

#         if booking_type:
#             filters = {
#                 "flights": "flight_bookings__isnull",
#                 "hotels": "hotel_bookings__isnull",
#                 "cars": "car_bookings__isnull",
#             }
#             filter_condition = filters.get(booking_type)
#             if filter_condition:
#                 queryset = queryset.filter(**{filter_condition: False}).distinct()

#         return queryset


#     @action(detail=True, methods=["patch"], url_path="deactivate")
#     def deactivate_user(self, request, pk=None):
#         """
#         Deactivate a user by setting is_active to False.
#         """
#         user = self.get_object()
#         user.is_active = False
#         user.save()
#         return Response({"detail": "User has been deactivated"}, status=status.HTTP_200_OK)

#     @action(detail=False, methods=["get"], url_path="export")
#     def export_users(self, request):
#         """
#         Export users as a CSV file.
#         """
#         response = HttpResponse(content_type="text/csv")
#         response["Content-Disposition"] = 'attachment; filename="users.csv"'

#         writer = csv.writer(response)
#         writer.writerow(["ID", "Email", "Username", "Is Active", "Date Joined"])

#         users = self.get_queryset()
#         for user in users:
#             writer.writerow([user.id, user.email, user.username, user.is_active, user.date_joined])

#         return response


class AdminUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing admin users, including filtering, searching,
    exporting user data, and retrieving booking history.
    """
    queryset = User.objects.all().prefetch_related("profile")
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["email", "name"]
    ordering_fields = ["date_joined"]

    def get_serializer_class(self):
        """Return appropriate serializer for list and detail views."""
        if self.action == "retrieve":
            return AdminUserDetailSerializer
        return AdminUserSerializer

    def get_queryset(self):
        """
        Returns all users by default.
        If `booking_type` is provided in query params, filters users based on booking type.
        """
        queryset = super().get_queryset().annotate(
            total_flight_bookings=Count("flight_bookings"),
            total_car_bookings=Count("car_bookings"),
        )

        booking_type = self.request.query_params.get("booking_type")

        if booking_type:
            if booking_type == "flights":
                queryset = queryset.filter(flight_bookings__isnull=False).distinct()
            elif booking_type == "cars":
                queryset = queryset.filter(car_bookings__isnull=False).distinct()

        return queryset

    @admin_list_user_schema
    def list(self, request, *args, **kwargs):
        """
        Retrieves a list of users with profile details.
        Supports filtering, searching, and ordering.
        """
        return super().list(request, *args, **kwargs)

    @admin_deactivate_user_schema
    @action(detail=True, methods=["patch"], url_path="deactivate")
    def deactivate_user(self, request, pk=None):
        """
        Deactivate a user by setting is_active to False.
        """
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({"detail": "User has been deactivated"}, status=status.HTTP_200_OK)

    @admin_export_user_schema
    @action(detail=False, methods=["get"], url_path="export")
    def export_users(self, request):
        """
        Export users as a CSV file including ID, Email, Name, Status, Date Joined, and Total Bookings.
        """
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="users.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Email", "Name", "Is Active", "Date Joined", "Total Bookings"])

        users = self.get_queryset()
        for user in users:
            writer.writerow([
                user.id,
                user.email,
                user.name,
                user.is_active,
                user.date_joined.strftime("%Y-%m-%d"),
                user.total_bookings,
            ])

        return response

# ruff: noqa
from smtplib import SMTPRecipientsRefused
from core.applications.users.email import OTPRegistrationEmail
import pyotp
from django.core.cache import cache

from django.contrib.auth import logout
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

from core.applications.users.models import Profile, User
from core.applications.users.token import default_token_generator
from core.helpers.custom_exceptions import CustomError
from core.applications.users.api.serializers import AdminRegistrationSerializer, CustomUserCreateSerializer, EmailSubmissionSerializer, PasswordRetypeSerializer, ProfileSerializers, UserSerializer, VerifyOTPSerializer
from core.helpers.authentication import CustomJWTAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
import logging
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from core.applications.users.api.schemas import(
    submit_email_schema, verify_otp_schema, verify_admin_schema,
    resend_otp_schema
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


class TokenObtainPairView(TokenViewBase):
    """
    Takes a set of user credentials and returns an access and refresh JSON web
    token pair to prove the authentication of those credentials.
    """

    _serializer_class = api_settings.TOKEN_OBTAIN_SERIALIZER


token_obtain_pair = TokenObtainPairView.as_view()


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

@extend_schema(tags=["User Register with OTP"])
class OTPRegistrationViewSet(ViewSet):
    """Handles OTP-based registration and verification."""
    permission_classes = [AllowAny]
    OTP_EXPIRY = 400  # 6 minutes
    OTP_DIGITS = 4
    OTP_SECRET = "JBSWY3DPEHPK3PXP"

    def generate_otp(self, email):
        """Generates and caches a 4-digit OTP."""
        otp = pyotp.TOTP(self.OTP_SECRET, digits=self.OTP_DIGITS).now()
        cache.set(email, otp, timeout=self.OTP_EXPIRY)
        logger.info(f"OTP generated for {email}")
        return otp

    def send_otp_email(self, request, email, otp):
        """Sends OTP via email."""
        OTPRegistrationEmail(request, {"otp": otp}).send([email])
        logger.info(f"OTP email sent to {email}")

    def generate_tokens(self, user):
        """Generates JWT tokens."""
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}

    def validate_otp(self, email, otp):
        """Validates OTP from cache."""
        cached_otp = cache.get(email)
        if cached_otp == otp:
            cache.delete(email)
            return True
        return False

    @submit_email_schema
    @action(detail=False, methods=["post"])
    def submit_email(self, request):
        """Submits email to receive an OTP."""
        serializer = EmailSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            self.send_otp_email(request, email, self.generate_otp(email))
            return Response({"message": "OTP sent to your email."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def register_user(self, request, serializer_class):
        """Registers a user or admin after OTP validation."""
        serializer = serializer_class(data=request.data)
        if serializer.is_valid():
            email, otp = serializer.validated_data["email"], serializer.validated_data["otp"].strip()
            if self.validate_otp(email, otp):
                user = serializer.save()
                logger.info(f"Account created for {email}")
                return Response({"message": "User created successfully.", **self.generate_tokens(user)}, status=status.HTTP_201_CREATED)
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @verify_otp_schema
    @action(detail=False, methods=["post"])
    def verify_otp_and_set_password(self, request):
        """Verifies OTP, sets password, and logs in the user."""
        return self.register_user(request, CustomUserCreateSerializer)

    @verify_admin_schema
    @action(detail=False, methods=["post"])
    def verify_admin(self, request):
        """Verifies OTP and registers an admin."""
        return self.register_user(request, AdminRegistrationSerializer)

    @resend_otp_schema
    @action(detail=False, methods=["post"])
    def resend_otp(self, request):
        """Resends OTP to the user."""
        serializer = EmailSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            self.send_otp_email(request, email, self.generate_otp(email))
            return Response({"message": "New OTP sent to your email."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["User"])
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
        self.get_object = self.get_instance
        if request.method == "GET":
            return self.retrieve(request, *args, **kwargs)
        if request.method == "PUT":
            return self.update(request, *args, **kwargs)
        if request.method == "PATCH":
            return self.partial_update(request, *args, **kwargs)
        if request.method == "DELETE":
            return self.destroy(request, *args, **kwargs)

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
    @action(["get"], detail=False, authentication_classes=[JWTAuthentication])
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



class GoogleLoginView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    @extend_schema(
        summary="Google OAuth Login",
        description="Authenticate using a Google OAuth access token",
        request={
            "application/json": {
                "type": "object",
                "properties": {"access_token": {"type": "string"}}
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {"key": {"type": "string"}}
            }
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class FacebookLoginView(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter

    @extend_schema(
        summary="Facebook OAuth Login",
        description="Authenticate using a Facebook OAuth access token",
        request={
            "application/json": {
                "type": "object",
                "properties": {"access_token": {"type": "string"}}
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {"key": {"type": "string"}}
            }
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class AppleLoginView(SocialLoginView):
    adapter_class = AppleOAuth2Adapter

    @extend_schema(
        summary="Apple OAuth Login",
        description="Authenticate using a Apple OAuth access token",
        request={
            "application/json": {
                "type": "object",
                "properties": {"access_token": {"type": "string"}}
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {"key": {"type": "string"}}
            }
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

import contextlib
from typing import Literal
from django.utils.module_loading import import_string
from django.contrib.auth import authenticate
from django.contrib.auth import user_logged_in
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions as django_exceptions
from core.applications.cars.models import Booking, CarBooking
from core.applications.flights.models import FlightBooking
from core.helpers.enums import Account_Delete_Reason_Choices
from djoser.compat import get_user_email
from djoser.conf import settings
from djoser.serializers import UserCreateSerializer
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings
from django.core.cache import cache
from django.conf import settings as django_settings

from core.applications.users.managers import OTPManager
from core.applications.users.models import Profile, User
from core.applications.users.token import default_token_generator
from core.helpers.custom_exceptions import CustomError
from core.helpers.interface import BaseModelNoDefs
# from core.helpers.password_validator import validate_password_strength
import logging
from core.applications.users.email import ActivationEmail, ConfirmationEmail
from drf_spectacular.utils import extend_schema_field

logger = logging.getLogger(__name__)
from django.contrib.auth import get_user_model
User = get_user_model()


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name", "email"]


class CustomUserCreateSerializer(serializers.ModelSerializer):
    otp = serializers.CharField(
        required=True,
        write_only=True,
        help_text="Required. OTP sent to the user's email.",
    )

    class Meta:
        model = User
        fields = ("email", "password", "otp")
        extra_kwargs = {
            "otp": {"write_only": True},
        }

    def validate(self, attrs):
        logger.info(f"Validated data: {attrs}")  # Log the validated data
        email = attrs.get("email")
        otp = attrs.get("otp").strip()
        password = attrs.get("password")

        if not email:
            raise serializers.ValidationError({"email": "Email is required."})

        # Verify OTP
        cached_otp = cache.get(email)
        if cached_otp != otp:
            raise serializers.ValidationError({"otp": "Invalid or expired OTP."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("otp")  # OTP is validated, remove before saving
        return User.objects.create_user(**validated_data)


class AdminRegistrationSerializer(CustomUserCreateSerializer):
    class Meta:
        model = User
        fields = ("email", "password", "otp")

    def create(self, validated_data):
        validated_data.pop("otp")  # Remove OTP after validation

        user = User.objects.create_superuser(**validated_data)
        user.is_staff = True
        user.is_admin = True  # Explicitly set this field
        user.save()

        return user


class OTPVerificationSerializer(serializers.Serializer):
    """Serializer for verifying OTP."""
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, max_length=4, min_length=4)


class PasswordSetSerializer(serializers.Serializer):
    """Serializer for setting password after OTP verification."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password]  # Django's built-in password validators
    )
    def validate_email(self, email):
        user_exists = User.objects.filter(email=email).exists()
        is_verified = cache.get(f"{email}_verified")

        # Only require OTP if user doesn't exist
        if not user_exists and not is_verified:
            raise serializers.ValidationError("OTP not verified or expired.")
        return email

class OSNameSchema(BaseModelNoDefs):
    Android: Literal["Android"] | None = None
    iOS: Literal["iOS", "iPadOS"] | None = None  # noqa: N815
    web: Literal["iOS", "Windows", "Android"] | None = None


class ModelNameSchema(BaseModelNoDefs):
    Android: str | None = None
    iOS: str | None = None  # noqa: N815
    web: str | None = None


class OSVersionSchema(BaseModelNoDefs):
    Android: str | None = None
    iOS: str | None = None  # noqa: N815
    web: str | None = None


class UserDeviceInfoSchema(BaseModelNoDefs):
    osName: Literal["Android", "android", "iOS", "ios", "web", "Web"] | None = (  # noqa: N815
        None
    )
    modelName: str | None = None  # noqa: N815
    osVersion: str | None = None  # noqa: N815


class UserMetadataSchema(BaseModelNoDefs):
    push_notification_id: str | None
    device_info: UserDeviceInfoSchema | None


class UserSerializer:
    class AddOrRetrieveDevice(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ("email",)

    class Update(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ("email",)

    class Info(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = (
                "id",
                "email",
                "name",
            )


class GetUser(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "name",
        )

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                "Status": 400,
                "Message": "No account is associated with this email.",
                "Error": True
            })
        self.user = user
        return value


    def get_user(self):
        return getattr(self, "user", None)

class EmailAndTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()

    default_error_messages = {
        "invalid_token": "The token may have expired or is invalid.",
        "invalid_email": "No user found with that email. Create an account or try another email.",  # noqa: E501
    }

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        # uid validation have to be here, because validate_<field_name>
        # doesn't work with modelserializer
        try:
            email = self.initial_data.get("email", "")
            self.user = User.objects.get(email=email)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError) as e:
            key_error = "invalid_email"
            raise CustomError.BadRequest(
                {"email": self.error_messages[key_error]},
                code=key_error,
            ) from e

        is_token_valid = default_token_generator.check_token(
            self.user,
            self.initial_data.get("token", ""),
        )
        generated_token = default_token_generator.make_token(self.user)
        print(generated_token, ".>>>>>>>>>>>>>>>>>>>>>>")
        if is_token_valid:
            return validated_data
        key_error = "invalid_token"
        raise CustomError.BadRequest(
            {"token": self.error_messages[key_error]},
            code=key_error,
        )


class PasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(style={"input_type": "password"}, write_only=True)

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(self, "user", None) or (request.user if request else None)

        if not user:
            raise CustomError.BadRequest({"user": "User instance is required."})

        try:
            validate_password(attrs["new_password"], user)
        except django_exceptions.ValidationError as e:
            raise CustomError.BadRequest({"new_password": e.messages[0]})

        return attrs


class PasswordRetypeSerializer(PasswordSerializer):
    re_new_password = serializers.CharField(style={"input_type": "password"}, write_only=True)

    default_error_messages = {
        "password_mismatch": settings.CONSTANTS.messages.PASSWORD_MISMATCH_ERROR,
    }

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if attrs["new_password"] != attrs["re_new_password"]:
            raise CustomError.BadRequest({"re_new_password": self.error_messages["password_mismatch"]})

        return attrs

class VerifiedEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    default_error_messages = {
        "invalid_email": "No user found with that email. Create an account or try another email.",
        "superuser_not_allowed": "Superuser accounts cannot reset their password using this flow.",
    }

    def validate(self, attrs):
        email = self.initial_data.get("email", "")
        try:
            self.user = User.objects.get(email=email)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError) as e:
            raise CustomError.BadRequest(
                {"email": self.error_messages["invalid_email"]},
                code="invalid_email"
            ) from e

        # Check if the user is a superuser
        # if self.user.is_superuser:
        #     raise CustomError.BadRequest(
        #         {"email": self.error_messages["superuser_not_allowed"]},
        #         code="superuser_not_allowed"
        #     )

        return attrs


class SetNewPasswordSerializer(VerifiedEmailSerializer, PasswordSerializer):
    pass

class UsernameSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (settings.LOGIN_FIELD,)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username_field = settings.LOGIN_FIELD
        self._default_username_field = User.USERNAME_FIELD
        self.fields[f"new_{self.username_field}"] = self.fields.pop(self.username_field)

    def save(self, **kwargs):
        if self.username_field != self._default_username_field:
            kwargs[User.USERNAME_FIELD] = self.validated_data.get(
                f"new_{self.username_field}",
            )
        return super().save(**kwargs)


class UsernameRetypeSerializer(UsernameSerializer):
    default_error_messages = {
        "username_mismatch": settings.CONSTANTS.messages.USERNAME_MISMATCH_ERROR.format(
            settings.LOGIN_FIELD,
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["re_new_" + settings.LOGIN_FIELD] = serializers.CharField()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        new_username = attrs[settings.LOGIN_FIELD]
        if new_username != attrs[f"re_new_{settings.LOGIN_FIELD}"]:
            return self.fail("username_mismatch")
        return attrs


class ActivationSerializer(EmailAndTokenSerializer):
    default_error_messages = {
        "stale_token": settings.CONSTANTS.messages.STALE_TOKEN_ERROR,
    }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not self.user.is_active:
            return attrs
        raise PermissionDenied(self.error_messages["stale_token"])


class PasswordResetConfirmSerializer(EmailAndTokenSerializer, PasswordSerializer):
    pass


class PasswordResetConfirmRetypeSerializer(
    EmailAndTokenSerializer,
    PasswordRetypeSerializer,
):
    pass


class UsernameResetConfirmSerializer(EmailAndTokenSerializer, UsernameSerializer):
    pass


class UsernameResetConfirmRetypeSerializer(
    EmailAndTokenSerializer,
    UsernameRetypeSerializer,
):
    pass


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def get_setup_info(self, user: User):
        return {"user_info": user.accounts_dict, "is_verified": user.is_verified}

    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            "password": attrs["password"],
        }
        with contextlib.suppress(KeyError):
            authenticate_kwargs["request"] = self.context["request"]

        self.user: User = authenticate(**authenticate_kwargs)
        if not self.user:
            if user := User.objects.filter(email=attrs["email"]).first():
                if not user.is_active:
                    context = {"user": user}
                    to = [get_user_email(user)]
                    settings.EMAIL.activation(self.context["request"], context).send(to)
                    msg = "Your account is not yet verified, kindly check yur email and proceed to verification"  # noqa: E501
                    raise PermissionDenied(
                        msg,
                    )
                if not api_settings.USER_AUTHENTICATION_RULE(self.user):
                    raise AuthenticationFailed(
                        detail="Login failed. Please check your email and password and try again.",  # noqa: E501
                    )

        data = super().validate(attrs)
        refresh = self.get_token(self.user)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)
        data["setup_info"] = None
        data["registration_complete"] = None
        data["setup_info"] = UserSerializer.Info(instance=self.user).data
        data["registration_complete"] = all([self.user.is_active])
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)
        if not self.user.is_superuser:
            user_logged_in.send(
                sender=self.user.__class__,
                token=data["access"],
                user=self.user,
            )
        return data



class UserDeleteSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=Account_Delete_Reason_Choices.choices)
    additional_feedback = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        reason = data.get("reason")
        feedback = data.get("additional_feedback", "").strip()

        if reason == Account_Delete_Reason_Choices.OTHERS and not feedback:
            raise serializers.ValidationError({
                "additional_feedback": "Please provide feedback when selecting 'Others'."
            })
        return data



# class VerifyOTPSerializer(serializers.Serializer):
#     """
#     Serializer to handle OTP verification and password setup.
#     """
#     email = serializers.EmailField()
#     otp = serializers.CharField(max_length=4, min_length=4)
#     password = serializers.CharField(write_only=True, min_length=8)
#     confirm_password = serializers.CharField(write_only=True, min_length=8)

#     def validate(self, data):
#         """
#         Validate OTP and password match.
#         """
#         if not OTPManager.verify_otp(data["email"], data["otp"]):
#             raise serializers.ValidationError({"otp": "Invalid OTP."})

#         if data["password"] != data["confirm_password"]:
#             raise serializers.ValidationError({"password": "Passwords do not match."})

#         return data

#     def create_user(self):
#         """
#         Creates a new user after OTP validation.
#         """
#         email = self.validated_data["email"]
#         password = self.validated_data["password"]

#         user = User.objects.create(
#             email=email,
#             password=make_password(password),
#             is_active=True,  # Activate user after verification
#         )
#         return user


# class RequestOTPSerializer(serializers.Serializer):
#     """
#     Serializer to handle OTP request.
#     """
#     email = serializers.EmailField()

#     def validate_email(self, value):
#         """
#         Validate if the email exists in the system.
#         """
#         if User.objects.filter(email=value).exists():
#             raise serializers.ValidationError("Email is already registered.")
#         return value


#     def send_otp(self):
#         """
#         Generates OTP, stores it in cache, and sends email.
#         """
#         email = self.validated_data["email"].strip().lower()
#         otp = OTPManager.generate_otp(email)

#         # Store OTP in cache for 5 minutes
#         cache.set(f"otp_{email}", otp, timeout=300)

#         # Send email
#         context = {"otp": otp}

#         try:
#             if settings.SEND_ACTIVATION_EMAIL:
#                 email_instance = ActivationEmail(context=context)
#                 email_instance.send([email])  # ✅ Send without request.user
#             elif settings.SEND_CONFIRMATION_EMAIL:
#                 email_instance = ConfirmationEmail(context=context)
#                 email_instance.send([email])  # ✅ Send without request.user
#             print(f"OTP email sent! OTP: {otp}")  # Debugging: Print OTP
#         except Exception as e:
#             print(f"Email sending failed: {e}")


class EmailSubmissionSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()


    def validate(self, data):
        """Check if OTP is valid and correctly formatted."""
        email = data["email"].strip().lower()
        otp = str(data["otp"]).strip()  # Ensure OTP is always a string
        print(otp, "zzzzzzzzzzzzzzzzzzz")

        # 🔍 Debug: Print stored OTP (Only for testing, remove in production)
        stored_otp = cache.get(f"otp_{email}")
        print(f"Stored OTP for {email}: {stored_otp}")  # Check if OTP is saved

        if not stored_otp:
            raise serializers.ValidationError("OTP not found or expired.")

        if stored_otp != otp:
            raise serializers.ValidationError("Invalid OTP entered.")

        return data

    def save(self):
        """Create a new user with the verified email."""
        email = self.validated_data["email"]

        # Create user (if not exists)
        user, created = User.objects.get_or_create(email=email)

        # ✅ Clear OTP from cache after successful verification
        cache.delete(f"otp_{email}")

        return {"message": "Email verified successfully. Proceed to set up your account."}


class ProfileSerializers:
    class BaseProfileSerializer(serializers.ModelSerializer):
        email = serializers.EmailField(source="user.email", read_only=True)

        class Meta:
            model = Profile
            fields = (
               "id", "email", "first_name", "last_name", "gender",
                "date_of_birth", "address", "mobile_number"
            )



# class AdminUserSerializer(serializers.ModelSerializer):
#     flight_bookings = serializers.SerializerMethodField()
#     # hotel_bookings = serializers.SerializerMethodField()
#     car_bookings = serializers.SerializerMethodField()

#     class Meta:
#         model = User
#         fields = (
#             "id",
#             "email",
#             "name",
#             "is_active",
#             "is_staff",
#             "is_superuser",
#             "flight_bookings",
#             # "hotel_bookings",
#             "car_bookings",
#         )

#     def get_flight_bookings(self, obj):
#         return FlightBooking.objects.filter(user=obj).values(
#             "id",
#             "service_fee",
#         )
#     def get_car_bookings(self, obj):
#         return Booking.objects.filter(user=obj).values(
#             "id"
#         )


# class AdminUserSerializer(serializers.ModelSerializer):
#     profile_picture = serializers.SerializerMethodField()
#     date_created = serializers.DateTimeField(source="date_joined", format="%Y-%m-%d", read_only=True)
#     total_bookings = serializers.SerializerMethodField()
#     flight_bookings = serializers.SerializerMethodField()
#     car_bookings = serializers.SerializerMethodField()

#     class Meta:
#         model = User
#         fields = (
#             "id",
#             "email",
#             "name",
#             "is_active",
#             "is_staff",
#             "is_superuser",
#             "profile_picture",
#             "date_created",
#             "total_bookings",
#             "flight_bookings",
#             "car_bookings",
#         )

#     def get_profile_picture(self, obj):
#         """Get user's profile picture URL or default avatar."""
#         if hasattr(obj, "profile") and obj.profile.profile_pics:
#             return obj.profile.profile_pics.url
#         return f"{settings.STATIC_URL}images/avatar.png"

#     def get_total_bookings(self, obj):
#         """Count total bookings associated with the user."""
#         return Booking.objects.filter(user=obj).count()

#     def get_flight_bookings(self, obj):
#         """Retrieve flight booking history."""
#         return FlightBooking.objects.filter(booking__user=obj).values(
#             "id",
#             "booking_reference",
#             "booking_type",
#             "currency",
#             "service_fee",
#             "base_flight_cost",
#         )

#     def get_car_bookings(self, obj):
#         """Retrieve car booking history."""
#         return CarBooking.objects.filter(booking__user=obj).values(
#             "id",
#             "booking_reference",
#             "pickup_location__name",
#             "dropoff_location__name",
#             "pickup_date",
#             "dropoff_date",
#             "base_transfer_cost",
#             "service_fee",
#         )


class AdminUserSerializer(serializers.ModelSerializer):
    """
    Serializer for listing users.
    Includes profile picture, name, email, date created, and total bookings.
    """
    profile_picture = serializers.SerializerMethodField()
    first_name = serializers.CharField(source="profile.first_name", read_only=True)
    last_name = serializers.CharField(source="profile.last_name", read_only=True)
    date_created = serializers.DateTimeField(source="date_joined", format="%Y-%m-%d", read_only=True)
    total_bookings = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "name",
            "profile_picture", "date_created", "total_bookings"
        )

    @extend_schema_field(str)
    def get_profile_picture(self, obj):
        """Retrieve the user's profile picture or default avatar."""
        profile = getattr(obj, "profile", None)
        if profile and profile.profile_pics:
            return profile.profile_pics.url
        return f"{django_settings.STATIC_URL}images/avatar.png"

    def get_first_name(self, obj):
        """Retrieve the first name from the profile model, handle if profile doesn't exist."""
        return obj.profile.first_name if hasattr(obj, "profile") and obj.profile else ""

    def get_last_name(self, obj):
        """Retrieve the last name from the profile model, handle if profile doesn't exist."""
        return obj.profile.last_name if hasattr(obj, "profile") and obj.profile else ""


class AdminUserDetailSerializer(AdminUserSerializer):
    """
    Serializer for retrieving detailed user information,
    including booking histories (flights, cars, and hotels).
    """
    flight_bookings = serializers.SerializerMethodField()
    car_bookings = serializers.SerializerMethodField()

    class Meta(AdminUserSerializer.Meta):
        fields = AdminUserSerializer.Meta.fields + ("flight_bookings", "car_bookings")

    def get_flight_bookings(self, obj):
        """Retrieve flight booking history."""
        return FlightBooking.objects.filter(booking__user=obj).values(
            "id",
            "booking_reference",
            "booking_type",
            "currency",
            "service_fee",
            "base_flight_cost",
        )
    @extend_schema_field(str)

    def get_car_bookings(self, obj):
        """Retrieve car booking history."""
        return CarBooking.objects.filter(booking__user=obj).values(
            "id",
            "booking_reference",
            "pickup_location__name",
            "dropoff_location__name",
            "pickup_date",
            "dropoff_date",
            "base_transfer_cost",
            "service_fee",
        )




class SuperUserTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer to restrict JWT login to superusers only.
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.is_superuser:
            raise serializers.ValidationError(
                "Only superusers are allowed to authenticate."
            )
        return data

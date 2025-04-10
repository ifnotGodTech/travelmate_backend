from core.applications.users.api.serializers import AdminRegistrationSerializer, AdminUserSerializer, CustomUserCreateSerializer, EmailAndTokenSerializer, EmailSubmissionSerializer, OTPVerificationSerializer, PasswordSetSerializer
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import OpenApiParameter, OpenApiExample, OpenApiTypes, OpenApiResponse
from djoser.conf import settings

login_validate_email_schema = extend_schema(
    summary="Validate Email",
    description="Step 1 of 2-step login: Validates whether the provided email exists in the system.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email", "example": "user@example.com"}
            },
            "required": ["email"]
        }
    },
    responses={
        200: OpenApiExample(
            name="Email Found",
            value={"detail": "Email exists."},
            response_only=True
        ),
        400: OpenApiExample(
            name="Email Not Found",
            value={"detail": "Email not found."},
            response_only=True
        )
    }
)


login_validate_password_schema = extend_schema(
    summary="Validate Password and Obtain JWT Tokens",
    description="Step 2 of 2-step login: Validates email and password, and returns access and refresh tokens.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email", "example": "user@example.com"},
                "password": {"type": "string", "format": "password", "example": "strong_password123"}
            },
            "required": ["email", "password"]
        }
    },
    responses={
        200: OpenApiExample(
            name="Successful Login",
            value={
                "access": "eyJ0eXAiOiJKV1QiLCJhbGciOi...",
                "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOi..."
            },
            response_only=True
        ),
        400: OpenApiExample(
            name="Invalid Credentials",
            value={"detail": "Invalid credentials."},
            response_only=True
        )
    }
)


submit_email_schema = extend_schema(
        summary="Step 1: Submit Email to Receive OTP",
        description="User submits their email to receive an OTP for registration.",
        request=EmailSubmissionSerializer,
        responses={
            200: OpenApiExample(
                name="OTP Sent",
                value={"message": "OTP sent to your email."},
                response_only=True,
            ),
            400: OpenApiExample(
                name="Invalid Email",
                value={"error": "Invalid email format."},
                response_only=True,
            ),
        },
    )


set_password_schema = extend_schema(
        summary="Step 3: Set Password After OTP Verification",
        description="Once the OTP is verified, the user can set their password to complete registration.",
        request=PasswordSetSerializer,
        responses={
            201: OpenApiExample(
                name="Password Set Successfully",
                value={"message": "Password set successfully.", "access": "JWT_ACCESS_TOKEN", "refresh": "JWT_REFRESH_TOKEN"},
                response_only=True,
            ),
            400: OpenApiExample(
                name="OTP Not Verified",
                value={"error": "OTP not verified or expired."},
                response_only=True,
            ),
        },
    )

# Schema for verifying OTP and registering a standard user
verify_otp_schema = extend_schema(
        summary="Step 2: Verify OTP",
        description="User enters the OTP received in email to verify their account.",
        request=OTPVerificationSerializer,
        responses={
            200: OpenApiExample(
                name="OTP Verified",
                value={"message": "OTP verified. Proceed to set your password."},
                response_only=True,
            ),
            400: OpenApiExample(
                name="Invalid OTP",
                value={"error": "Invalid or expired OTP."},
                response_only=True,
            ),
        },
    )
# Schema for verifying OTP and registering an admin user
verify_admin_schema = extend_schema(
    operation_id="verify_admin",
    summary="Verify OTP & Register Admin",
    description=(
        "Verifies the provided OTP, registers the user as an admin, "
        "and grants them administrative privileges."
    ),
    request=AdminRegistrationSerializer,
    responses={
        201: OpenApiResponse(description="Admin registered successfully."),
        400: OpenApiResponse(description="Invalid OTP or validation error."),
    },
)

# Schema for resending OTP
resend_otp_schema = extend_schema(
    operation_id="resend_otp",
    summary="Resend OTP",
    description="Users can request a new OTP if they did not receive or lost the previous one.",
    request=EmailSubmissionSerializer,
    responses={
        200: OpenApiResponse(description="A new OTP has been sent to your email."),
        400: OpenApiResponse(description="Invalid email format or missing field."),
    },
)


admin_list_user_schema = extend_schema(
        operation_id="admin_list_user",
        summary="List All Users",
        description="Retrieve a list of all users with profile details.",
        parameters=[
            OpenApiParameter(name="search", description="Search users by email or name.", required=False, type=str),
            OpenApiParameter(name="ordering", description="Order by date joined.", required=False, type=str),
            OpenApiParameter(name="booking_type", description="Filter users by booking type (flights, hotels, cars).", required=False, type=str),
        ],
        responses={200: AdminUserSerializer(many=True)},
    )


admin_deactivate_user_schema = extend_schema(
        description="Deactivate a user by setting `is_active` to False.",
        responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
    )

admin_export_user_schema = extend_schema(
        description="Export user data as a CSV file.",
        responses={200: {"content": {"text/csv": {}}}},
    )


reset_password_schema = extend_schema(
    summary="(Step 1 to reset passoword.)Request password reset email",
    description="Initiate password reset process by sending an email with UID and token to the user.",
    request={"application/json": {"email": "user@example.com"}},
    responses={204: None},
    examples=[
        OpenApiExample(
            name="Password Reset Request",
            value={"email": "user@example.com"},
            request_only=True,
        )
    ],
)

validate_password_reset_token_schema = extend_schema(
    summary="(Step 2 to reset passoword.)Validate password reset token",
    description="Verifies that the provided UID and token are valid for password reset.",
    request=EmailAndTokenSerializer,
    responses={200: OpenApiExample(
        name="Token Valid",
        value={"detail": "Token is valid."},
        response_only=True
    )},
    examples=[
        OpenApiExample(
            name="Token Validation",
            value={"uid": "Mg", "token": "abc123-token"},
            request_only=True,
        )
    ],
)

reset_password_confirm_schema = extend_schema(
    summary="Confirm password reset",
    description="Sets a new password using a valid UID and token. This completes the password reset process.",
    request=settings.SERIALIZERS.password_reset_confirm,
    responses={204: None},
    examples=[
        OpenApiExample(
            name="Confirm Reset",
            value={
                "uid": "Mg",
                "token": "abc123-token",
                "new_password": "NewSecurePassword1!"
            },
            request_only=True,
        )
    ],
)

set_new_password_schema = extend_schema(
    summary="(Step 3 to reset passoword.)Set new password (via reset)",
    description="Sets a new password using UID and token. Designed for separate password-reset flow.",
    request=settings.SERIALIZERS.set_new_password,
    responses={204: None},
    examples=[
        OpenApiExample(
            name="Set New Password",
            value={
                "uid": "Mg",
                "token": "abc123-token",
                "new_password": "NewPassword123!"
            },
            request_only=True,
        )
    ],
)

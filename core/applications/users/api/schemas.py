from core.applications.users.api.serializers import AdminRegistrationSerializer, AdminUserSerializer, CustomUserCreateSerializer, EmailSubmissionSerializer, OTPVerificationSerializer, PasswordSetSerializer
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import OpenApiParameter, OpenApiExample, OpenApiTypes, OpenApiResponse


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

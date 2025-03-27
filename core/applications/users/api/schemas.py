from core.applications.users.api.serializers import AdminRegistrationSerializer, CustomUserCreateSerializer, EmailSubmissionSerializer
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import OpenApiParameter, OpenApiExample, OpenApiTypes, OpenApiResponse


submit_email_schema = extend_schema(
    operation_id="submit_email",
    summary="Submit Email for OTP",
    description="Users submit their email to receive a One-Time Password (OTP) for authentication.",
    request=EmailSubmissionSerializer,
    responses={
        200: OpenApiResponse(description="OTP has been sent to your email."),
        400: OpenApiResponse(description="Invalid email format or missing field."),
    },
)

# Schema for verifying OTP and registering a standard user
verify_otp_schema = extend_schema(
    operation_id="verify_otp_and_set_password",
    summary="Verify OTP & Register User",
    description=(
        "Verifies the provided OTP, allows the user to set a password, "
        "and automatically logs them in."
    ),
    request=CustomUserCreateSerializer,
    responses={
        201: OpenApiResponse(description="User registered successfully."),
        400: OpenApiResponse(description="Invalid OTP or validation error."),
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

from core.applications.users.api.serializers import(
     AdminRegistrationSerializer, AdminUserDetailSerializer, AdminUserSerializer,
     BulkDeleteUserSerializer,
     EmailAndTokenSerializer, EmailSubmissionSerializer,
     OTPVerificationSerializer, PasswordSetSerializer, SoftDeletedUserSerializer,
     RoleSerializer,
)
from drf_spectacular.utils import extend_schema, extend_schema_view
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
    summary="Step 1: Submit Email for OTP",
    description="Submit an email to receive an OTP. If the email is already registered, a 307 response is returned indicating to proceed with login.",
    request=EmailSubmissionSerializer,
    responses={
        200: OpenApiResponse(description="OTP sent to email."),
        307: OpenApiResponse(description="Email already exists. Proceed with login."),
        400: OpenApiResponse(description="Invalid email submission.")
    }
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
        description="Verify the OTP sent to the provided email. On success, allows the user to proceed with password setup.",
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

admin_extend_viewer = extend_schema_view(
    list=extend_schema(
        summary="List all admin users",
        description="Returns a list of all admin users with optional filters.",
        responses={200: AdminUserSerializer(many=True)}
    ),
    retrieve=extend_schema(
        summary="Get a specific admin user",
        description="Retrieves detailed information for a specific admin user.",
        responses={200: AdminUserDetailSerializer}
    ),
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
        operation_id="admin_deactivate_user",
        summary="Deactivate User",
        description="Deactivate a user by setting `is_active` to False.",
        responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
    )

admin_activate_user_schema = extend_schema(
    operation_id="admin_activate_user",
    summary="Activate User" ,
    description="Activate a user by  setting is_active to True.",
     responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
)

admin_export_user_schema = extend_schema(
        operation_id="admin_export_user",
        summary="Export User Data",
        description="Export user data as a CSV file.",
        responses={200: {"content": {"text/csv": {}}}},
    )

admin_bulk_delete_user = extend_schema(
    summary="Bulk Delete Users",
    description="Deletes multiple users at once using a list of user IDs.",
    request=BulkDeleteUserSerializer,
    responses={
        200: OpenApiResponse(
            description="Users successfully deleted",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "Status": 200,
                        "Message": "3 user(s) have been deleted successfully.",
                        "Error": False
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Validation or deletion error",
            examples=[
                OpenApiExample(
                    "Missing or invalid data",
                    value={
                        "Status": 400,
                        "Message": "Please provide a valid list of user IDs.",
                        "Error": True
                    }
                )
            ]
        ),
    }
)

admin_list_deleted_users = extend_schema(
        summary="List users who deleted their account",
        description=(
            "Returns a list of users who have soft-deleted their accounts by setting `is_active=False`. "
            "Includes the reason and any additional feedback they provided during deletion."
        ),
        responses={200: OpenApiResponse(response=SoftDeletedUserSerializer(many=True))},
        tags=["Admin - Users"]
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

make_admin_schema = extend_schema(
    operation_id="make_admin",
    summary="Promote User to Admin",
    description="Promote a user to admin (is_staff=True). Only superusers can do this.",
    responses={200: OpenApiResponse(description="User promoted to admin")}
)

admin_grouped_permissions_schema = extend_schema(
    summary="Retrieve grouped permissions",
    description="Returns all Django permissions grouped by their app label. Accessible only by superadmins.",
    responses={
        200: {
            "type": "object",
            "description": "Grouped permissions data",
            "example": {
                "auth": [
                    {"id": 1, "name": "Can add user", "codename": "add_user"},
                    {"id": 2, "name": "Can change user", "codename": "change_user"},
                ],
                "blog": [
                    {"id": 10, "name": "Can add post", "codename": "add_post"},
                ]
            }
        },
        403: {
            "description": "Permission denied if user is not superadmin"
        }
    }
)

create_role_schema = extend_schema(
    summary="Create a new role",
    description="Create a role with a name, description, and associated permissions.",
    request={"application/json": RoleSerializer},
    responses={
        201: RoleSerializer,
        400: {"description": "Validation errors on role data"},
    }
)

delete_role_schema = extend_schema(
    summary="Delete a role",
    description="Delete a role if it has no assigned users. Otherwise, returns an error.",
    responses={
        204: {"description": "Role deleted successfully"},
        400: {
            "description": "Cannot delete a role with assigned users",
            "example": {"message": "Cannot delete a role with assigned users.", "error": True}
        }
    }
)

assign_admin_schema = extend_schema(
    summary="Assign user to role",
    description="Assign an existing user to the specified role by providing the user's email.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "format": "email",
                    "description": "Email of the user to assign"
                }
            },
            "required": ["email"],
            "example": {
                "email": "user@example.com"
            }
        }
    },
    responses={
        200: {
            "description": "User assigned to role successfully",
            "example": {
                "message": "User user@example.com assigned to role Admin.",
                "error": False
            }
        },
        400: {
            "description": "Missing email in request",
            "example": {
                "message": "Email is required.",
                "error": True
            }
        },
        404: {
            "description": "User not found",
            "example": {
                "message": "User with this email does not exist.",
                "error": True
            }
        }
    }
)

invite_admin_schema =  extend_schema(
    summary="Invite admin by email",
    description=(
        "Invite a new user to the admin dashboard by sending an invitation email. "
        "If the email has already been invited and not accepted, the request will fail. "
        "Only superadmins can perform this action."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "format": "email",
                    "description": "Email of the invited user"
                },
                "name": {
                    "type": "string",
                    "description": "Name of the invited user (optional)"
                }
            },
            "required": ["email"],
            "example": {
                "email": "invitee@example.com",
                "name": "John Doe"
            }
        }
    },
    responses={
        201: {
            "description": "Invitation sent successfully",
            "example": {
                "message": "Invitation sent successfully.",
                "error": False
            }
        },
        400: {
            "description": "Missing email in request",
            "example": {
                "message": "Email is required.",
                "error": True
            }
        },
        409: {
            "description": "An invitation for this email is already pending",
            "example": {
                "message": "An invitation for this email is already pending.",
                "error": True
            }
        }
    }
)

remove_admin_schema = extend_schema(
    summary="Remove a user from a role",
    description=(
        "Remove an existing user from the specified role by their email address. "
        "Only superadmins can perform this action. "
        "If the user is not part of the role, an error will be returned."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "format": "email",
                    "description": "Email address of the user to remove from the role"
                }
            },
            "required": ["email"],
            "example": {
                "email": "user_to_remove@example.com"
            }
        }
    },
    responses={
        200: {
            "description": "User removed successfully from the role",
            "example": {
                "message": "User user_to_remove@example.com has been removed from the role 'Admin'.",
                "error": False
            }
        },
        400: {
            "description": "User is not a member of this role or invalid input",
            "example": {
                "message": "User user_to_remove@example.com is not part of the role.",
                "error": True
            }
        },
        404: {
            "description": "User with the provided email does not exist",
            "example": {
                "message": "User with email user_to_remove@example.com does not exist.",
                "error": True
            }
        }
    }
)

accept_invitation_schema = extend_schema(
        summary="Accept Invitation",
        description="Accepts an admin invitation using the provided email, token, and sets a new password.",
        request=OpenApiTypes.OBJECT,
        examples=[
            OpenApiExample(
                "Accept Invitation Request Example",
                value={
                    "email": "user@example.com",
                    "token": "your-token-here",
                    "password": "NewSecurePassword123!"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Successful Response",
                value={
                    "message": "Invitation accepted, password set, and role assigned.",
                    "error": False
                },
                response_only=True
            ),
            OpenApiExample(
                "Error Response - Missing Fields",
                value={
                    "message": "Email, token, and password are required.",
                    "error": True
                },
                response_only=True
            ),
        ],
        responses={
            200: OpenApiResponse(description="Invitation accepted and user activated."),
            400: OpenApiResponse(description="Missing/invalid data or token."),
            404: OpenApiResponse(description="Invitation not found or already accepted."),
        }
    )

validate_invitation_schema = extend_schema(
    summary="Validate Invitation Token",
    description="Check if the invitation token is valid, not expired, and has not already been used.",
    parameters=[
        OpenApiParameter(
            name="token",
            type=str,
            location=OpenApiParameter.QUERY,
            required=True,
            description="The invitation token to be validated.",
        )
    ],
    examples=[
        OpenApiExample(
            "Valid Token Example",
            value={"token": "sample-valid-token"},
            request_only=True
        ),
        OpenApiExample(
            "Success Response",
            value={
                "message": "Token is valid.",
                "email": "invited-user@example.com",
                "error": False
            },
            response_only=True
        ),
        OpenApiExample(
            "Expired/Invalid Token",
            value={
                "message": "Invalid or expired token.",
                "error": True
            },
            response_only=True
        ),
        OpenApiExample(
            "Token Already Used",
            value={
                "message": "This invitation has already been used.",
                "error": True
            },
            response_only=True
        )
    ],
    responses={
        200: OpenApiResponse(description="Token is valid."),
        400: OpenApiResponse(description="Missing, invalid or already-used token."),
    }
)

super_admin_view_schema = extend_schema_view(
    list=extend_schema(
        summary="List superadmins",
        description="Retrieve a list of all users with superadmin privileges.",
        responses={200: OpenApiResponse(description="List of superadmins")}
    ),
    retrieve=extend_schema(
        summary="Retrieve superadmin",
        description="Get detailed information about a specific superadmin.",
        responses={200: AdminUserDetailSerializer}
    )
)

super_admin_transfer_schema = extend_schema(
    methods=["POST"],
    operation_id="transfer_superadmin_privilege",
    summary="Transfer Superadmin Privilege",
    description=(
        "Transfer superadmin rights to another existing user (must not already be a superadmin). "
        "Current superadmin can either revoke their own access entirely or downgrade to a role."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "downgrade_to_role_id": {"type": "integer"},
                "revoke": {"type": "boolean"}
            },
            "required": ["email"]
        }
    },
    responses={
        200: OpenApiExample(
            "Successful Transfer",
            value={
                "message": "Superadmin privileges transferred to newadmin@example.com.",
                "error": False
            },
            status_codes=["200"]
        ),
        400: OpenApiExample(
            "Invalid request",
            value={"message": "Target user email is required.", "error": True},
            status_codes=["400"]
        ),
        404: OpenApiExample(
            "User not found",
            value={"message": "User with this email does not exist.", "error": True},
            status_codes=["404"]
        )
    },
)

super_admin_invite_schema = extend_schema(
        methods=["POST"],
        summary="Invite a Superadmin",
        description="Send an invitation email to promote a new superadmin by email.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "name": {"type": "string"}
                },
                "required": ["email"]
            }
        }
    )

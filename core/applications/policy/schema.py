# schema.py
from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from .views import *

# User endpoints schema extensions
extend_schema(
    tags=['User - Policy'],
    summary="Get About Us content",
    description="Retrieve the most recent About Us content. Read-only endpoint for regular users.",
)(UserAboutUsViewSet)

extend_schema(
    tags=['User - Policy'],
    summary="Get Privacy Policy",
    description="Retrieve the most recent Privacy Policy. Read-only endpoint for regular users.",
)(UserPrivacyPolicyViewSet)

extend_schema(
    tags=['User - Policy'],
    summary="Get Terms of Use",
    description="Retrieve the most recent Terms of Use. Read-only endpoint for regular users.",
)(UserTermsOfUseViewSet)

extend_schema(
    tags=['User - Partners'],
    summary="Get Partners",
    description="Retrieve the list of active partners. Read-only endpoint for regular users.",
    parameters=[
        OpenApiParameter(
            name='category',
            description='Filter partners by category (airline, stay, or car_rental)',
            required=False,
            type=str,
            examples=[
                OpenApiExample(
                    'Airline Partners',
                    value='airline',
                ),
                OpenApiExample(
                    'Stay Partners',
                    value='stay',
                ),
                OpenApiExample(
                    'Car Rental Partners',
                    value='car_rental',
                ),
            ]
        ),
    ]
)(UserPartnerViewSet)

# Admin endpoints schema extensions
extend_schema(
    tags=['Admin - Policy'],
    summary="Manage About Us content",
    description="Create, read, update, and delete About Us content. Restricted to admin users only.",
)(AdminAboutUsViewSet)

extend_schema(
    tags=['Admin - Policy'],
    summary="Manage Privacy Policy",
    description="Create, read, update, and delete Privacy Policy content. Restricted to admin users only.",
)(AdminPrivacyPolicyViewSet)

extend_schema(
    tags=['Admin - Policy'],
    summary="Manage Terms of Use",
    description="Create, read, update, and delete Terms of Use content. Restricted to admin users only.",
)(AdminTermsOfUseViewSet)

extend_schema(
    tags=['Admin - Partners'],
    summary="Manage Partner Categories",
    description="Create, read, update, and delete Partner Categories. Restricted to admin users only.",
    parameters=[
        OpenApiParameter(
            name='name',
            description='Filter by partner category name',
            required=False,
            type=str,
            examples=[
                OpenApiExample(
                    'Airline Partners',
                    value='airline',
                ),
                OpenApiExample(
                    'Stay Partners',
                    value='stay',
                ),
                OpenApiExample(
                    'Car Rental Partners',
                    value='car_rental',
                ),
            ]
        ),
    ]
)(AdminPartnerCategoryViewSet)

extend_schema(
    tags=['Admin - Partners'],
    summary="Manage Partners",
    description="Create, read, update, and delete Partners. Restricted to admin users only.",
    parameters=[
        OpenApiParameter(
            name='category',
            description='Filter partners by category',
            required=False,
            type=str,
            examples=[
                OpenApiExample(
                    'Airline Partners',
                    value='airline',
                ),
                OpenApiExample(
                    'Stay Partners',
                    value='stay',
                ),
                OpenApiExample(
                    'Car Rental Partners',
                    value='car_rental',
                ),
            ]
        ),
    ]
)(AdminPartnerViewSet)

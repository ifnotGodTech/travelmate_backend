from rest_framework import viewsets, permissions, status, mixins
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import AboutUs, PrivacyPolicy, TermsOfUse, PartnerCategory, Partner
from .serializers import (
    AboutUsSerializer,
    PrivacyPolicySerializer,
    TermsOfUseSerializer,
    PartnerCategorySerializer,
    PartnerCategoryDetailSerializer,
    PartnerSerializer
)


class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


# Admin ViewSets (full CRUD)
class AdminAboutUsViewSet(viewsets.ModelViewSet):
    """
    Manage About Us content.

    Create, read, update, and delete About Us content. Restricted to admin users only.
    """
    queryset = AboutUs.objects.all().order_by('-updated_at')
    serializer_class = AboutUsSerializer
    permission_classes = [IsAdminUser]

    def list(self, request):
        about_us = AboutUs.objects.order_by('-updated_at').first()
        if not about_us:
            about_us = AboutUs.objects.create(content="About Us content goes here.")

        serializer = self.get_serializer(about_us)
        return Response(serializer.data)


class AdminPrivacyPolicyViewSet(viewsets.ModelViewSet):
    """
    Manage Privacy Policy.

    Create, read, update, and delete Privacy Policy content. Restricted to admin users only.
    """
    queryset = PrivacyPolicy.objects.all().order_by('-last_updated')
    serializer_class = PrivacyPolicySerializer
    permission_classes = [IsAdminUser]

    def list(self, request):
        privacy_policy = PrivacyPolicy.objects.order_by('-last_updated').first()
        if not privacy_policy:
            privacy_policy = PrivacyPolicy.objects.create(content="Privacy Policy content goes here.")

        serializer = self.get_serializer(privacy_policy)
        return Response(serializer.data)


class AdminTermsOfUseViewSet(viewsets.ModelViewSet):
    """
    Manage Terms of Use.

    Create, read, update, and delete Terms of Use content. Restricted to admin users only.
    """
    queryset = TermsOfUse.objects.all().order_by('-last_updated')
    serializer_class = TermsOfUseSerializer
    permission_classes = [IsAdminUser]

    def list(self, request):
        terms_of_use = TermsOfUse.objects.order_by('-last_updated').first()
        if not terms_of_use:
            terms_of_use = TermsOfUse.objects.create(content="Terms of Use content goes here.")

        serializer = self.get_serializer(terms_of_use)
        return Response(serializer.data)


class AdminPartnerCategoryViewSet(viewsets.ModelViewSet):
    """
    Manage Partner Categories.

    Create, read, update, and delete Partner Categories. Restricted to admin users only.
    """
    queryset = PartnerCategory.objects.all()
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PartnerCategoryDetailSerializer
        return PartnerCategorySerializer

    def list(self, request):
        # Ensure all three categories exist
        categories = {
            'airline': 'Airline Partners',
            'stay': 'Stay Partners',
            'car_rental': 'Car Rental Partners'
        }

        for category_key, category_name in categories.items():
            PartnerCategory.objects.get_or_create(
                name=category_key,
                defaults={'description': f'Description for {category_name}'}
            )

        return super().list(request)


class AdminPartnerViewSet(viewsets.ModelViewSet):
    """
    Manage Partners.

    Create, read, update, and delete Partners. Restricted to admin users only.
    """
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = Partner.objects.all()
        category = self.request.query_params.get('category', None)
        if category is not None:
            queryset = queryset.filter(category__name=category)
        return queryset


# User ViewSets (read-only)
class UserAboutUsViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Get About Us content.

    Retrieve the most recent About Us content. Read-only endpoint for regular users.
    """
    queryset = AboutUs.objects.all().order_by('-updated_at')
    serializer_class = AboutUsSerializer

    def list(self, request):
        about_us = AboutUs.objects.order_by('-updated_at').first()
        if not about_us:
            about_us = AboutUs.objects.create(content="About Us content goes here.")

        serializer = self.get_serializer(about_us)
        return Response(serializer.data)


class UserPrivacyPolicyViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Get Privacy Policy.

    Retrieve the most recent Privacy Policy. Read-only endpoint for regular users.
    """
    queryset = PrivacyPolicy.objects.all().order_by('-last_updated')
    serializer_class = PrivacyPolicySerializer

    def list(self, request):
        privacy_policy = PrivacyPolicy.objects.order_by('-last_updated').first()
        if not privacy_policy:
            privacy_policy = PrivacyPolicy.objects.create(content="Privacy Policy content goes here.")

        serializer = self.get_serializer(privacy_policy)
        return Response(serializer.data)


class UserTermsOfUseViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Get Terms of Use.

    Retrieve the most recent Terms of Use. Read-only endpoint for regular users.
    """
    queryset = TermsOfUse.objects.all().order_by('-last_updated')
    serializer_class = TermsOfUseSerializer

    def list(self, request):
        terms_of_use = TermsOfUse.objects.order_by('-last_updated').first()
        if not terms_of_use:
            terms_of_use = TermsOfUse.objects.create(content="Terms of Use content goes here.")

        serializer = self.get_serializer(terms_of_use)
        return Response(serializer.data)


class UserPartnerViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Get Partners.

    Retrieve the list of active partners. Read-only endpoint for regular users.
    """
    queryset = Partner.objects.filter(is_active=True)
    serializer_class = PartnerSerializer

    def get_queryset(self):
        queryset = Partner.objects.filter(is_active=True)
        category = self.request.query_params.get('category', None)
        if category is not None:
            queryset = queryset.filter(category__name=category)
        return queryset

from rest_framework import viewsets, permissions, filters, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import F
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import FAQCategory, FAQ
from .serializers import FAQCategorySerializer, FAQSerializer


class IsAdminUser(permissions.BasePermission):
    """
    Permission to only allow admin users access.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff


# Read-only viewsets for regular users
@extend_schema_view(
    list=extend_schema(
        summary="List all FAQ categories",
        description="Returns a list of all available FAQ categories",
        tags=["FAQ User API"]
    ),
    retrieve=extend_schema(
        summary="Get a specific FAQ category",
        description="Returns details of a specific FAQ category including all associated FAQs",
        tags=["FAQ User API"]
    )
)
class FAQCategoryReadOnlyViewSet(mixins.ListModelMixin,
                                 mixins.RetrieveModelMixin,
                                 viewsets.GenericViewSet):
    queryset = FAQCategory.objects.all()
    serializer_class = FAQCategorySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['order', 'name']


@extend_schema_view(
    list=extend_schema(
        summary="List all FAQs",
        description="Returns a list of all active FAQs with optional category filtering",
        parameters=[
            OpenApiParameter(
                name="category",
                type=OpenApiTypes.STR,
                description="Filter FAQs by category name (e.g. FLIGHTS, STAYS, etc.)",
                required=False,
                examples=[
                    OpenApiExample(
                        "Flights example",
                        value="FLIGHTS"
                    ),
                    OpenApiExample(
                        "Stays example",
                        value="STAYS"
                    ),
                ]
            )
        ],
        tags=["FAQ User API"]
    ),
    retrieve=extend_schema(
        summary="Get a specific FAQ",
        description="Returns details of a specific FAQ",
        tags=["FAQ User API"]
    )
)
class FAQReadOnlyViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    queryset = FAQ.objects.filter(is_active=True)
    serializer_class = FAQSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['question', 'answer', 'category__name']
    ordering_fields = ['order', 'views', 'created_at', 'updated_at']

    def get_queryset(self):
        queryset = FAQ.objects.filter(is_active=True)

        # Filter by category if provided
        category = self.request.query_params.get('category', None)
        if category is not None:
            queryset = queryset.filter(category__name=category)

        return queryset

    @extend_schema(
        summary="Record a view",
        description="Increments the view counter for a specific FAQ",
        responses={200: {"type": "object", "properties": {"status": {"type": "string"}}}},
        tags=["FAQ User API"]
    )
    @action(detail=True, methods=['post'])
    def record_view(self, request, pk=None):
        """Endpoint to increment the view count for an FAQ"""
        faq = self.get_object()
        faq.increment_views()
        return Response({'status': 'view recorded'})


# Full CRUD viewsets for admin users
@extend_schema_view(
    list=extend_schema(
        summary="Admin: List all FAQ categories",
        description="Admin access to list all FAQ categories",
        tags=["FAQ Admin API"]
    ),
    retrieve=extend_schema(
        summary="Admin: Get a specific FAQ category",
        description="Admin access to get a specific FAQ category",
        tags=["FAQ Admin API"]
    ),
    create=extend_schema(
        summary="Admin: Create a new FAQ category",
        description="Admin access to create a new FAQ category",
        tags=["FAQ Admin API"]
    ),
    update=extend_schema(
        summary="Admin: Update a FAQ category",
        description="Admin access to update an existing FAQ category",
        tags=["FAQ Admin API"]
    ),
    partial_update=extend_schema(
        summary="Admin: Partially update a FAQ category",
        description="Admin access to partially update an existing FAQ category",
        tags=["FAQ Admin API"]
    ),
    destroy=extend_schema(
        summary="Admin: Delete a FAQ category",
        description="Admin access to delete an existing FAQ category",
        tags=["FAQ Admin API"]
    )
)
class FAQCategoryViewSet(viewsets.ModelViewSet):
    queryset = FAQCategory.objects.all()
    serializer_class = FAQCategorySerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['order', 'name']


@extend_schema_view(
    list=extend_schema(
        summary="Admin: List all FAQs",
        description="Admin access to list all FAQs including inactive ones",
        parameters=[
            OpenApiParameter(
                name="category",
                type=OpenApiTypes.STR,
                description="Filter FAQs by category name",
                required=False
            ),
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                description="Filter FAQs by active status",
                required=False
            )
        ],
        tags=["FAQ Admin API"]
    ),
    retrieve=extend_schema(
        summary="Admin: Get a specific FAQ",
        description="Admin access to get a specific FAQ",
        tags=["FAQ Admin API"]
    ),
    create=extend_schema(
        summary="Admin: Create a new FAQ",
        description="Admin access to create a new FAQ",
        tags=["FAQ Admin API"]
    ),
    update=extend_schema(
        summary="Admin: Update a FAQ",
        description="Admin access to update an existing FAQ",
        tags=["FAQ Admin API"]
    ),
    partial_update=extend_schema(
        summary="Admin: Partially update a FAQ",
        description="Admin access to partially update an existing FAQ",
        tags=["FAQ Admin API"]
    ),
    destroy=extend_schema(
        summary="Admin: Delete a FAQ",
        description="Admin access to delete an existing FAQ",
        tags=["FAQ Admin API"]
    )
)
class FAQViewSet(viewsets.ModelViewSet):
    queryset = FAQ.objects.all()  # Admin can see all FAQs including inactive ones
    serializer_class = FAQSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['question', 'answer', 'category__name']
    ordering_fields = ['order', 'views', 'created_at', 'updated_at']

    def get_queryset(self):
        queryset = FAQ.objects.all()

        # Filter by category if provided
        category = self.request.query_params.get('category', None)
        if category is not None:
            queryset = queryset.filter(category__name=category)

        # Filter by active status if provided
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        # Set the current user as the creator
        serializer.save(created_by=self.request.user)

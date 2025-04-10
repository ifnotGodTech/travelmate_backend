from rest_framework import viewsets, permissions, filters, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Max, F, Value, BooleanField
from django.db.models.functions import Coalesce
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatSessionDetailSerializer, ChatMessageSerializer


class IsAdminUser(permissions.BasePermission):
    """Permission to only allow admin users access."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff


class IsSessionOwnerOrAdmin(permissions.BasePermission):
    """Permission to only allow the session owner or admin to access."""
    def has_object_permission(self, request, view, obj):
        # Admin can access any session
        if request.user.is_staff:
            return True
        # User can only access their own sessions
        return obj.user == request.user


# User Chat Session ViewSet
@extend_schema_view(
    list=extend_schema(
        summary="List user's chat sessions",
        description="Returns a list of all chat sessions for the authenticated user",
        tags=["Chat User API"]
    ),
    retrieve=extend_schema(
        summary="Get a specific chat session",
        description="Returns details of a specific chat session including all messages",
        tags=["Chat User API"]
    ),
    create=extend_schema(
        summary="Create a new chat session",
        description="Creates a new support chat session",
        tags=["Chat User API"]
    )
)
class UserChatSessionViewSet(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.CreateModelMixin,
                          viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['updated_at', 'created_at', 'status']
    ordering = ['-updated_at']

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChatSessionDetailSerializer
        return ChatSessionSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status='WAITING')

    @extend_schema(
        summary="Mark messages as read",
        description="Marks all admin messages in the session as read",
        responses={200: {"type": "object", "properties": {"status": {"type": "string"}}}},
        tags=["Chat User API"]
    )
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Endpoint for users to mark admin messages as read"""
        session = self.get_object()
        # Mark admin messages as read
        ChatMessage.objects.filter(
            session=session,
            sender__is_staff=True,
            is_read=False
        ).update(is_read=True)
        return Response({'status': 'messages marked as read'})


# Admin Chat Session ViewSet
@extend_schema_view(
    list=extend_schema(
        summary="Admin: List all chat sessions",
        description="Admin access to list all support chat sessions",
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                description="Filter chats by status (OPEN, CLOSED, WAITING, ACTIVE)",
                required=False
            ),
            OpenApiParameter(
                name="assigned",
                type=OpenApiTypes.BOOL,
                description="Filter by assignment status (true=assigned to me, false=unassigned)",
                required=False
            )
        ],
        tags=["Chat Admin API"]
    ),
    retrieve=extend_schema(
        summary="Admin: Get a specific chat session",
        description="Admin access to get a specific chat session with all messages",
        tags=["Chat Admin API"]
    ),
    update=extend_schema(
        summary="Admin: Update a chat session",
        description="Admin access to update a chat session (assign, change status)",
        tags=["Chat Admin API"]
    ),
    partial_update=extend_schema(
        summary="Admin: Partially update a chat session",
        description="Admin access to partially update a chat session",
        tags=["Chat Admin API"]
    )
)
class AdminChatSessionViewSet(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin,
                          viewsets.GenericViewSet):
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'user__first_name', 'user__email']
    ordering_fields = ['updated_at', 'created_at', 'status']
    ordering = ['-updated_at']

    def get_queryset(self):
        queryset = ChatSession.objects.all()

        # Filter by status if provided
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Filter by assignment status if provided
        assigned_param = self.request.query_params.get('assigned', None)
        if assigned_param is not None:
            if assigned_param.lower() == 'true':
                queryset = queryset.filter(assigned_admin=self.request.user)
            elif assigned_param.lower() == 'false':
                queryset = queryset.filter(assigned_admin__isnull=True)

        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChatSessionDetailSerializer
        return ChatSessionSerializer

    @extend_schema(
        summary="Admin: Assign chat session",
        description="Assign a chat session to the current admin",
        responses={200: ChatSessionSerializer},
        tags=["Chat Admin API"]
    )
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        session = self.get_object()
        session.assigned_admin = request.user
        session.status = 'ACTIVE'
        session.save()
        serializer = self.get_serializer(session)
        return Response(serializer.data)

    @extend_schema(
        summary="Admin: Close chat session",
        description="Close a chat session",
        responses={200: ChatSessionSerializer},
        tags=["Chat Admin API"]
    )
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        session = self.get_object()
        session.status = 'CLOSED'
        session.save()
        serializer = self.get_serializer(session)
        return Response(serializer.data)

    @extend_schema(
        summary="Admin: Mark messages as read",
        description="Marks all user messages in the session as read",
        responses={200: {"type": "object", "properties": {"status": {"type": "string"}}}},
        tags=["Chat Admin API"]
    )
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Endpoint for admins to mark user messages as read"""
        session = self.get_object()
        # Mark user messages as read
        ChatMessage.objects.filter(
            session=session,
            sender__is_staff=False,
            is_read=False
        ).update(is_read=True)
        return Response({'status': 'messages marked as read'})


# Chat Message ViewSet for both users and admins
@extend_schema_view(
    create=extend_schema(
        summary="Send a chat message",
        description="Sends a new message in a chat session",
        tags=["Chat API"]
    )
)
class ChatMessageViewSet(mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return ChatMessage.objects.all()
        return ChatMessage.objects.filter(session__user=self.request.user)

    def perform_create(self, serializer):
        session = serializer.validated_data['session']
        # Validate the user has access to this session
        if not self.request.user.is_staff and session.user != self.request.user:
            raise permissions.PermissionDenied("You don't have permission to send messages in this chat.")

        # If admin sending first message to a waiting session, update status
        if self.request.user.is_staff and session.status == 'WAITING':
            session.status = 'ACTIVE'
            session.assigned_admin = self.request.user
            session.save()

        # If session is closed, reopen it
        elif session.status == 'CLOSED':
            session.status = 'ACTIVE' if self.request.user.is_staff else 'WAITING'
            session.save()

        # Save the message with the current user as sender
        serializer.save(sender=self.request.user)

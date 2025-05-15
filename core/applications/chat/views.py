from rest_framework import viewsets, permissions, filters, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Max, F, Value, BooleanField
from django.db.models.functions import Coalesce
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from django.http import HttpResponse
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from .models import ChatSession, ChatMessage, ChatAttachment
from .serializers import ChatSessionSerializer, ChatSessionDetailSerializer, ChatMessageSerializer, UserSerializer, ChatAttachmentSerializer
from core.applications.users.models import User
from rest_framework.parsers import MultiPartParser, FormParser


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
        description="Returns details of a specific chat session including all messages and attachments",
        tags=["Chat User API"]
    ),
    create=extend_schema(
        summary="Create a new chat session",
        description="Creates a new support chat session. The session will be in WAITING status until an admin responds.",
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

    @extend_schema(
        summary="Export chat session as PDF",
        description="Generate and download a PDF document containing the chat session details and messages",
        responses={
            200: OpenApiResponse(
                description="PDF file containing chat session details",
                response=OpenApiTypes.BINARY
            )
        },
        tags=["Chat User API"]
    )
    @action(detail=True, methods=['get'])
    def export_pdf(self, request, pk=None):
        """
        Export chat session details and messages as a PDF document.
        """
        session = self.get_object()

        # Create a BytesIO buffer to store the PDF
        buffer = BytesIO()

        # Create the PDF document
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30
        )
        elements.append(Paragraph(f"Chat Session #{session.id}: {session.title}", title_style))
        elements.append(Spacer(1, 12))

        # Add session details
        details_style = styles['Normal']
        details = [
            f"Status: {session.status}",
            f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Last Updated: {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}"
        ]

        if session.assigned_admin:
            details.append(f"Assigned Admin: {session.assigned_admin.email}")

        for detail in details:
            elements.append(Paragraph(detail, details_style))
            elements.append(Spacer(1, 6))

        elements.append(Spacer(1, 20))

        # Add messages
        elements.append(Paragraph("Messages:", styles['Heading2']))
        messages = session.messages.all().order_by('created_at')

        if messages:
            for message in messages:
                elements.append(Spacer(1, 12))
                sender_type = "Support" if message.sender.is_staff else "User"
                elements.append(Paragraph(
                    f"From: {sender_type} ({message.sender.email}) - {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                    styles['Heading3']
                ))
                elements.append(Paragraph(message.content, details_style))
        else:
            elements.append(Paragraph("No messages found.", details_style))

        # Build the PDF
        doc.build(elements)

        # Get the value of the BytesIO buffer
        pdf = buffer.getvalue()
        buffer.close()

        # Create the HTTP response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="chat_session_{session.id}.pdf"'
        response.write(pdf)

        return response

    @extend_schema(
        summary="Delete chat session",
        description="Deletes a chat session and all its messages",
        responses={
            204: OpenApiResponse(description="Chat session successfully deleted"),
            404: OpenApiResponse(description="Chat session not found"),
            403: OpenApiResponse(description="Not authorized to delete this chat session")
        },
        tags=["Chat User API"]
    )
    @action(detail=True, methods=['delete'])
    def delete_session(self, request, pk=None):
        """Endpoint for users to delete their chat session"""
        session = self.get_object()
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Admin Chat Session ViewSet
@extend_schema_view(
    list=extend_schema(
        summary="Admin: List all chat sessions",
        description="Admin access to list all support chat sessions. Any admin can view and respond to any session.",
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                description="Filter chats by status (OPEN, CLOSED, WAITING, ACTIVE)",
                required=False
            )
        ],
        tags=["Chat Admin API"]
    ),
    retrieve=extend_schema(
        summary="Admin: Get a specific chat session",
        description="Admin access to get a specific chat session with all messages and attachments",
        tags=["Chat Admin API"]
    ),
    update=extend_schema(
        summary="Admin: Update a chat session",
        description="Admin access to update a chat session status",
        tags=["Chat Admin API"]
    ),
    partial_update=extend_schema(
        summary="Admin: Partially update a chat session",
        description="Admin access to partially update a chat session status",
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

        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChatSessionDetailSerializer
        return ChatSessionSerializer

    @extend_schema(
        summary="Admin: Close chat session",
        description="Close a chat session. This prevents further messages until reopened.",
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

    @extend_schema(
        summary="Admin: Export chat session as PDF",
        description="Generate and download a PDF document containing the chat session details and messages",
        responses={
            200: OpenApiResponse(
                description="PDF file containing chat session details",
                response=OpenApiTypes.BINARY
            )
        },
        tags=["Chat Admin API"]
    )
    @action(detail=True, methods=['get'])
    def export_pdf(self, request, pk=None):
        """
        Export chat session details and messages as a PDF document.
        """
        session = self.get_object()

        # Create a BytesIO buffer to store the PDF
        buffer = BytesIO()

        # Create the PDF document
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30
        )
        elements.append(Paragraph(f"Chat Session #{session.id}: {session.title}", title_style))
        elements.append(Spacer(1, 12))

        # Add session details
        details_style = styles['Normal']
        details = [
            f"User: {session.user.email}",
            f"Status: {session.status}",
            f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Last Updated: {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}"
        ]

        for detail in details:
            elements.append(Paragraph(detail, details_style))
            elements.append(Spacer(1, 6))

        elements.append(Spacer(1, 20))

        # Add messages
        elements.append(Paragraph("Messages:", styles['Heading2']))
        messages = session.messages.all().order_by('created_at')

        if messages:
            for message in messages:
                elements.append(Spacer(1, 12))
                sender_type = "Support" if message.sender.is_staff else "User"
                elements.append(Paragraph(
                    f"From: {sender_type} ({message.sender.email}) - {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                    styles['Heading3']
                ))
                elements.append(Paragraph(message.content, details_style))
        else:
            elements.append(Paragraph("No messages found.", details_style))

        # Build the PDF
        doc.build(elements)

        # Get the value of the BytesIO buffer
        pdf = buffer.getvalue()
        buffer.close()

        # Create the HTTP response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="chat_session_{session.id}.pdf"'
        response.write(pdf)

        return response

    @extend_schema(
        summary="Admin: Delete chat session",
        description="Admin endpoint to delete a chat session and all its messages",
        responses={
            204: OpenApiResponse(description="Chat session successfully deleted"),
            404: OpenApiResponse(description="Chat session not found"),
            403: OpenApiResponse(description="Not authorized to delete this chat session")
        },
        tags=["Chat Admin API"]
    )
    @action(detail=True, methods=['delete'])
    def delete_session(self, request, pk=None):
        """Endpoint for admins to delete a chat session"""
        session = self.get_object()
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Chat Message ViewSet for both users and admins
@extend_schema_view(
    create=extend_schema(
        summary="Send a chat message",
        description="""Sends a new message in a chat session with optional file attachments.

        For users:
        - Can only send messages to their own sessions
        - If session is closed, it will be reopened in WAITING status

        For admins:
        - Can send messages to any session
        - If session is in WAITING status, it will be changed to ACTIVE
        - If session is closed, it will be reopened in ACTIVE status

        File attachments:
        - Multiple files can be attached to a single message
        - Files are stored in chat_attachments/session_id/message_id/
        """,
        tags=["Chat API"]
    )
)
class ChatMessageViewSet(mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatMessageSerializer
    parser_classes = (MultiPartParser, FormParser)

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
            session.save()

        # If session is closed, reopen it
        elif session.status == 'CLOSED':
            session.status = 'ACTIVE' if self.request.user.is_staff else 'WAITING'
            session.save()

        # Save the message with the current user as sender
        message = serializer.save(sender=self.request.user)

        # Handle file attachments
        files = self.request.FILES.getlist('attachments')
        for file in files:
            ChatAttachment.objects.create(
                message=message,
                file=file,
                file_name=file.name,
                file_type=file.content_type,
                file_size=file.size
            )

        # Update read status
        if self.request.user.is_staff:
            ChatMessage.objects.filter(session=session, sender__is_staff=False, is_read=False).update(is_read=True)
        else:
            ChatMessage.objects.filter(session=session, sender__is_staff=True, is_read=False).update(is_read=True)


# Admin List ViewSet
@extend_schema_view(
    list=extend_schema(
        summary="List all admin users",
        description="Returns a list of all admin users in the system",
        tags=["Chat API"]
    )
)
class AdminListViewSet(mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.filter(is_staff=True).order_by('email')

# core/applications/tickets/views.py
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.mail import send_mail
from django.db import models
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
from .models import Ticket, Message, EscalationLevel
from .serializers import (
    TicketSerializer, MessageSerializer, TicketCreateSerializer,
    TicketEscalateSerializer, MessageCreateSerializer,
    EscalationLevelSerializer, TicketEscalatedStatsSerializer,
    TicketResolutionStatsSerializer,
    CategoryStatsSerializer,
    EscalationLevelStatsSerializer
)
from drf_spectacular.utils import extend_schema_view
from .schema import (
    ticket_list_schema, ticket_create_schema, ticket_retrieve_schema,
    ticket_update_schema, ticket_partial_update_schema, ticket_destroy_schema,
    ticket_escalate_schema, ticket_resolve_schema, ticket_pending_schema,
    ticket_resolved_schema, message_list_schema, message_create_schema,
    message_retrieve_schema, escalation_level_list_schema,
    escalation_level_create_schema, message_update_schema,
    message_partial_update_schema, message_destroy_schema,
    message_list_all_schema, admin_ticket_list_schema,
    admin_ticket_create_schema, admin_ticket_retrieve_schema,
    admin_ticket_update_schema, admin_ticket_partial_update_schema,
    admin_ticket_destroy_schema, escalation_level_retrieve_schema,
    escalation_level_update_schema, escalation_level_partial_update_schema,
    escalation_level_destroy_schema, admin_ticket_escalated_stats_schema,
    admin_ticket_resolution_stats_schema, admin_ticket_all_stats_schema,
    admin_ticket_category_stats_schema, admin_ticket_pending_schema,
    admin_ticket_escalation_level_stats_schema, admin_ticket_average_response_time_schema,
)

class IsAdminOrOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # For Ticket objects
        if hasattr(obj, 'user'):
            return request.user.is_staff or obj.user == request.user
        # For Message objects
        if hasattr(obj, 'ticket'):
            return request.user.is_staff or obj.ticket.user == request.user
        return False

@extend_schema_view(
    list=escalation_level_list_schema,
    create=escalation_level_create_schema,
    retrieve=escalation_level_retrieve_schema,
    update=escalation_level_update_schema,
    partial_update=escalation_level_partial_update_schema,
    destroy=escalation_level_destroy_schema
)
class EscalationLevelViewSet(viewsets.ModelViewSet):
    queryset = EscalationLevel.objects.all()
    serializer_class = EscalationLevelSerializer
    permission_classes = [permissions.IsAdminUser]

@extend_schema_view(
    list=admin_ticket_list_schema,
    create=admin_ticket_create_schema,
    retrieve=admin_ticket_retrieve_schema,
    update=admin_ticket_update_schema,
    partial_update=admin_ticket_partial_update_schema,
    destroy=admin_ticket_destroy_schema,
    escalate=ticket_escalate_schema,
    resolve=ticket_resolve_schema,
    escalated_stats=admin_ticket_escalated_stats_schema,
    resolution_stats=admin_ticket_resolution_stats_schema,
    category_stats=admin_ticket_category_stats_schema,
    escalation_level_stats=admin_ticket_escalation_level_stats_schema,
    pending=admin_ticket_pending_schema,
    average_response_time=admin_ticket_average_response_time_schema,
    all_stats = admin_ticket_all_stats_schema,
)
class AdminTicketViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = TicketSerializer
    queryset = Ticket.objects.all()

    @action(detail=False, methods=['get'])
    def all_stats(self, request):
        """
        Returns all ticket statistics in a single payload.
        Query params: days, weeks, months, years (all optional, integer)
        Example: /api/admin/tickets/all_stats/?days=7
        """
        from django.db.models import Count

        # Get query params
        days = int(request.query_params.get('days', 0))
        weeks = int(request.query_params.get('weeks', 0))
        months = int(request.query_params.get('months', 0))
        years = int(request.query_params.get('years', 0))

        now = timezone.now()
        delta = timedelta()
        if days:
            delta += timedelta(days=days)
        if weeks:
            delta += timedelta(weeks=weeks)
        if months:
            delta += timedelta(days=30 * months)
        if years:
            delta += timedelta(days=365 * years)

        # Initialize response data
        response_data = {}

        # 1. Escalated Stats
        escalated_queryset = self.queryset.filter(escalated=True, status='pending')
        if delta:
            since = now - delta
            escalated_queryset = escalated_queryset.filter(created_at__gte=since)

        escalated_serializer = self.get_serializer(escalated_queryset, many=True)
        response_data['escalated_issues'] = {
            'count': escalated_queryset.count(),
            'tickets': escalated_serializer.data
        }

        # 2. Resolution Stats
        resolved_queryset = self.queryset.filter(status='resolved')
        if delta:
            since = now - delta
            resolved_queryset = resolved_queryset.filter(updated_at__gte=since)

        resolved_serializer = self.get_serializer(resolved_queryset, many=True)
        response_data['resolved_tickets'] = {
            'count': resolved_queryset.count(),
            'tickets': resolved_serializer.data
        }

        # 3. Category Stats
        category_counts = self.queryset.values('category').annotate(
            total=Count('id'),
            pending=Count('id', filter=models.Q(status='pending')),
            resolved=Count('id', filter=models.Q(status='resolved')),
            escalated=Count('id', filter=models.Q(escalated=True))
        )
        response_data['categories'] = category_counts

        # 4. Escalation Level Stats
        escalation_stats = self.queryset.filter(
            escalated=True
        ).values(
            'escalation_level__name'
        ).annotate(
            total=Count('id'),
            pending=Count('id', filter=models.Q(status='pending')),
            resolved=Count('id', filter=models.Q(status='resolved'))
        )
        response_data['escalation_levels'] = escalation_stats

        # 5. Pending Tickets
        pending_queryset = self.queryset.filter(status='pending')
        if delta:
            since = now - delta
            pending_queryset = pending_queryset.filter(created_at__gte=since)

        pending_serializer = self.get_serializer(pending_queryset, many=True)
        response_data['open_tickets'] = {
            'count': pending_queryset.count(),
            'tickets': pending_serializer.data
        }

        # 6. Average Response Time
        tickets = self.queryset.all()
        response_times = []

        for ticket in tickets:
            # Find the first admin message for this ticket
            first_admin_message = (
                Message.objects
                .filter(ticket=ticket, sender__is_staff=True)
                .order_by('timestamp')
                .first()
            )
            if first_admin_message:
                response_time = (first_admin_message.timestamp - ticket.created_at).total_seconds()
                response_times.append(response_time)

        if response_times:
            avg_seconds = sum(response_times) / len(response_times)
        else:
            avg_seconds = 0

        response_data['average_response_time'] = {
            "seconds": avg_seconds,
            "human_readable": str(timedelta(seconds=int(avg_seconds)))
        }

        return Response(response_data)

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        ticket = self.get_object()

        if not request.user.is_staff:
            return Response(
                {"detail": "Only admins can escalate tickets."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if escalation_level is in the request data
        if 'escalation_level' not in request.data:
            return Response(
                {"detail": "escalation_level field is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if 'escalation_reason' not in request.data:
            return Response(
                {"detail": "escalation_reason field is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Use the specific serializer for escalation
        serializer = TicketEscalateSerializer(ticket, data=request.data, partial=True)

        if serializer.is_valid():
            # Save the updated ticket with escalation info
            ticket = serializer.save(escalated=True)

            # Verify escalation level was set
            if not ticket.escalation_level:
                return Response(
                    {"detail": "Failed to set escalation level. Please check the escalation_level ID."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Import the Profile model
            from core.applications.users.models import Profile

            # Get the user's profile to access first_name and last_name
            try:
                user_profile = Profile.objects.get(user=ticket.user)
                user_first_name = user_profile.first_name
                user_last_name = user_profile.last_name
            except Profile.DoesNotExist:
                user_first_name = "Unknown"
                user_last_name = "Customer"

            # Email body content
            subject_prefix = getattr(settings, 'EMAIL_SUBJECT_PREFIX', '[Ticket System] ')
            subject = f'{subject_prefix}Ticket #{ticket.id} Escalated: {ticket.title}'

            message = f"""
            Ticket has been escalated.

            Ticket ID: {ticket.id}
            Title: {ticket.title}
            Category: {ticket.category}
            Customer: {user_first_name} {user_last_name}
            Email: {ticket.user.email}

            Escalation Level: {ticket.escalation_level.name}
            Reason: {ticket.escalation_reason}
            """

            # Add response time if available
            if ticket.escalation_response_time:
                message += f"\nResponse Time: {dict(ticket.RESPONSE_TIME_CHOICES)[ticket.escalation_response_time]}"

            # Add note if available
            if ticket.escalation_note:
                message += f"\nNote: {ticket.escalation_note}"

            # Send email notification
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_email = ticket.escalation_level.email

            try:
                send_mail(
                    subject,
                    message,
                    from_email,
                    [recipient_email],
                    fail_silently=False,
                )
                return Response(
                    {"detail": "Ticket escalated successfully and notification sent."},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Email notification failed: {str(e)}")

                return Response(
                    {"detail": f"Ticket escalated but email notification failed: {str(e)}"},
                    status=status.HTTP_200_OK
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        ticket = self.get_object()

        if not request.user.is_staff:
            return Response(
                {"detail": "Only admins can resolve tickets."},
                status=status.HTTP_403_FORBIDDEN
            )

        ticket.status = 'resolved'
        ticket.save()

        return Response(
            {"detail": "Ticket resolved successfully."},
            status=status.HTTP_200_OK
        )

@extend_schema_view(
    list=ticket_list_schema,
    create=ticket_create_schema,
    retrieve=ticket_retrieve_schema,
    update=ticket_update_schema,
    partial_update=ticket_partial_update_schema,
    destroy=ticket_destroy_schema,
    pending=ticket_pending_schema,
    resolved=ticket_resolved_schema
)
class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Ticket.objects.all()
        return Ticket.objects.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return TicketCreateSerializer
        elif self.action == 'escalate':
            return TicketEscalateSerializer
        return TicketSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        queryset = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def resolved(self, request):
        queryset = self.get_queryset().filter(status='resolved')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

@extend_schema_view(
    get=message_list_schema,
    post=message_create_schema
)
class TicketMessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        ticket_id = self.kwargs.get('ticket_pk')
        ticket = Ticket.objects.get(id=ticket_id)

        # Check permissions
        if not (self.request.user.is_staff or ticket.user == self.request.user):
            return Message.objects.none()

        return Message.objects.filter(ticket_id=ticket_id)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MessageCreateSerializer
        return MessageSerializer

    def perform_create(self, serializer):
        ticket_id = self.kwargs.get('ticket_pk')
        ticket = Ticket.objects.get(id=ticket_id)

        # Check if this user has access to this ticket
        if not (self.request.user.is_staff or ticket.user == self.request.user):
            self.permission_denied(self.request, message="You don't have access to this ticket")

        # Check if the ticket is resolved
        if ticket.status == 'resolved':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot add messages to a resolved ticket. Please create a new ticket.")


        serializer.save(
            ticket_id=ticket_id,
            sender=self.request.user
        )

@extend_schema_view(
    list=message_list_all_schema,
    retrieve=message_retrieve_schema,
    update=message_update_schema,
    partial_update=message_partial_update_schema,
    destroy=message_destroy_schema
)
class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.all()

    def get_object(self):
        obj = super().get_object()
        self.check_object_permissions(self.request, obj)
        return obj

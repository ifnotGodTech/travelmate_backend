# core/applications/tickets/schema.py
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from .serializers import (
    TicketSerializer, MessageSerializer, TicketCreateSerializer,
    TicketEscalateSerializer, MessageCreateSerializer,
    EscalationLevelSerializer, EscalationReasonSerializer
)

# Ticket ViewSet schema definitions
ticket_list_schema = extend_schema(
    summary="List all tickets",
    description="Returns a list of all tickets. For regular users, only their own tickets are returned. For admins, all tickets are returned.",
    responses={
        200: TicketSerializer(many=True),
        401: OpenApiResponse(description="Authentication credentials were not provided.")
    },
    examples=[
        OpenApiExample(
            name="Regular User Response",
            value=[{
                "id": 1,
                "title": "Login Issue",
                "description": "I cannot log into my account",
                "category": "account",
                "status": "pending",
                "priority": "medium",
                "created_at": "2025-04-05T10:30:00Z",
                "updated_at": "2025-04-05T10:30:00Z",
                "escalated": False
            }]
        )
    ],
    tags=["User Tickets"]
)

ticket_create_schema = extend_schema(
    summary="Create a new ticket",
    description="Creates a new support ticket. The user is automatically set to the authenticated user.",
    request=TicketCreateSerializer,
    responses={
        201: TicketSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided.")
    },
    examples=[
        OpenApiExample(
            name="Create Ticket Request",
            value={
                "title": "Payment Failed",
                "description": "My payment is being declined",
                "category": "billing",
                "priority": "high"
            },
            request_only=True
        ),
        OpenApiExample(
            name="Create Ticket Response",
            value={
                "id": 2,
                "title": "Payment Failed",
                "description": "My payment is being declined",
                "category": "billing",
                "status": "pending",
                "priority": "high",
                "created_at": "2025-04-07T15:22:17Z",
                "updated_at": "2025-04-07T15:22:17Z",
                "escalated": False
            },
            response_only=True
        )
    ],
    tags=["User Tickets"]
)

ticket_retrieve_schema = extend_schema(
    summary="Retrieve a specific ticket",
    description="Returns detailed information about a specific ticket including its status and metadata.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the ticket."
        )
    ],
    responses={
        200: TicketSerializer,
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this ticket."),
        404: OpenApiResponse(description="Ticket not found.")
    },
    tags=["User Tickets"]
)

ticket_update_schema = extend_schema(
    summary="Update a ticket",
    description="Update details of an existing ticket. Regular users can only update their own tickets.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the ticket."
        )
    ],
    request=TicketSerializer,
    responses={
        200: TicketSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to modify this ticket."),
        404: OpenApiResponse(description="Ticket not found.")
    },
    tags=["User Tickets"]
)

ticket_partial_update_schema = extend_schema(
    summary="Partially update a ticket",
    description="Update specific fields of an existing ticket. Regular users can only update their own tickets.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the ticket."
        )
    ],
    request=TicketSerializer,
    responses={
        200: TicketSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to modify this ticket."),
        404: OpenApiResponse(description="Ticket not found.")
    },
    tags=["User Tickets"]
)

ticket_destroy_schema = extend_schema(
    summary="Delete a ticket",
    description="Delete a ticket. Regular users can only delete their own tickets.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the ticket."
        )
    ],
    responses={
        204: OpenApiResponse(description="Ticket deleted successfully."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to delete this ticket."),
        404: OpenApiResponse(description="Ticket not found.")
    },
    tags=["User Tickets"]
)

ticket_escalate_schema = extend_schema(
    summary="Escalate a ticket",
    description="Escalate a ticket to a higher support level. This action is restricted to admins only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the ticket."
        )
    ],
    request=TicketEscalateSerializer,
    responses={
        200: OpenApiResponse(description="Ticket escalated successfully."),
        400: OpenApiResponse(description="Invalid input for escalation. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="Only admins can escalate tickets."),
        404: OpenApiResponse(description="Ticket not found.")
    },
    examples=[
        OpenApiExample(
            name="Escalate Request",
            value={
                "escalation_level": 2,
                "escalation_reason": 3,
                "escalation_note": "Customer has requested expedited resolution",
                "escalation_response_time": "24h"
            },
            request_only=True
        )
    ],
    tags=["Admin Ticket Management"]
)

ticket_resolve_schema = extend_schema(
    summary="Resolve a ticket",
    description="Mark a ticket as resolved. This action is restricted to admins only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the ticket."
        )
    ],
    responses={
        200: OpenApiResponse(description="Ticket resolved successfully."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="Only admins can resolve tickets."),
        404: OpenApiResponse(description="Ticket not found.")
    },
    tags=["Admin Ticket Management"]
)

ticket_pending_schema = extend_schema(
    summary="List pending tickets",
    description="Returns a list of all pending tickets. For regular users, only their own pending tickets are returned.",
    responses={
        200: TicketSerializer(many=True),
        401: OpenApiResponse(description="Authentication credentials were not provided.")
    },
    tags=["User Tickets"]
)

ticket_resolved_schema = extend_schema(
    summary="List resolved tickets",
    description="Returns a list of all resolved tickets. For regular users, only their own resolved tickets are returned.",
    responses={
        200: TicketSerializer(many=True),
        401: OpenApiResponse(description="Authentication credentials were not provided.")
    },
    tags=["User Tickets"]
)

# Messages ViewSet schema definitions
message_list_schema = extend_schema(
    summary="List all messages for a ticket",
    description="Returns all messages for a specific ticket. Users can only access messages for their own tickets.",
    parameters=[
        OpenApiParameter(
            name="ticket_pk",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the ticket."
        ),
    ],
    responses={
        200: MessageSerializer(many=True),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this ticket."),
        404: OpenApiResponse(description="Ticket not found.")
    },
    examples=[
        OpenApiExample(
            name="Messages List Response",
            value=[
                {
                    "id": 1,
                    "ticket": 1,
                    "sender_id": 2,
                    "sender_name": "John Support",
                    "content": "How can I help you with your login issue?",
                    "created_at": "2025-04-05T10:35:00Z",
                    "is_staff": True
                },
                {
                    "id": 2,
                    "ticket": 1,
                    "sender_id": 5,
                    "sender_name": "Jane Customer",
                    "content": "I keep getting an 'invalid password' error even though I'm sure it's correct.",
                    "created_at": "2025-04-05T10:36:00Z",
                    "is_staff": False
                }
            ],
            response_only=True
        )
    ],
    tags=["Ticket Messages"]
)

message_create_schema = extend_schema(
    summary="Create a new message",
    description="Add a new message to a ticket. Users can only add messages to their own tickets.",
    parameters=[
        OpenApiParameter(
            name="ticket_pk",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the ticket."
        ),
    ],
    request=MessageCreateSerializer,
    responses={
        201: MessageSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this ticket."),
        404: OpenApiResponse(description="Ticket not found.")
    },
    examples=[
        OpenApiExample(
            name="Create Message Request",
            value={
                "content": "I've tried resetting my password but I'm still having issues.",
                "attachment": None  # Can be a file
            },
            request_only=True
        ),
        OpenApiExample(
            name="Create Message Response",
            value={
                "id": 3,
                "ticket": 1,
                "sender_id": 5,
                "sender_name": "Jane Customer",
                "content": "I've tried resetting my password but I'm still having issues.",
                "attachment": "http://example.com/media/ticket_attachments/document.pdf",
                "created_at": "2025-04-07T15:40:22Z",
                "is_staff": False
            },
            response_only=True
        )
    ],
    tags=["Ticket Messages"]
)

message_retrieve_schema = extend_schema(
    summary="Retrieve a specific message",
    description="Returns details of a specific message. Users can only access messages from their own tickets.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the message."
        )
    ],
    responses={
        200: MessageSerializer,
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this message."),
        404: OpenApiResponse(description="Message not found.")
    },
    tags=["Ticket Messages"]
)

# Escalation Level schema definitions
escalation_level_list_schema = extend_schema(
    summary="List all escalation levels",
    description="Returns all available escalation levels. This endpoint is restricted to admin users only.",
    responses={
        200: EscalationLevelSerializer(many=True),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view.")
    },
    examples=[
        OpenApiExample(
            name="Escalation Levels Response",
            value=[
                {
                    "id": 1,
                    "name": "Level 1 Support",
                    "description": "First line customer support",
                    "email": "support-l1@example.com"
                },
                {
                    "id": 2,
                    "name": "Level 2 Support",
                    "description": "Technical support specialists",
                    "email": "support-l2@example.com"
                },
                {
                    "id": 3,
                    "name": "Engineering",
                    "description": "Development team for bug fixes",
                    "email": "engineering@example.com"
                }
            ],
            response_only=True
        )
    ],
    tags=["Escalation Management"]
)

escalation_level_create_schema = extend_schema(
    summary="Create a new escalation level",
    description="Create a new escalation level. This endpoint is restricted to admin users only.",
    request=EscalationLevelSerializer,
    responses={
        201: EscalationLevelSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view.")
    },
    examples=[
        OpenApiExample(
            name="Create Escalation Level Request",
            value={
                "name": "Executive Support",
                "description": "Escalations requiring executive attention",
                "email": "executive-support@example.com"
            },
            request_only=True
        )
    ],
    tags=["Escalation Management"]
)

# Escalation Reason schema definitions
escalation_reason_list_schema = extend_schema(
    summary="List all escalation reasons",
    description="Returns all available escalation reasons. This endpoint is restricted to admin users only.",
    responses={
        200: EscalationReasonSerializer(many=True),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view.")
    },
    examples=[
        OpenApiExample(
            name="Escalation Reasons Response",
            value=[
                {
                    "id": 1,
                    "reason": "Technical complexity",
                    "description": "Issue requires specialized technical knowledge"
                },
                {
                    "id": 2,
                    "reason": "Customer request",
                    "description": "Customer has specifically requested escalation"
                },
                {
                    "id": 3,
                    "reason": "SLA breach imminent",
                    "description": "Ticket approaching SLA breach time"
                }
            ],
            response_only=True
        )
    ],
    tags=["Escalation Management"]
)

escalation_reason_create_schema = extend_schema(
    summary="Create a new escalation reason",
    description="Create a new escalation reason. This endpoint is restricted to admin users only.",
    request=EscalationReasonSerializer,
    responses={
        201: EscalationReasonSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view.")
    },
    examples=[
        OpenApiExample(
            name="Create Escalation Reason Request",
            value={
                "reason": "Legal implications",
                "description": "Issue involves potential legal or compliance concerns"
            },
            request_only=True
        )
    ],
    tags=["Escalation Management"]
)

# Add these to your schema.py file

# For EscalationLevel
escalation_level_retrieve_schema = extend_schema(
    summary="Retrieve an escalation level",
    description="Retrieve details for a specific escalation level. Admin access only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the escalation level."
        )
    ],
    responses={
        200: EscalationLevelSerializer,
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view."),
        404: OpenApiResponse(description="Escalation level not found.")
    },
    tags=["Escalation Management"]
)

escalation_level_update_schema = extend_schema(
    summary="Update an escalation level",
    description="Update an existing escalation level. Admin access only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the escalation level."
        )
    ],
    request=EscalationLevelSerializer,
    responses={
        200: EscalationLevelSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view."),
        404: OpenApiResponse(description="Escalation level not found.")
    },
    tags=["Escalation Management"]
)

escalation_level_partial_update_schema = extend_schema(
    summary="Partially update an escalation level",
    description="Partially update an existing escalation level. Admin access only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the escalation level."
        )
    ],
    request=EscalationLevelSerializer,
    responses={
        200: EscalationLevelSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view."),
        404: OpenApiResponse(description="Escalation level not found.")
    },
    tags=["Escalation Management"]
)

escalation_level_destroy_schema = extend_schema(
    summary="Delete an escalation level",
    description="Delete an existing escalation level. Admin access only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the escalation level."
        )
    ],
    responses={
        204: OpenApiResponse(description="Escalation level deleted successfully."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view."),
        404: OpenApiResponse(description="Escalation level not found.")
    },
    tags=["Escalation Management"]
)

# For EscalationReason
escalation_reason_retrieve_schema = extend_schema(
    summary="Retrieve an escalation reason",
    description="Retrieve details for a specific escalation reason. Admin access only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the escalation reason."
        )
    ],
    responses={
        200: EscalationReasonSerializer,
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view."),
        404: OpenApiResponse(description="Escalation reason not found.")
    },
    tags=["Escalation Management"]
)

escalation_reason_update_schema = extend_schema(
    summary="Update an escalation reason",
    description="Update an existing escalation reason. Admin access only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the escalation reason."
        )
    ],
    request=EscalationReasonSerializer,
    responses={
        200: EscalationReasonSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view."),
        404: OpenApiResponse(description="Escalation reason not found.")
    },
    tags=["Escalation Management"]
)

escalation_reason_partial_update_schema = extend_schema(
    summary="Partially update an escalation reason",
    description="Partially update an existing escalation reason. Admin access only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the escalation reason."
        )
    ],
    request=EscalationReasonSerializer,
    responses={
        200: EscalationReasonSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view."),
        404: OpenApiResponse(description="Escalation reason not found.")
    },
    tags=["Escalation Management"]
)

escalation_reason_destroy_schema = extend_schema(
    summary="Delete an escalation reason",
    description="Delete an existing escalation reason. Admin access only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the escalation reason."
        )
    ],
    responses={
        204: OpenApiResponse(description="Escalation reason deleted successfully."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view."),
        404: OpenApiResponse(description="Escalation reason not found.")
    },
    tags=["Escalation Management"]
)

# For AdminTicketViewSet
admin_ticket_list_schema = extend_schema(
    summary="Admin: List all tickets",
    description="Returns a list of all tickets in the system. Admin access only.",
    responses={
        200: TicketSerializer(many=True),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view.")
    },
    tags=["Admin Ticket Management"]
)

admin_ticket_create_schema = extend_schema(
    summary="Admin: Create a new ticket",
    description="Creates a new ticket. Admin access only.",
    request=TicketCreateSerializer,
    responses={
        201: TicketSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view.")
    },
    tags=["Admin Ticket Management"]
)

admin_ticket_retrieve_schema = extend_schema(
    summary="Admin: Retrieve a specific ticket",
    description="Returns detailed information about a specific ticket. Admin access only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the ticket."
        )
    ],
    responses={
        200: TicketSerializer,
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view."),
        404: OpenApiResponse(description="Ticket not found.")
    },
    tags=["Admin Ticket Management"]
)

admin_ticket_update_schema = extend_schema(
    summary="Admin: Update a ticket",
    description="Update details of an existing ticket. Admin access only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the ticket."
        )
    ],
    request=TicketSerializer,
    responses={
        200: TicketSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view."),
        404: OpenApiResponse(description="Ticket not found.")
    },
    tags=["Admin Ticket Management"]
)

admin_ticket_partial_update_schema = extend_schema(
    summary="Admin: Partially update a ticket",
    description="Partially update an existing ticket. Admin access only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the ticket."
        )
    ],
    request=TicketSerializer,
    responses={
        200: TicketSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view."),
        404: OpenApiResponse(description="Ticket not found.")
    },
    tags=["Admin Ticket Management"]
)

admin_ticket_destroy_schema = extend_schema(
    summary="Admin: Delete a ticket",
    description="Delete an existing ticket. Admin access only.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the ticket."
        )
    ],
    responses={
        204: OpenApiResponse(description="Ticket deleted successfully."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view."),
        404: OpenApiResponse(description="Ticket not found.")
    },
    tags=["Admin Ticket Management"]
)

# Admin Ticket Statistics schema definitions

admin_ticket_escalated_stats_schema = extend_schema(
    summary="Admin: Get escalated tickets statistics",
    description=(
        "Returns statistics and details about unresolved escalated tickets. "
        "Supports filtering by days, weeks, months, and years via query parameters. "
        "Example: /api/admin/tickets/escalated_stats/?days=2"
    ),
    parameters=[
        OpenApiParameter("days", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of days to look back"),
        OpenApiParameter("weeks", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of weeks to look back"),
        OpenApiParameter("months", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of months to look back"),
        OpenApiParameter("years", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of years to look back"),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Escalated tickets statistics and details",
            examples=[
                OpenApiExample(
                    name="Escalated Stats Response",
                    value={
                        "unresolved_escalated": {
                            "count": 5,
                            "tickets": [
                                {
                                    "id": 1,
                                    "title": "Payment Issue",
                                    "category": "Flight",
                                    "description": "Payment not processed",
                                    "status": "pending",
                                    "escalated": True,
                                    "created_at": "2025-04-18T10:30:00Z",
                                    "escalation_level": {
                                        "id": 2,
                                        "name": "Level 2 Support"
                                    },
                                    "escalation_reason": {
                                        "id": 1,
                                        "reason": "Technical complexity"
                                    }
                                }
                            ]
                        }
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view.")
    },
    tags=["Admin Ticket Statistics"]
)

admin_ticket_resolution_stats_schema = extend_schema(
    summary="Admin: Get ticket resolution statistics",
    description=(
        "Returns statistics and details about resolved tickets. "
        "Supports filtering by days, weeks, months, and years via query parameters. "
        "Example: /api/admin/tickets/resolution_stats/?months=1"
    ),
    parameters=[
        OpenApiParameter("days", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of days to look back"),
        OpenApiParameter("weeks", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of weeks to look back"),
        OpenApiParameter("months", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of months to look back"),
        OpenApiParameter("years", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of years to look back"),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Ticket resolution statistics and details",
            examples=[
                OpenApiExample(
                    name="Resolution Stats Response",
                    value={
                        "resolved_tickets": {
                            "count": 10,
                            "tickets": [
                                {
                                    "id": 1,
                                    "title": "Booking Confirmation",
                                    "category": "Hotel",
                                    "description": "Need booking confirmation",
                                    "status": "resolved",
                                    "created_at": "2025-04-18T10:30:00Z",
                                    "updated_at": "2025-04-18T11:30:00Z"
                                }
                            ]
                        }
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view.")
    },
    tags=["Admin Ticket Statistics"]
)

admin_ticket_pending_schema = extend_schema(
    summary="Admin: List pending tickets",
    description=(
        "Returns all tickets with status 'pending', with optional time-based filtering. "
        "Supports filtering by days, weeks, months, and years via query parameters. "
        "Example: /api/admin/tickets/pending/?days=7"
    ),
    parameters=[
        OpenApiParameter("days", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of days to look back"),
        OpenApiParameter("weeks", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of weeks to look back"),
        OpenApiParameter("months", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of months to look back"),
        OpenApiParameter("years", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of years to look back"),
    ],
    responses={
        200: TicketSerializer(many=True),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view.")
    },
    tags=["Admin Ticket Management"]
)

admin_ticket_average_response_time_schema = extend_schema(
    summary="Admin: Get average admin response time",
    description="Returns the average admin response time for tickets (in seconds and human-readable format).",
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Average admin response time",
            examples=[
                OpenApiExample(
                    name="Average Response Time",
                    value={
                        "average_response_time_seconds": 3600,
                        "average_response_time_human": "1:00:00"
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view.")
    },
    tags=["Admin Ticket Statistics"]
)

admin_ticket_category_stats_schema = extend_schema(
    summary="Admin: Get ticket category statistics",
    description="Returns statistics about tickets grouped by category.",
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Ticket category statistics",
            examples=[
                OpenApiExample(
                    name="Category Stats Response",
                    value={
                        "categories": [
                            {
                                "category": "Flight",
                                "total": 150,
                                "pending": 45,
                                "resolved": 105,
                                "escalated": 20
                            },
                            {
                                "category": "Hotel",
                                "total": 100,
                                "pending": 30,
                                "resolved": 70,
                                "escalated": 15
                            }
                        ]
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view.")
    },
    tags=["Admin Ticket Statistics"]
)

admin_ticket_escalation_level_stats_schema = extend_schema(
    summary="Admin: Get escalation level statistics",
    description="Returns statistics about tickets grouped by escalation level.",
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Escalation level statistics",
            examples=[
                OpenApiExample(
                    name="Escalation Level Stats Response",
                    value={
                        "escalation_levels": [
                            {
                                "escalation_level__name": "Level 1",
                                "total": 50,
                                "pending": 20,
                                "resolved": 30
                            },
                            {
                                "escalation_level__name": "Level 2",
                                "total": 30,
                                "pending": 10,
                                "resolved": 20
                            }
                        ]
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view.")
    },
    tags=["Admin Ticket Statistics"]
)

admin_ticket_all_stats_schema = extend_schema(
    summary="Admin: Get comprehensive ticket statistics",
    description=(
        "Returns all ticket statistics in a single payload including escalated tickets, "
        "resolved tickets, category statistics, escalation level statistics, pending tickets, "
        "and average response time statistics. "
        "Supports filtering by days, weeks, months, and years via query parameters. "
        "Example: /api/admin/tickets/all_stats/?days=7"
    ),
    parameters=[
        OpenApiParameter("days", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of days to look back"),
        OpenApiParameter("weeks", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of weeks to look back"),
        OpenApiParameter("months", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of months to look back"),
        OpenApiParameter("years", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of years to look back"),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Comprehensive ticket statistics",
            examples=[
                OpenApiExample(
                    name="All Stats Response",
                    value={
                        "unresolved_escalated": {
                            "count": 5,
                            "tickets": [
                                {
                                    "id": 1,
                                    "title": "Payment Issue",
                                    "category": "Flight",
                                    "description": "Payment not processed",
                                    "status": "pending",
                                    "escalated": True,
                                    "created_at": "2025-04-18T10:30:00Z",
                                    "escalation_level": {
                                        "id": 2,
                                        "name": "Level 2 Support"
                                    },
                                    "escalation_reason": {
                                        "id": 1,
                                        "reason": "Technical complexity"
                                    }
                                }
                            ]
                        },
                        "resolved_tickets": {
                            "count": 10,
                            "tickets": [
                                {
                                    "id": 2,
                                    "title": "Booking Confirmation",
                                    "category": "Hotel",
                                    "description": "Need booking confirmation",
                                    "status": "resolved",
                                    "created_at": "2025-04-18T10:30:00Z",
                                    "updated_at": "2025-04-18T11:30:00Z"
                                }
                            ]
                        },
                        "categories": [
                            {
                                "category": "Flight",
                                "total": 150,
                                "pending": 45,
                                "resolved": 105,
                                "escalated": 20
                            },
                            {
                                "category": "Hotel",
                                "total": 100,
                                "pending": 30,
                                "resolved": 70,
                                "escalated": 15
                            }
                        ],
                        "escalation_levels": [
                            {
                                "escalation_level__name": "Level 1",
                                "total": 50,
                                "pending": 20,
                                "resolved": 30
                            },
                            {
                                "escalation_level__name": "Level 2",
                                "total": 30,
                                "pending": 10,
                                "resolved": 20
                            }
                        ],
                        "pending_tickets": {
                            "count": 75,
                            "tickets": [
                                {
                                    "id": 3,
                                    "title": "Refund Request",
                                    "category": "Flight",
                                    "description": "Need refund for canceled flight",
                                    "status": "pending",
                                    "created_at": "2025-04-18T14:30:00Z"
                                }
                            ]
                        },
                        "average_response_time": {
                            "seconds": 3600,
                            "human_readable": "1:00:00"
                        }
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to access this view.")
    },
    tags=["Admin Ticket Statistics"]
)

# Add these schema definitions
message_update_schema = extend_schema(
    summary="Update a message",
    description="Update an existing message. Users can only update their own messages.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the message."
        )
    ],
    request=MessageSerializer,
    responses={
        200: MessageSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to modify this message."),
        404: OpenApiResponse(description="Message not found.")
    },
    tags=["Ticket Messages"]
)

message_partial_update_schema = extend_schema(
    summary="Partially update a message",
    description="Partially update an existing message. Users can only update their own messages.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the message."
        )
    ],
    request=MessageSerializer,
    responses={
        200: MessageSerializer,
        400: OpenApiResponse(description="Invalid input. See error details."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to modify this message."),
        404: OpenApiResponse(description="Message not found.")
    },
    tags=["Ticket Messages"]
)

message_destroy_schema = extend_schema(
    summary="Delete a message",
    description="Delete an existing message. Users can only delete their own messages.",
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying the message."
        )
    ],
    responses={
        204: OpenApiResponse(description="Message deleted successfully."),
        401: OpenApiResponse(description="Authentication credentials were not provided."),
        403: OpenApiResponse(description="You do not have permission to delete this message."),
        404: OpenApiResponse(description="Message not found.")
    },
    tags=["Ticket Messages"]
)

message_list_all_schema = extend_schema(
    summary="List all messages",
    description="Returns a list of all messages the user has access to.",
    responses={
        200: MessageSerializer(many=True),
        401: OpenApiResponse(description="Authentication credentials were not provided.")
    },
    tags=["Ticket Messages"]
)

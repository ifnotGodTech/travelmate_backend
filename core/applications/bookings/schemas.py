from django.utils.decorators import method_decorator
from drf_spectacular.utils import (
    extend_schema, OpenApiParameter, OpenApiExample,
    OpenApiResponse, inline_serializer, extend_schema_view
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers

from core.applications.bookings.serializers import BookingHistorySerializer
from core.applications.cars.serializers import CarBookingSerializer, PaymentSerializer
from core.applications.flights.serializers import FlightBookingSerializer


# Common response serializers
booking_not_found_response = OpenApiResponse(
    description="Booking not found",
    response=inline_serializer(
        name="BookingNotFoundError",
        fields={"error": serializers.CharField()}
    )
)

invalid_request_response = OpenApiResponse(
    description="Invalid request parameters",
    response=inline_serializer(
        name="InvalidRequestError",
        fields={"error": serializers.CharField()}
    )
)

# Unified booking list response serializer
unified_booking_list_serializer = inline_serializer(
    name="UnifiedBookingListResponse",
    fields={
        "id": serializers.IntegerField(),
        "created_at": serializers.DateTimeField(),
        "status": serializers.CharField(),
        "user": serializers.CharField(),
        "email": serializers.EmailField(),
        "total_amount": serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True),
        "booking_type": serializers.CharField(),
        "specific_id": serializers.IntegerField(allow_null=True),
        "details": serializers.DictField(),
    }
)

# Car booking detail response
car_booking_detail_serializer = inline_serializer(
    name="CarBookingDetailResponse",
    fields={
        **{field_name: field for field_name, field in CarBookingSerializer().fields.items()},
        "user": serializers.DictField(),
        "payments": serializers.ListField(child=serializers.DictField()),
        "car": serializers.DictField(),
        "status_history": serializers.ListField(child=serializers.DictField()),
        "booking_type": serializers.CharField(),
    }
)

# Flight booking detail response
flight_booking_detail_serializer = inline_serializer(
    name="FlightBookingDetailResponse",
    fields={
        **{field_name: field for field_name, field in FlightBookingSerializer().fields.items()},
        "user": serializers.DictField(),
        "flights": serializers.ListField(child=serializers.DictField()),
        "passengers": serializers.ListField(child=serializers.DictField()),
        "booking_type": serializers.CharField(),
    }
)

# Cancellation response schemas
cancellation_success_serializer = inline_serializer(
    name="CancellationSuccessResponse",
    fields={
        "message": serializers.CharField(),
    }
)

cancellation_with_refund_serializer = inline_serializer(
    name="CancellationWithRefundResponse",
    fields={
        "message": serializers.CharField(),
        "refund_details": serializers.DictField(),
    }
)

cancellation_partial_failure_serializer = inline_serializer(
    name="CancellationPartialFailureResponse",
    fields={
        "message": serializers.CharField(),
        "refund_error": serializers.CharField(),
    }
)

# Update response schema
update_success_serializer = inline_serializer(
    name="UpdateSuccessResponse",
    fields={
        "message": serializers.CharField(),
        "updated_fields": serializers.ListField(child=serializers.CharField()),
    }
)


# Schema extensions for UnifiedBookingAdminViewSet
unified_booking_schema = {
    'list': extend_schema(
        summary="List all bookings",
        description="List all bookings with filtering options for date range and booking type",
        parameters=[
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                description="Filter bookings created on or after this date (YYYY-MM-DD)",
                required=False
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                description="Filter bookings created on or before this date (YYYY-MM-DD)",
                required=False
            ),
            OpenApiParameter(
                name="type",
                type=OpenApiTypes.STR,
                description="Filter by booking type: 'car' or 'flight'",
                required=False,
                enum=["car", "flight"]
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                description="Filter by booking status",
                required=False,
                examples=[
                    OpenApiExample(
                        "Confirmed",
                        value="CONFIRMED"
                    ),
                    OpenApiExample(
                        "Cancelled",
                        value="CANCELLED"
                    ),
                    OpenApiExample(
                        "Pending",
                        value="PENDING"
                    ),
                ]
            )
        ],
        responses={
            200: OpenApiResponse(
                description="List of bookings",
                response=unified_booking_list_serializer,
                examples=[
                    OpenApiExample(
                        "Mixed Bookings Example",
                        value=[
                            {
                                "id": 123,
                                "created_at": "2023-10-15T14:30:00Z",
                                "status": "CONFIRMED",
                                "user": "John Doe",
                                "email": "john@example.com",
                                "total_amount": 149.99,
                                "booking_type": "car",
                                "specific_id": 456,
                                "details": {
                                    "pickup_date": "2023-11-01",
                                    "dropoff_date": "2023-11-05",
                                    "car_model": "Toyota Corolla"
                                }
                            },
                            {
                                "id": 124,
                                "created_at": "2023-10-16T10:15:00Z",
                                "status": "CONFIRMED",
                                "user": "Jane Smith",
                                "email": "jane@example.com",
                                "total_amount": 523.50,
                                "booking_type": "flight",
                                "specific_id": 789,
                                "details": {
                                    "departure": "JFK",
                                    "arrival": "LAX",
                                    "departure_date": "2023-12-15",
                                    "flight_number": "AA123"
                                }
                            }
                        ]
                    )
                ]
            )
        },
        tags=["Admin Bookings"]
    ),

    'retrieve': extend_schema(
        summary="Get detailed booking info",
        description="Get detailed booking information for any booking type (car or flight)",
        responses={
            200: OpenApiResponse(
                description="Booking details",
                response={
                    "application/json": {
                        "oneOf": [
                            {"$ref": "#/components/schemas/CarBookingDetailResponse"},
                            {"$ref": "#/components/schemas/FlightBookingDetailResponse"}
                        ]
                    }
                },
                examples=[
                    OpenApiExample(
                        "Car Booking Example",
                        value={
                            "id": 456,
                            "booking_id": 123,
                            "pickup_date": "2023-11-01",
                            "dropoff_date": "2023-11-05",
                            "pickup_time": "10:00",
                            "dropoff_time": "14:00",
                            "user": {
                                "first_name": "John",
                                "last_name": "Doe",
                                "email": "john@example.com",
                                "phone_number": "+1234567890"
                            },
                            "payments": [
                                {
                                    "id": 321,
                                    "amount": 149.99,
                                    "status": "COMPLETED",
                                    "payment_date": "2023-10-15T14:35:22Z"
                                }
                            ],
                            "car": {
                                "model": "Toyota Corolla",
                                "passenger_capacity": 5,
                                "company": "Hertz"
                            },
                            "status_history": [
                                {
                                    "status": "CONFIRMED",
                                    "changed_at": "2023-10-15T14:35:30Z",
                                    "notes": "Booking confirmed after payment"
                                }
                            ],
                            "booking_type": "car"
                        }
                    )
                ]
            ),
            404: booking_not_found_response,
            400: invalid_request_response
        },
        tags=["Admin Bookings"]
    ),

    'update_booking': extend_schema(
        summary="Update booking details",
        description="Update any booking type (car or flight)",
        request={
            "application/json": {
                "oneOf": [
                    {
                        "title": "Car Booking Update",
                        "type": "object",
                        "properties": {
                            "pickup_date": {"type": "string", "format": "date"},
                            "pickup_time": {"type": "string"},
                            "dropoff_date": {"type": "string", "format": "date"},
                            "dropoff_time": {"type": "string"},
                            "passengers": {"type": "integer"},
                            "child_seats": {"type": "integer"},
                            "special_requests": {"type": "string"}
                        }
                    },
                    {
                        "title": "Flight Booking Update",
                        "type": "object",
                        "required": ["flight_id"],
                        "properties": {
                            "flight_id": {"type": "integer"},
                            "departure_datetime": {"type": "string", "format": "date-time"},
                            "arrival_datetime": {"type": "string", "format": "date-time"},
                            "flight_number": {"type": "string"}
                        }
                    }
                ]
            }
        },
        responses={
            200: update_success_serializer,
            400: invalid_request_response,
            404: booking_not_found_response
        },
        tags=["Admin Bookings"]
    ),

    'cancel_booking': extend_schema(
        summary="Cancel booking",
        description="Cancel any booking type with optional refund",
        request=inline_serializer(
            name="CancellationRequest",
            fields={
                "process_refund": serializers.BooleanField(default=False, required=False),
                "refund_amount": serializers.DecimalField(max_digits=10, decimal_places=2, required=False),
                "reason": serializers.CharField(required=False)
            }
        ),
        responses={
            200: OpenApiResponse(
                description="Booking cancelled successfully",
                response={
                    "application/json": {
                        "oneOf": [
                            {"$ref": "#/components/schemas/CancellationSuccessResponse"},
                            {"$ref": "#/components/schemas/CancellationWithRefundResponse"}
                        ]
                    }
                }
            ),
            207: cancellation_partial_failure_serializer,
            400: invalid_request_response,
            404: booking_not_found_response
        },
        tags=["Admin Bookings"]
    ),

    'history': extend_schema(
        summary="Get booking history",
        description="Get the full history trail for any booking type",
        responses={
            200: BookingHistorySerializer(many=True),
            404: booking_not_found_response
        },
        tags=["Admin Bookings"]
    )
}


def apply_unified_booking_schema(cls):
    """
    Decorator to apply all schema definitions to the UnifiedBookingAdminViewSet
    """
    return extend_schema_view(**unified_booking_schema)(cls)

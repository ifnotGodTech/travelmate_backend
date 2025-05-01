from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample,
    OpenApiResponse, OpenApiTypes
)
from drf_spectacular.plumbing import build_parameter_type
from rest_framework import serializers
from .models import FlightBooking, Flight, Passenger, PassengerBooking
from .serializers import (
    FlightBookingSerializer,
    FlightBookingInputSerializer,
    PaymentInputSerializer,
    FlightSearchSerializer,
    MultiCityFlightSearchSerializer
)
from rest_framework.decorators import action

# Custom serializers for schema documentation only
class FlightOfferResponseSerializer(serializers.Serializer):
    """Serializer for flight offer search results"""
    id = serializers.CharField(help_text="Unique identifier for this flight offer")
    source = serializers.CharField(help_text="Source of the flight data")
    instantTicketingRequired = serializers.BooleanField(help_text="Whether instant ticketing is required")
    nonHomogeneous = serializers.BooleanField(help_text="Whether the fare is non-homogeneous")
    oneWay = serializers.BooleanField(help_text="Whether this is a one-way flight")
    lastTicketingDate = serializers.DateField(help_text="Last date for ticketing")
    numberOfBookableSeats = serializers.IntegerField(help_text="Number of bookable seats")
    itineraries = serializers.JSONField(help_text="Flight itineraries details")
    price = serializers.JSONField(help_text="Price information")
    pricingOptions = serializers.JSONField(help_text="Pricing options")
    validatingAirlineCodes = serializers.ListField(
        child=serializers.CharField(),
        help_text="Codes of validating airlines"
    )
    travelerPricings = serializers.JSONField(help_text="Pricing information for travelers")

class FlightOffersSearchResponseSerializer(serializers.Serializer):
    """Top level response for flight search results"""
    data = serializers.ListField(
        child=FlightOfferResponseSerializer(),
        help_text="List of flight offers"
    )
    dictionaries = serializers.JSONField(help_text="Reference data dictionaries")
    meta = serializers.JSONField(help_text="Metadata about the search results")

class AirportSearchResponseSerializer(serializers.Serializer):
    """Response for airport search results"""
    data = serializers.ListField(
        child=serializers.JSONField(),
        help_text="List of airport information"
    )

class PaymentIntentResponseSerializer(serializers.Serializer):
    """Response for payment intent creation"""
    payment_intent_id = serializers.CharField(help_text="ID of the created payment intent")
    client_secret = serializers.CharField(help_text="Client secret for the payment intent")
    payment_split = serializers.JSONField(help_text="Payment amount split details")

class PaymentErrorResponseSerializer(serializers.Serializer):
    """Response for payment processing errors"""
    error = serializers.CharField(help_text="Error message")

class BookingCreationResponseSerializer(serializers.Serializer):
    """Response for booking creation"""
    id = serializers.IntegerField(help_text="ID of the created booking")
    booking_reference = serializers.CharField(help_text="Booking reference number")
    booking_type = serializers.CharField(help_text="Type of booking (ONE_WAY, ROUND_TRIP, MULTI_CITY)")
    base_flight_cost = serializers.DecimalField(max_digits=10, decimal_places=2, help_text="Base cost of flight")
    service_fee = serializers.DecimalField(max_digits=10, decimal_places=2, help_text="Service fee")
    currency = serializers.CharField(help_text="Currency code")
    # Include additional fields as needed to match your FlightBookingSerializer

# Serializer for upsell flight offer request
class UpsellFlightOfferRequestSerializer(serializers.Serializer):
    """Serializer for upsell flight offer request"""
    flight_offer_id = serializers.CharField(
        help_text="ID of the flight offer to fetch upsell options for, obtained from a previous flight search"
    )

# Define schema extensions for FlightBookingViewSet
flight_booking_schema = extend_schema_view(
    list=extend_schema(
        summary="List user's flight bookings",
        description="Returns a list of flight bookings for the current user",
        responses={200: FlightBookingSerializer(many=True)}
    ),
    retrieve=extend_schema(
        summary="Get flight booking details",
        description="Returns details for a specific flight booking",
        responses={200: FlightBookingSerializer},
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="A unique integer value identifying this flight booking"
            )
        ]
    ),
    create_booking=extend_schema(
        summary="Create new flight booking",
        description="""
        Create a new flight booking with passenger details, flight offer IDs, and an optional upsell offer ID.
        The flight offers must have been previously retrieved and cached from a flight search.
        If an upsell_offer_id is provided, the booking will use the upsell offer instead of the original flight offer.
        """,
        request=FlightBookingInputSerializer,
        responses={
            201: OpenApiResponse(
                response=BookingCreationResponseSerializer,
                description="Flight booking created successfully"
            ),
            400: OpenApiResponse(
                description="Invalid input data"
            )
        },
        examples=[
            OpenApiExample(
                "Booking Example with Upsell",
                value={
                    "flight_offer_ids": ["1"],
                    "upsell_offer_id": "upsell456",
                    "passengers": [
                        {
                            "title": "MR",
                            "first_name": "John",
                            "last_name": "Doe",
                            "email": "john.doe@example.com",
                            "date_of_birth": "1980-01-01",
                            "gender": "M",
                            "passport_number": "US123456",
                            "passport_expiry": "2030-01-01",
                            "nationality": "US",
                            "phone": "+12345678900",
                            "address_line1": "123 Main St",
                            "city": "New York",
                            "country": "US",
                            "postal_code": "10001"
                        }
                    ],
                    "booking_type": "ONE_WAY"
                },
                request_only=True
            ),
            OpenApiExample(
                "Booking Example without Upsell",
                value={
                    "flight_offer_ids": ["1", "2"],
                    "passengers": [
                        {
                            "title": "MR",
                            "first_name": "John",
                            "last_name": "Doe",
                            "email": "john.doe@example.com",
                            "date_of_birth": "1980-01-01",
                            "gender": "M",
                            "passport_number": "US123456",
                            "passport_expiry": "2030-01-01",
                            "nationality": "US",
                            "phone": "+12345678900"
                        }
                    ],
                    "booking_type": "ROUND_TRIP"
                },
                request_only=True
            )
        ]
    ),
    process_payment=extend_schema(
        summary="Process payment for a booking",
        description="Process payment for a pending booking using Stripe payment method",
        request=PaymentInputSerializer,
        responses={
            200: OpenApiResponse(
                response=PaymentIntentResponseSerializer,
                description="Payment processed successfully"
            ),
            400: OpenApiResponse(
                response=PaymentErrorResponseSerializer,
                description="Payment processing failed"
            )
        },
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="""A unique integer value identifying the flight booking. Note that this is the booking ID, not the flight offer ID. The booking ID is generated when the booking is created."""
            )
        ],
        examples=[
            OpenApiExample(
                "Payment Example",
                value={"payment_method_id": "pm_card_visa"},
                request_only=True
            )
        ]
    ),
    cancel_booking=extend_schema(
        summary="Cancel a booking",
        description="Cancel an existing flight booking",
        request=None,
        responses={
            200: OpenApiResponse(
                response=FlightBookingSerializer,
                description="Booking cancelled successfully"
            ),
            400: OpenApiResponse(
                description="Booking cannot be cancelled"
            )
        },
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="A unique integer value identifying the flight booking to cancel"
            )
        ]
    )
)

# Define schema extensions for FlightSearchViewSet
flight_search_schema = extend_schema_view(
    one_way=extend_schema(
        summary="Search for one-way flights",
        description="Search for one-way flights using the Amadeus API",
        request=FlightSearchSerializer,
        responses={
            200: OpenApiResponse(
                response=FlightOffersSearchResponseSerializer,
                description="Flight search results"
            )
        },
        examples=[
            OpenApiExample(
                "One-way Search Example",
                value={
                    "origin": "JFK",
                    "destination": "LAX",
                    "departure_date": "2025-05-01",
                    "adults": 1,
                    "children": 1,
                    "infants": 1,
                    "travel_class": "ECONOMY",
                    "non_stop": False,
                    "currency": "USD"
                },
                request_only=True
            )
        ]
    ),
    round_trip=extend_schema(
        summary="Search for round-trip flights",
        description="Search for round-trip flights using the Amadeus API",
        request=FlightSearchSerializer,
        responses={
            200: OpenApiResponse(
                response=FlightOffersSearchResponseSerializer,
                description="Flight search results"
            )
        },
        examples=[
            OpenApiExample(
                "Round-trip Search Example",
                value={
                    "origin": "JFK",
                    "destination": "LAX",
                    "departure_date": "2025-05-01",
                    "return_date": "2025-05-08",
                    "adults": 1,
                    "children": 1,
                    "infants": 1,
                    "travel_class": "ECONOMY",
                    "non_stop": False,
                    "currency": "USD"
                },
                request_only=True
            )
        ]
    ),
    multi_city=extend_schema(
        summary="Search for multi-city flights",
        description="Search for multi-city flights using the Amadeus API",
        request=MultiCityFlightSearchSerializer,
        responses={
            200: OpenApiResponse(
                response=FlightOffersSearchResponseSerializer,
                description="Flight search results"
            )
        },
        examples=[
            OpenApiExample(
                "Multi-city Search Example",
                value={
                    "segments": [
                        {
                            "origin": "JFK",
                            "destination": "LAX",
                            "departure_date": "2025-05-01"
                        },
                        {
                            "origin": "LAX",
                            "destination": "SFO",
                            "departure_date": "2025-05-05"
                        },
                        {
                            "origin": "SFO",
                            "destination": "JFK",
                            "departure_date": "2025-05-10"
                        }
                    ],
                    "adults": 1,
                    "travel_class": "ECONOMY",
                    "children": 1,
                    "infants": 1,
                    "currency": "USD"
                },
                request_only=True
            )
        ]
    ),
    price_flight_offers=extend_schema(
        summary="Price flight offers",
        description="Get accurate pricing for flight offers",
        responses={
            200: OpenApiResponse(
                response=FlightOffersSearchResponseSerializer,
                description="Priced flight offers"
            )
        },
        request=serializers.Serializer
    ),
    search_airports=extend_schema(
        summary="Search for airports",
        description="Search for airports by keyword, with optional filters",
        responses={
            200: OpenApiResponse(
                response=AirportSearchResponseSerializer,
                description="Airport search results"
            )
        },
        parameters=[
            OpenApiParameter(
                name="keyword",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search keyword for airport name or city"
            ),
            OpenApiParameter(
                name="subType",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by subtype (e.g., AIRPORT, CITY)",
                required=False
            ),
            OpenApiParameter(
                name="countryCode",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by country code (e.g., US)",
                required=False
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Maximum number of results to return",
                required=False
            )
        ]
    ),
    flight_details=extend_schema(
        summary="Get flight details",
        description="Get details for a specific flight offer",
        responses={
            200: OpenApiResponse(
                response=FlightOfferResponseSerializer,
                description="Flight details"
            ),
            404: OpenApiResponse(
                description="Flight not found"
            )
        },
        parameters=[
            OpenApiParameter(
                name="flight_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="ID of the flight offer which has been previously retrieved from search",
            )
        ]
    ),
    upsell_flight_offer=extend_schema(
        summary="Get upsell flight offers",
        description="""
        Retrieve upsell options (e.g., upgraded cabin classes or branded fares) for a specific flight offer.
        The flight offer must have been previously retrieved and cached from a flight search.
        """,
        request=UpsellFlightOfferRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=FlightOffersSearchResponseSerializer,
                description="Upsell flight offer results"
            ),
            400: OpenApiResponse(
                description="Invalid flight offer ID or flight offer not found"
            )
        },
        examples=[
            OpenApiExample(
                "Upsell Flight Offer Example",
                value={
                    "flight_offer_id": "offer123"
                },
                request_only=True
            )
        ]
    )
)

# Additional serializers for tagged operation groups
class FlightServiceMetaSerializer(serializers.Serializer):
    """Serializer to document the flight service API"""
    version = serializers.CharField(default="1.0.0")
    name = serializers.CharField(default="Flight Booking API")
    description = serializers.CharField(
        default="API for searching, booking, and managing flight reservations"
    )

# Custom schema operation tags
FLIGHT_TAGS = ["Flight Booking", "Flight Search", "Payment Processing"]

# # Schema customization function
# def get_spectacular_settings():
#     return {
#         'TITLE': 'Flight Booking API',
#         'DESCRIPTION': 'API for searching, booking, and managing flight reservations',
#         'VERSION': '1.0.0',
#         'SERVE_INCLUDE_SCHEMA': False,

#         # Customizations
#         'SCHEMA_PATH_PREFIX': r'/api/v[0-9]',
#         'COMPONENT_SPLIT_REQUEST': True,
#         'TAGS': [
#             {'name': 'Flight Booking', 'description': 'Operations related to flight bookings'},
#             {'name': 'Flight Search', 'description': 'Operations related to searching for flights'},
#             {'name': 'Payment Processing', 'description': 'Operations related to payment processing'},
#         ],

#         # Add authentication schemes
#         'SECURITY': [
#             {'Bearer': []},
#         ],
#         'SWAGGER_UI_SETTINGS': {
#             'deepLinking': True,
#             'persistAuthorization': True,
#             'displayOperationId': True,
#         },

#         # Customize operations
#         'DEFAULT_GENERATOR_CLASS': 'drf_spectacular.generators.SchemaGenerator',
#         'COMPONENT_NO_READ_ONLY_REQUIRED': True,
#         'ENUM_NAME_OVERRIDES': {
#             'BookingTypeEnum': ['ONE_WAY', 'ROUND_TRIP', 'MULTI_CITY'],
#             'TravelClassEnum': ['ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST'],
#             'PaymentStatusEnum': ['PENDING', 'COMPLETED', 'FAILED', 'REFUNDED', 'PARTIALLY_REFUNDED'],
#             'BookingStatusEnum': ['PENDING', 'COMPLETED', 'CANCELLED', 'PAYMENT_FAILED'],
#         },

#         # Add operation filtering
#         'POSTPROCESSING_HOOKS': [
#             'drf_spectacular.hooks.postprocess_schema_enums',
#             'drf_spectacular.hooks.postprocess_prioritize_required',
#         ],
#     }

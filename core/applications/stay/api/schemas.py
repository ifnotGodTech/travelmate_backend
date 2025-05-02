from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
    OpenApiTypes
)
from datetime import datetime, timedelta
from core.applications.stay.api.serializers import (
    HotelBookingSerializer,
    HotelDiscoverySerializer,
    AvailabilityCheckSerializer,
    GeoSearchSerializer,
    HotelReviewsSerializer
)

# --------------------------
# Common Response Examples
# --------------------------
ERROR_RESPONSE = OpenApiExample(
    "Error Response",
    value={"error": "Detailed error message"},
    status_codes=['400', '401', '404', '429']
)

# --------------------------
# Hotel Discovery Schema
# --------------------------
discover_hotel_schema = extend_schema(
    operation_id="discover_hotels",
    summary="Search for hotels by city or coordinates",
    description="Discover available hotels in a city or around specific coordinates with optional filters for price, rating, amenities, and dates.",
    parameters=[
        # [Same parameters as before...]
    ],
    responses={
        200: OpenApiResponse(
            response=HotelDiscoverySerializer,
            description="List of matching hotels",
            examples=[
                OpenApiExample(
                    "Success Response",
                    summary="Hotels Found",
                    description="Returns a list of hotels with basic info and pagination",
                    value={
                        "hotels": [
                            {
                                "code": "H1234",
                                "name": "Grand Hyatt",
                                "category": 5,
                                "location": {
                                    "city": "New York",
                                    "country": "US"
                                },
                                "min_rate": 250.00,
                                "currency": "USD"
                            }
                        ],
                        "pagination": {
                            "total": 42,
                            "page": 1
                        }
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid query parameters",
            examples=[ERROR_RESPONSE]
        ),
        429: OpenApiResponse(
            description="Rate limit exceeded",
            examples=[ERROR_RESPONSE]
        )
    }
)

# --------------------------
# Availability Check Schema
# --------------------------
availability_schema = extend_schema(
    summary="Check Hotel Availability",
    description="Check real-time availability and rates for a specific hotel.",
    request=AvailabilityCheckSerializer,
    responses={
        200: OpenApiResponse(
            description="Available rooms and rates",
            examples=[
                OpenApiExample(
                    name="Success Response",
                    value={
                        "available": True,
                        "rooms": [
                            {
                                "code": "DBL-STD",
                                "name": "Standard Double",
                                "rate_key": "XYZ123",
                                "price": 199.00,
                                "cancellation_policy": "Free cancellation until 24h before",
                                "amenities": ["WIFI", "TV"]
                            }
                        ]
                    }
                )
            ]
        ),
        400: OpenApiResponse(description="Invalid parameters", examples=[ERROR_RESPONSE]),
        404: OpenApiResponse(description="Hotel not found", examples=[ERROR_RESPONSE])
    }
)

# --------------------------
# Booking Schema
# --------------------------
book_hotel_schema = extend_schema(
    summary="Book Hotel",
    description="Create a new hotel booking with guest and payment details.",
    request=HotelBookingSerializer,
    responses={
        201: OpenApiResponse(
            description="Booking confirmed",
            examples=[
                OpenApiExample(
                    name="Success Response",
                    value={
                        "booking_reference": "HB123456",
                        "status": "CONFIRMED",
                        "hotel": "Grand Hyatt",
                        "check_in": "2023-12-01",
                        "check_out": "2023-12-05",
                        "total": 795.00,
                        "currency": "USD"
                    }
                )
            ]
        ),
        400: OpenApiResponse(description="Booking failed", examples=[ERROR_RESPONSE]),
        402: OpenApiResponse(description="Payment required", examples=[ERROR_RESPONSE])
    }
)

# --------------------------
# Booking Details Schema
# --------------------------
booking_details_schema = extend_schema(
    operation_id="get_booking",
    summary="Get Booking Details",

    description="Retrieve booking details by reference",
    parameters=[
        OpenApiParameter(
            name="reference",
            type=str,
            location=OpenApiParameter.PATH,
            description="Booking reference number"
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Booking details",
            examples=[
                OpenApiExample(
                    "Success Response",
                    value={
                        "reference": "HB123456",
                        "status": "CONFIRMED",
                        "hotel": {
                            "name": "Grand Hyatt",
                            "room": "Standard Double"
                        },
                        "dates": {
                            "check_in": "2023-12-01",
                            "check_out": "2023-12-05"
                        },
                        "guest": {
                            "name": "John Doe",
                            "email": "john@example.com"
                        }
                    }
                )
            ]
        ),
        404: OpenApiResponse(
            description="Booking not found",
            examples=[ERROR_RESPONSE]
        )
    }
)

# --------------------------
# Hotel Details Schema
# --------------------------
hotel_details_schema = extend_schema(
    operation_id="get_hotel_details",
    summary="Get Hotel Details",
    description="Get comprehensive hotel information",
    parameters=[
        OpenApiParameter(
            name="hotel_id",
            type=str,
            location=OpenApiParameter.PATH,
            description="Hotelbeds property ID"
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Hotel details",
            examples=[
                OpenApiExample(
                    "Success Response",
                    value={
                        "code": "H1234",
                        "name": "Grand Hyatt",
                        "description": "Luxury 5-star hotel in Manhattan",
                        "address": "123 Park Ave, New York",
                        "location": {
                            "latitude": 40.7128,
                            "longitude": -74.0060
                        },
                        "amenities": [
                            {"code": "POOL", "name": "Swimming Pool"},
                            {"code": "GYM", "name": "Fitness Center"}
                        ],
                        "images": [
                            {
                                "type": "MAIN",
                                "url": "https://example.com/hotel1.jpg"
                            }
                        ]
                    }
                )
            ]
        ),
        404: OpenApiResponse(
            description="Hotel not found",
            examples=[ERROR_RESPONSE]
        )
    }
)

# --------------------------
# Geo Search Schema
# --------------------------
geo_search_schema = extend_schema(
    operation_id="geo_search",
    summary="Search Hotels by Coordinates",
    description="Search hotels by geographic coordinates",
    request=GeoSearchSerializer,
    responses={
        200: OpenApiResponse(
            description="Nearby hotels",
            examples=[
                OpenApiExample(
                    "Success Response",
                    value={
                        "results": [
                            {
                                "hotel_id": "H1234",
                                "name": "Grand Hyatt",
                                "distance": 0.5,
                                "unit": "km",
                                "min_rate": 250.00
                            }
                        ]
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid coordinates",
            examples=[ERROR_RESPONSE]
        )
    }
)

# --------------------------
# Hotel Reviews Schema
# --------------------------
hotel_reviews_schema = extend_schema(
    operation_id="get_hotel_reviews",
    summary="Get Hotel Reviews",
    description="Get guest reviews for a hotel",
    request=HotelReviewsSerializer,
    parameters=[
        OpenApiParameter(
            name="hotel_id",
            type=str,
            location=OpenApiParameter.PATH,
            description="Hotelbeds property ID"
        ),
        OpenApiParameter(
            name="language",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Language code (default: EN)",
            default="EN"
        )
    ],
    responses={
        200: OpenApiResponse(
            response=HotelReviewsSerializer,
            description="Hotel reviews",
            examples=[
                OpenApiExample(
                    "Success Response",
                    value={
                        "reviews": [
                            {
                                "rating": 4.5,
                                "title": "Excellent stay",
                                "comment": "Great service and location",
                                "author": "Traveler123",
                                "date": "2023-05-15"
                            }
                        ],
                        "average_rating": 4.3,
                        "total_reviews": 42
                    }
                )
            ]
        ),
        404: OpenApiResponse(
            description="Hotel not found",
            examples=[ERROR_RESPONSE]
        )
    }
)


search_hotel_schema = extend_schema(
    operation_id="search_hotels",
    summary="Search Hotels",
    description="Search for hotels based on destination, check-in/check-out dates, number of guests, and optional filters like price range and amenities.",
    parameters=[
        OpenApiParameter(
            name="destination", type=str, location=OpenApiParameter.QUERY,
            description="City code or geographic coordinates"
        ),
        OpenApiParameter(name="check_in", type=OpenApiTypes.DATE, location=OpenApiParameter.QUERY, description="Check-in date (YYYY-MM-DD)"),
        OpenApiParameter(name="check_out", type=OpenApiTypes.DATE, location=OpenApiParameter.QUERY, description="Check-out date (YYYY-MM-DD)"),
        OpenApiParameter(name="adults", type=int, location=OpenApiParameter.QUERY, description="Number of adults", default=2),
        OpenApiParameter(name="children", type=int, location=OpenApiParameter.QUERY, description="Number of children", default=0),
        OpenApiParameter(name="min_price", type=int, location=OpenApiParameter.QUERY, description="Minimum price per night"),
        OpenApiParameter(name="max_price", type=int, location=OpenApiParameter.QUERY, description="Maximum price per night"),
        OpenApiParameter(name="amenities", type=str, location=OpenApiParameter.QUERY, description="Comma-separated list of amenity codes (e.g., WIFI,PARKING)")
    ],
    responses={
        200: OpenApiResponse(
            response=HotelDiscoverySerializer,
            description="List of matching hotels",
            examples=[
                OpenApiExample(
                    name="Success Response",
                    value={
                        "hotels": [
                            {
                                "code": "H1234",
                                "name": "Grand Hyatt",
                                "category": 5,
                                "location": {
                                    "city": "New York",
                                    "country": "US"
                                },
                                "min_rate": 250.00,
                                "currency": "USD"
                            }
                        ],
                        "pagination": {
                            "total": 42,
                            "page": 1
                        }
                    }
                )
            ]
        ),
        400: OpenApiResponse(description="Validation Error", examples=[ERROR_RESPONSE]),
        429: OpenApiResponse(description="Rate Limit Exceeded", examples=[ERROR_RESPONSE])
    }
)

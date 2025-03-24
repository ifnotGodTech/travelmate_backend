from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import OpenApiParameter, OpenApiExample, OpenApiTypes, OpenApiResponse



list_hotel_schema = extend_schema(
    operation_id="list_hotels",
        summary="Fetch Hotels by City Code",
        description="Retrieve a list of hotels within a specific city using the city code. , (helps to get the hotels id)",
        parameters=[
            OpenApiParameter(
                name="city_code",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="The IATA city code (e.g., 'NYC' for New York)."
            )
        ],
        responses={
            200: OpenApiResponse(
                response={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "hotel_id": {"type": "string", "description": "Unique hotel identifier."},
                            "name": {"type": "string", "description": "Hotel name."},
                            "city": {"type": "string", "description": "City code of the hotel location."}
                        }
                    }
                },
                description="A list of hotels in the given city."
            ),
            400: OpenApiResponse(
                description="Invalid or missing city code."
            ),
            500: OpenApiResponse(
                description="Internal server error."
            ),
        },
    )


search_hotel_schema = extend_schema(
    operation_id="search_hotels",
    summary="Search hotels",
    description="Search for hotels using hotel IDs (can search for multiple hotels ) and optional filters such as check-in/check-out dates, price range, number of adults, and country of residence.",
    parameters=[
        OpenApiParameter(
            name="hotelIds",
            type={"type": "array", "items": {"type": "string"}},
            location=OpenApiParameter.QUERY,
            required=True,
            description="List of hotel IDs to search for (comma-separated)."
        ),
        OpenApiParameter(
            name="checkInDate",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Check-in date in YYYY-MM-DD format (default: today)."
        ),
        OpenApiParameter(
            name="checkOutDate",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Check-out date in YYYY-MM-DD format (default: tomorrow)."
        ),
        OpenApiParameter(
            name="adults",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Number of adults (default: 1)."
        ),
        OpenApiParameter(
            name="roomQuantity",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Number of rooms required (default: 1)."
        ),
        OpenApiParameter(
            name="countryOfResidence",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Country of residence (ISO Alpha-2 country code, e.g., 'US')."
        ),
        OpenApiParameter(
            name="priceRange",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Price range in format 'min-max' (e.g., 100-300). Minimum price must be lower than maximum."
        ),
    ],
    responses={
        200: OpenApiResponse(
            response={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "hotel": {"type": "string", "description": "Hotel ID."},
                        "offer": {"type": "object", "description": "Hotel offer details."}
                    }
                }
            },
            description="List of available hotel offers."
        ),
        400: OpenApiResponse(
            description="Invalid input parameters, such as an incorrectly formatted price range or missing hotel IDs."
        ),
        500: OpenApiResponse(
            description="Internal server error or Amadeus API error."
        ),
    },
)


detail_schema = extend_schema(
        operation_id="get_hotel_details",
        summary="Get Hotel Details",
        description="Retrieves details of a specific hotel using its hotel ID.",
        parameters=[
            OpenApiParameter(
                name="hotel_id",
                description="Unique hotel identifier",
                required=True,
                type=str
            ),
        ],
        responses={200: dict},
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "hotelId": "HOTEL123",
                    "name": "Grand Hotel",
                    "address": "123 Main Street, London",
                    "rating": 5,
                    "amenities": ["Free WiFi", "Swimming Pool", "Breakfast"]
                },
                response_only=True
            )
        ]
    )



check_availability_schema = extend_schema(
        operation_id="check_hotel_availability",
        summary="🛏️ Check Hotel Availability",
        description="Checks room availability for a given hotel ID.",
        parameters=[
            OpenApiParameter(
                name="hotel_id",
                description="Unique hotel identifier",
                required=True,
                type=str
            ),
        ],
        responses={200: dict},
        examples=[
            OpenApiExample(
                "Success Response",
                value=[
                    {
                        "offerId": "OFFER123",
                        "room": "Deluxe Suite",
                        "price": "150 USD",
                        "availability": "Available"
                    },
                    {
                        "offerId": "OFFER456",
                        "room": "Standard Room",
                        "price": "100 USD",
                        "availability": "Limited"
                    }
                ],
                response_only=True
            )
        ]
    )

room_per_hotel_schema = extend_schema(
        operation_id="rooms_per_hotel",
        summary="Rooms per Hotel",
        description="Retrieve available rooms for a specific hotel with pricing transparency.",
        parameters=[
            OpenApiParameter(
                name="hotel_id", description="Hotel ID",
                required=True, type=str
            ),
            OpenApiParameter(
                name="check_in", description="Check-in date (YYYY-MM-DD)",
                required=True, type=str
            ),
            OpenApiParameter(
                name="check_out", description="Check-out date (YYYY-MM-DD)",
                required=True, type=str
            ),
        ],
        responses={200: dict},
        examples=[
            OpenApiExample(
                "Success Response",
                value=[
                    {
                        "offerId": "OFFER123",
                        "room": "Deluxe Suite",
                        "price": "150 USD",
                        "availability": "Available"
                    },
                    {
                        "offerId": "OFFER456",
                        "room": "Standard Room",
                        "price": "100 USD",
                        "availability": "Limited"
                    }
                ],
                response_only=True
            )
        ]
    )


book_hotel_schema = extend_schema(
    operation_id="book_hotel",
    summary="Book a Hotel Room",
    description=(
        "Allows a logged-in user to book a hotel room using their profile details. "
        "The user's first name, last name, email, and mobile number must be available in their profile."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "offer_id": {
                    "type": "string",
                    "description": "Unique ID of the hotel offer (required)."
                }
            },
            "required": ["offer_id"]
        }
    },
    responses={
        201: {
            "type": "object",
            "properties": {
                "pnr": {
                    "type": "string",
                    "description": "Booking reference number (PNR)."
                },
                "status": {
                    "type": "string",
                    "description": "Current booking status."
                },
                "providerConfirmationId": {
                    "type": "string",
                    "description": "Hotel provider confirmation number."
                }
            }
        },
        400: {
            "type": "object",
            "properties": {
                "error": {
                    "type": "string",
                    "description": "Error message (e.g., missing required fields, room unavailable)."
                }
            }
        },
        500: {
            "type": "object",
            "properties": {
                "error": {
                    "type": "string",
                    "description": "Internal server error message."
                }
            }
        }
    },
    parameters=[
        OpenApiParameter(
            name="Authorization",
            type=str,
            location=OpenApiParameter.HEADER,
            required=True,
            description="JWT token for authentication (Bearer Token format: `Bearer <token>`)."
        )
    ],
    examples=[
        OpenApiExample(
            "Successful Booking Request",
            description="A sample request body for booking a hotel room.",
            value={"offer_id": "ABC123XYZ"},
            request_only=True
        ),
        OpenApiExample(
            "Successful Booking Response",
            description="Example response when the hotel room is successfully booked.",
            value={
                "pnr": "X1Y2Z3",
                "status": "CONFIRMED",
                "providerConfirmationId": "12345678"
            },
            response_only=True
        ),
        OpenApiExample(
            "Error Response - Missing Offer ID",
            description="Example response when the `offer_id` is missing.",
            value={"error": "Offer ID is required"},
            response_only=True,
            status_codes=[400]
        ),
        OpenApiExample(
            "Error Response - Room Unavailable",
            description="Example response when the selected room is no longer available.",
            value={"error": "The room is not available"},
            response_only=True,
            status_codes=[400]
        ),
        OpenApiExample(
            "Error Response - Internal Server Error",
            description="Example response for unexpected server errors.",
            value={"error": "An unexpected error occurred"},
            response_only=True,
            status_codes=[500]
        )
    ],
    tags=["Hotels"]
)

city_search_schema = extend_schema(
        operation_id="search_cities",
        summary="Search for cities",
        description="Retrieve a list of cities that match the given search term.",
        parameters=[
            OpenApiParameter(
                name="term",
                description="Keyword to search for cities (e.g., 'Paris')",
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY
            )
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
        tags=["Hotels"]
    )

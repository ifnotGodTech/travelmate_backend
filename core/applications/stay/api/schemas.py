from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from datetime import datetime, timedelta


# Schema for listing hotels by city with optional filters
list_hotel_schema = extend_schema(
        description="Discover hotels by city with optional filters. Returns basic property information for hotels in a specified city.",
        parameters=[
            OpenApiParameter("city_code", description="City code of the city to search hotels in", required=True, type=str),
            OpenApiParameter("lat", description="Latitude of the location", required=False, type=str),
            OpenApiParameter("lon", description="Longitude of the location", required=False, type=str),
            OpenApiParameter("radius", description="Search radius in kilometers", required=False, type=str),
            OpenApiParameter("radius_unit", description="Unit for radius, e.g., KM or MI", required=False, type=str),
            OpenApiParameter("hotel_name", description="Name of the hotel to filter search results", required=False, type=str),
            OpenApiParameter("chains", description="Hotel chain name for filtering", required=False, type=str),
            OpenApiParameter("amenities", description="Hotel amenities to filter by", required=False, type=str),
            OpenApiParameter("ratings", description="Minimum rating for hotels", required=False, type=str),
        ],
        responses={
            200: OpenApiResponse(description="List of hotels matching the search criteria"),
            400: OpenApiResponse(description="Bad request error if city_code is missing or invalid"),
        }
    )

# Schema for checking real-time availability and rates for specific hotels
hotel_availability_schema = extend_schema(
        description="Check real-time availability and rates for specific hotels. Returns room types, prices, and booking conditions.",
        parameters=[
            OpenApiParameter("hotelIds", description="Comma-separated list of hotel IDs to check availability for", required=True, type=str),
            OpenApiParameter("checkInDate", description="Check-in date for the booking", required=False, type=str, default=datetime.today().strftime("%Y-%m-%d")),
            OpenApiParameter("checkOutDate", description="Check-out date for the booking", required=False, type=str, default=(datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")),
            OpenApiParameter("adults", description="Number of adults", required=False, type=int, default=1),
            OpenApiParameter("roomQuantity", description="Number of rooms to book", required=False, type=int, default=1),
            OpenApiParameter("countryOfResidence", description="Country of residence for the guest", required=False, type=str),
            OpenApiParameter("priceRange", description="Price range for the hotel", required=False, type=str),
        ],
        responses={
            200: OpenApiResponse(description="Availability and pricing details for the selected hotels"),
            400: OpenApiResponse(description="Bad request error if hotelIds are missing or invalid"),
        }
    )


# Schema for retrieving detailed property information for a specific hotel
property_info_schema = extend_schema(
        description="Retrieve comprehensive property details including amenities, descriptions, and media for a specific hotel.",
        parameters=[
            OpenApiParameter("hotel_id", description="The hotel ID for fetching detailed property information", required=True, type=str),
        ],
        responses={
            200: OpenApiResponse(description="Property details for the specified hotel"),
            400: OpenApiResponse(description="Bad request error if hotel_id is missing or invalid"),
            500: OpenApiResponse(description="Internal server error if an unexpected issue occurs"),
        }
    )


# Schema for unified comprehensive hotel search
comprehensive_search_schema = extend_schema(
        operation_id="comprehensive_search",
        description="Unified hotel search endpoint with comprehensive validation and error handling. Supports both discovery (general search) and availability (specific hotels) modes.",
        parameters=[
            OpenApiParameter("city_code", str, description="The city code for the hotel search.", required=False),
            OpenApiParameter("lat", str, description="Latitude for geo-based hotel search.", required=False),
            OpenApiParameter("lon", str, description="Longitude for geo-based hotel search.", required=False),
            OpenApiParameter("keyword", str, description="Keyword for hotel search.", required=False),
            OpenApiParameter("hotel_ids", str, description="Comma-separated list of hotel IDs for specific hotel search.", required=False),
            OpenApiParameter("radius", str, description="Radius for search in kilometers (default 50).", required=False, default="50"),
            OpenApiParameter("radius_unit", str, description="Unit of radius ('KM' or 'MI').", required=False, default="KM"),
            OpenApiParameter("chains", str, description="Comma-separated list of hotel chain codes.", required=False),
            OpenApiParameter("amenities", str, description="Comma-separated list of amenities.", required=False),
            OpenApiParameter("ratings", str, description="Ratings for the hotel search.", required=False),
            OpenApiParameter("price_range", str, description="Price range for hotel search in format 'min:max'.", required=False),
            OpenApiParameter("currency", str, description="Currency for the price range (default USD).", required=False, default="USD"),
            OpenApiParameter("view", str, description="View type (e.g., 'FULL').", required=False, default="FULL"),
            OpenApiParameter("best_rate_only", str, description="Filter for the best rate only (true/false).", required=False, default="true"),
            OpenApiParameter("check_in", str, description="Check-in date in YYYY-MM-DD format.", required=False),
            OpenApiParameter("check_out", str, description="Check-out date in YYYY-MM-DD format.", required=False),
            OpenApiParameter("adults", str, description="Number of adults (default 1).", required=False, default="1"),
            OpenApiParameter("room_quantity", str, description="Number of rooms (default 1).", required=False, default="1"),
            OpenApiParameter("country_of_residence", str, description="Country of residence.", required=False),
            OpenApiParameter("payment_policy", str, description="Payment policy.", required=False),
            OpenApiParameter("board_type", str, description="Board type (e.g., 'all-inclusive').", required=False)
        ],
        responses={
            200: OpenApiResponse(description="A list of hotels matching the search criteria."),
            400: OpenApiResponse(description="Bad request, validation error."),
            500: OpenApiResponse(description="Internal server error.")
        }
    )

# Schema for fetching hotel reviews
# fetch_review_schema = extend_schema(
#     operation_id="fetch_hotel_reviews",
#     summary="Fetch Hotel Reviews",
#     description="Fetch reviews for a specific hotel.",
#     parameters=common_parameters() + [
#         OpenApiParameter(
#             name="hotel_id", type=str, location=OpenApiParameter.QUERY,
#             description="Hotel ID to fetch reviews for.", required=True
#         ),
#     ],
#     responses={
#         200: generate_openapi_response(description="List of reviews for the specified hotel."),
#         400: generate_openapi_response(description="Bad Request if hotel_id is not provided."),
#         500: generate_openapi_response(description="Internal Server Error if the request fails.")
#     }
# )


book_hotel_schema = extend_schema(
        description="Book a hotel room for a specific stay.",
        parameters=[
            OpenApiParameter("hotel_id", type=str, location=OpenApiParameter.QUERY, description="Hotel ID", required=True),
            OpenApiParameter("check_in_date", type=str, location=OpenApiParameter.QUERY, description="Check-in date (YYYY-MM-DD)", required=True),
            OpenApiParameter("check_out_date", type=str, location=OpenApiParameter.QUERY, description="Check-out date (YYYY-MM-DD)", required=True),
            OpenApiParameter("guests_count", type=int, location=OpenApiParameter.QUERY, description="Number of guests", required=True),
        ],
        responses={
            200: "Hotel booked successfully",
            400: "Invalid input parameters",
            500: "Internal Server Error"
        }
    )

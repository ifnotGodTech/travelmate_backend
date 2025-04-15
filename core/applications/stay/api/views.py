import json
from core.amadeus import amadeus_client
from core.amadeus.amadeus_client2 import BookingAmadeusClient
from core.helpers.enums import GenderChoice
from rest_framework import  status
from rest_framework.viewsets import ViewSet

from core.amadeus.amadeus_services import  book_hotel_room, fetch_hotel_details, fetch_hotel_reviews, list_or_fetch_hotels_by_city, search_hotels
from rest_framework.response import Response
from core.applications.stay.api.schemas import (
    comprehensive_search_schema, list_hotel_schema, hotel_availability_schema,
    property_info_schema
)
from django.utils import timezone
from typing import Optional
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError

from amadeus import ResponseError, Location
import logging
from core.helpers.authentication import CustomJWTAuthentication
from djoser.conf import settings as djoser_settings
from django.conf import settings as django_settings
from rest_framework.decorators import action
from django.http import JsonResponse


logger = logging.getLogger(__name__)


class HotelApiViewSet(ViewSet):
    """
    ViewSet for hotel operations integrating with Amadeus API.
    Provides endpoints for hotel discovery, availability checking, and property details.
    """
    authentication_class = [CustomJWTAuthentication]
    permission_classes = djoser_settings.PERMISSIONS.user

    # --- Hotel Discovery Endpoints ---
    @list_hotel_schema
    def list(self, request):
        """
        Discover hotels by city with optional filters.
        Returns basic property information for hotels in a specified city.
        """
        city_code = request.query_params.get("city_code")
        if not city_code:
            return Response(
                {"error": "City code is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract optional filters from query params
        filters = {
            "latitude": request.query_params.get("lat"),
            "longitude": request.query_params.get("lon"),
            "radius": request.query_params.get("radius"),
            "radiusUnit": request.query_params.get("radius_unit"),
            "hotelName": request.query_params.get("hotel_name"),
            "chains": request.query_params.get("chains"),
            "amenities": request.query_params.get("amenities"),
            "ratings": request.query_params.get("ratings")
        }

        hotels = list_or_fetch_hotels_by_city(city_code, **{
            k: v for k, v in filters.items() if v is not None
        })

        return Response(
            hotels,
            status=status.HTTP_200_OK if isinstance(hotels, list) else status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # --- Availability Endpoints ---
    @hotel_availability_schema
    @action(detail=False, methods=["get"], url_path="availability")
    def check_availability(self, request):
        """
        Check real-time availability and rates for specific hotels.
        Returns room types, prices, and booking conditions.
        """
        hotel_ids = request.query_params.getlist("hotelIds")
        if not hotel_ids:
            return Response(
                {"error": "At least one hotelId is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set default dates if not provided
        check_in = request.query_params.get(
            "checkInDate",
            datetime.today().strftime("%Y-%m-%d")
        )
        check_out = request.query_params.get(
            "checkOutDate",
            (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        )

        # Get search parameters
        search_params = {
            "hotel_ids": hotel_ids,
            "check_in": check_in,
            "check_out": check_out,
            "adults": request.query_params.get("adults", "1"),
            "room_quantity": request.query_params.get("roomQuantity", "1"),
            "country_of_residence": request.query_params.get("countryOfResidence"),
            "price_range": request.query_params.get("priceRange")
        }

        response = search_hotels(**search_params)
        return Response(
            response,
            status=status.HTTP_200_OK if isinstance(response, list) else status.HTTP_400_BAD_REQUEST
        )

    # --- Property Information Endpoints ---
    @property_info_schema
    @action(detail=False, methods=["get"], url_path="property-info")
    def get_property_info(self, request):
        """
        Retrieve comprehensive property details including amenities, descriptions,
        and media for a specific hotel.
        """
        hotel_id = request.query_params.get("hotel_id")
        if not hotel_id:
            return Response(
                {"error": "hotel_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            response = fetch_hotel_details(hotel_id)
            return Response(
                response,
                status=status.HTTP_200_OK
            )
        except ResponseError as amadeus_error:
            logger.error(f"Amadeus API Error: {amadeus_error}")
            return Response(
                {"error": str(amadeus_error)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in get_property_info: {str(e)}", exc_info=True)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @comprehensive_search_schema
    @action(detail=False, methods=["get"], url_path="full-search")
    def comprehensive_search(self, request):
        """
        Unified hotel search endpoint with comprehensive validation and error handling.
        Supports both discovery (general search) and availability (specific hotels) modes.
        """
        try:
            # ===== 1. ENHANCED PARAMETER VALIDATION =====
            self._validate_location_params(request)
            params = self._build_search_params(request)

            # ===== 2. DATE VALIDATION =====
            if request.query_params.get('check_in'):
                self._validate_dates(request)
                params.update(self._build_availability_params(request))

            # ===== 3. API REQUEST EXECUTION =====
            clean_params = {k: v for k, v in params.items() if v is not None}
            logger.info(f"Amadeus API Request: {clean_params}")

            response = self._execute_amadeus_request(clean_params)

            # ===== 4. RESPONSE PROCESSING =====
            return Response(
                self._format_response(response.data),
                status=status.HTTP_200_OK
            )

        except ValidationError as e:
            logger.warning(f"Validation error: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ResponseError as error:
            error_details = self._parse_amadeus_error(error)
            logger.error(f"Amadeus API Error: {error_details}")
            return Response(
                {"error": "Hotel search failed", "details": error_details},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.critical(f"Unexpected error: {str(e)}", exc_info=True)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # Helper Methods --------------------------------------------------

    def _validate_location_params(self, request):
        """Validate at least one location parameter exists"""
        if not any([
            request.query_params.get('city_code'),
            request.query_params.get('lat'),
            request.query_params.get('keyword'),
            request.query_params.get('hotel_ids')
        ]):
            raise ValidationError("Provide city_code, lat/lon, keyword, or hotel_ids")

    def _validate_dates(self, request):
        """Validate date parameters with business rules"""
        check_in = request.query_params.get('check_in')
        check_out = request.query_params.get('check_out')

        if not check_out:
            raise ValidationError("Check-out date required when check-in is provided")

        try:
            check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Invalid date format. Use YYYY-MM-DD")

        today = datetime.now().date()
        if check_in_date < today:
            raise ValidationError("Check-in date cannot be in the past")
        if check_out_date <= check_in_date:
            raise ValidationError("Check-out must be after check-in")
        if (check_out_date - check_in_date).days > 30:
            raise ValidationError("Maximum stay duration is 30 days")

    def _build_search_params(self, request):
        """Construct base search parameters with defaults"""
        return {
            'cityCode': request.query_params.get('city_code'),
            'keyword': request.query_params.get('keyword'),
            'latitude': request.query_params.get('lat'),
            'longitude': request.query_params.get('lon'),
            'hotelIds': self._parse_hotel_ids(request),
            'radius': request.query_params.get('radius', '50'),
            'radiusUnit': request.query_params.get('radius_unit', 'KM').upper(),
            'chainCodes': request.query_params.get('chains'),
            'amenities': request.query_params.get('amenities'),
            'ratings': request.query_params.get('ratings'),
            'priceRange': self._validate_price_range(request.query_params.get('price_range')),
            'currency': request.query_params.get('currency', 'USD').upper(),
            'view': request.query_params.get('view', 'FULL').upper(),
            'bestRateOnly': str(request.query_params.get('best_rate_only', 'true')).lower() == 'true',
        }

    def _build_availability_params(self, request):
        """Construct availability-specific parameters"""
        return {
            'checkInDate': request.query_params.get('check_in'),
            'checkOutDate': request.query_params.get('check_out'),
            'adults': request.query_params.get('adults', '1'),
            'roomQuantity': request.query_params.get('room_quantity', '1'),
            'countryOfResidence': request.query_params.get('country_of_residence'),
            'paymentPolicy': request.query_params.get('payment_policy'),
            'boardType': request.query_params.get('board_type'),
        }

    def _parse_hotel_ids(self, request):
        hotel_ids_param = request.query_params.get('hotel_ids')
        if not hotel_ids_param:
            return None

        ids = [id.strip() for id in hotel_ids_param.split(',') if id.strip()]
        if not ids:
            return None

        return ",".join(ids)

    def _execute_amadeus_request(self, params):
        # Check for hotelIds (for specific hotels search)
        if "hotelIds" in params:
            return amadeus_client.shopping.hotel_offers_search.get(**params)

        # Check for cityCode (for city-based hotel search)
        elif "cityCode" in params:
            return amadeus_client.shopping.hotel_offers_search.get(**params)

        # Check for latitude and longitude (for geo-based hotel search)
        elif "latitude" in params and "longitude" in params:
            return amadeus_client.shopping.hotel_offers_search.get(**params)

        # Raise an error if none of the parameters are present
        else:
            raise ValueError("Invalid search mode — please provide hotelIds, cityCode, or lat/lon")


    def _format_response(self, data):
        """
        Format the response data returned by the Amadeus API.
        This method assumes that data can either be a list or a dictionary.
        """
        # Check if the data is a list or a dictionary and format accordingly
        if isinstance(data, list):
            # If it's a list, return the list as is, or modify the structure if needed
            formatted_data = {
                "hotels": data,  # Assuming `data` is the list of hotels
                "total_count": len(data)  # You can modify this based on the actual response
            }
        elif isinstance(data, dict):
            # If it's a dictionary, access keys like normal
            formatted_data = {
                "hotels": data.get("hotels", []),  # Assuming `hotels` is a key in the response
                "total_count": data.get("total_count", 0)
            }
        else:
            # Handle other unexpected formats or raise an error
            formatted_data = {
                "error": "Unexpected response format"
            }

        return formatted_data


    def _parse_amadeus_error(self, error):
        """Extract relevant error details from Amadeus response"""
        return {
            "status_code": error.response.status_code,
            "message": str(error),
            "amadeus_response": getattr(error.response, 'result', None),
        }

    def _validate_price_range(self, price_range_str: Optional[str]) -> Optional[str]:
        """
        Validates price range format (min:max) and ensures min <= max.
        Returns formatted string or raises ValidationError.
        """
        if not price_range_str:
            return None

        try:
            min_price, max_price = map(float, price_range_str.split(':'))
        except ValueError:
            raise ValidationError("Price range must be in format 'min:max' (e.g., '100:200')")

        if min_price < 0 or max_price < 0:
            raise ValidationError("Prices cannot be negative")

        if min_price > max_price:
            raise ValidationError("Minimum price cannot exceed maximum price")

        return f"{int(min_price)}:{int(max_price)}"

    # @fetch_review_schema
    @action(detail=True, methods=["get"], url_path="reviews")
    def get_hotel_reviews(self, request, pk=None):
        """
        Fetch reviews for a specific hotel based on hotel_id.
        """
        hotel_id = pk  # 'pk' comes from the URL path (e.g., /api/hotels/reviews/{hotel_id}/)

        if not hotel_id:
            return Response(
                {"error": "hotel_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            reviews = fetch_hotel_reviews(hotel_id)  # Assuming this function interacts with the Amadeus API
            return Response(
                reviews,
                status=status.HTTP_200_OK
            )
        except ResponseError as amadeus_error:
            logger.error(f"Amadeus API Error: {amadeus_error}")
            return Response(
                {"error": str(amadeus_error)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in get_hotel_reviews: {str(e)}", exc_info=True)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



    @action(detail=False, methods=["post"], url_path="book-hotel")
    def book_hotel(self, request):
        offer_id = request.data.get("offer_id")
        guests = request.data.get("guests")
        payments = request.data.get("payments")

        if not all([offer_id, guests, payments]):
            logger.warning("Missing booking parameters", extra={"request_data": request.data})
            return Response(
                {
                    "error": "Missing required parameters",
                    "required_fields": ["offer_id", "guests", "payments"],
                    "received": {k: v is not None for k, v in request.data.items()}
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        def attempt_booking():
            client = BookingAmadeusClient().get_client()
            # ✅ Use positional arguments, NOT keyword arguments
            return client.booking.hotel_bookings.post(
                [{"id": offer_id}],  # hotel_offers as first argument
                guests,              # second: guests
                payments             # third: payments
            )

        try:
            response = attempt_booking()

            logger.info("Hotel booking successful", extra={"offer_id": offer_id, "guest_count": len(guests)})
            return Response({
                "message": "Hotel booked successfully",
                "data": response.data,
                "booking_reference": response.result.get("bookingId")
            }, status=status.HTTP_200_OK)

        except ResponseError as e:
            if getattr(e, 'code', None) == 38190:
                logger.info("Access token expired, retrying...")
                # Try to refresh the access token and make the booking again
                try:
                    # Re-initialize the Amadeus client and retry the booking
                    client = BookingAmadeusClient()
                    client.client = client._initialize_client()  # Refresh the client with new credentials
                    response = attempt_booking()

                    logger.info("Hotel booked after token refresh", extra={"offer_id": offer_id})
                    return Response({
                        "message": "Hotel booked successfully after token refresh",
                        "data": response.data,
                        "booking_reference": response.result.get("bookingId")
                    }, status=status.HTTP_200_OK)

                except Exception as retry_error:
                    logger.error("Retry failed after token refresh", exc_info=True)
                    return Response({
                        "error": "Booking failed after token refresh",
                        "details": str(retry_error)
                    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            logger.error("Amadeus API error during booking", extra={
                "offer_id": offer_id,
                "error_details": str(e)
            })
            return Response({
                "error": "Amadeus API booking failure",
                "details": str(e)
            }, status=getattr(e.response, 'status_code', status.HTTP_400_BAD_REQUEST))

        except Exception as e:
            logger.critical("Unexpected error during hotel booking", exc_info=True)
            return Response({
                "error": "Internal booking system error",
                "reference_id": f"ERR-{timezone.now().timestamp()}",
                "contact_support": True
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

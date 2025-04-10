import json
from core.amadeus import amadeus_client
from core.helpers.enums import GenderChoice
from rest_framework import  status
from rest_framework.viewsets import ViewSet

from core.amadeus.amadeus_services import  book_hotel_room, fetch_hotel_details, list_or_fetch_hotels_by_city, search_hotels
from rest_framework.response import Response
from core.applications.stay.api.schemas import (
    search_hotel_schema, detail_schema, check_availability_schema,
    room_per_hotel_schema, book_hotel_schema, city_search_schema,
    list_hotel_schema
)
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
    @search_hotel_schema
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
    @detail_schema
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
        """Convert hotel_ids query param to Amadeus format"""
        if ids := request.query_params.get('hotel_ids'):
            return ",".join([id.strip() for id in ids.split(',')])
        return None

    def _execute_amadeus_request(self, params):
        """Route to appropriate Amadeus endpoint"""
        if 'hotelIds' in params and params['hotelIds']:
            return amadeus_client.shopping.hotel_offers_by_hotel.get(**params)
        else:
            return amadeus_client.shopping.hotel_offers_search.get(**params)


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

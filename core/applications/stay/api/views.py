from core.applications.stay.services.exceptions import HotelbedsAPIError
from core.applications.stay.services.hotelbads import HotelbedsService
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import UserRateThrottle

from core.applications.stay.api.serializers import (
    HotelDiscoverySerializer,
    AvailabilityCheckSerializer,
    HotelBookingSerializer,
    GeoSearchSerializer,
    HotelReviewsSerializer,
    HotelSearchSerializer
)

from core.applications.stay.api.schemas import  (
    availability_schema, book_hotel_schema, search_hotel_schema,
    booking_details_schema, hotel_details_schema, geo_search_schema,
    hotel_reviews_schema, discover_hotel_schema
)

import logging

logger = logging.getLogger('hotelbeds.views')

class HotelApiViewSet(ViewSet):
    """
    Hotelbeds API Integration

    Provides endpoints for:
    - Hotel discovery
    - Availability checking
    - Booking management
    - Hotel information
    """

    service = HotelbedsService()
    # throttle_classes = [UserRateThrottle]

    def handle_exception(self, exc):
        """Custom exception handler for Hotelbeds API errors"""
        if isinstance(exc, HotelbedsAPIError):
            logger.error(f"Hotelbeds API error: {str(exc)}")
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().handle_exception(exc)

    @search_hotel_schema
    @action(detail=False, methods=['GET'])
    def search(self, request):
        """
        Search hotels with flexible criteria

        Query Params:
        - destination (str): City code or geographic coordinates
        - check_in (str): YYYY-MM-DD
        - check_out (str): YYYY-MM-DD
        - adults (int): Default=2
        - children (int): Default=0
        - min_price (int): Optional
        - max_price (int): Optional
        - amenities (str): Comma-separated codes (e.g., "WIFI,PARKING")
        """
        serializer = HotelSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data

        # Parse amenities only if provided
        amenities = validated.get("amenities")
        amenity_list = (
            [a.strip() for a in amenities.split(",") if a.strip()]
            if amenities
            else []
        )

        try:
            results = self.service.search_hotels(
                destination=validated["destination"],
                check_in=validated["check_in"],   # now properly formatted date object
                check_out=validated["check_out"], # now properly formatted date object
                adults=validated.get("adults", 2),
                children=validated.get("children", 0),
                filters={
                    "min_price": validated.get("min_price"),
                    "max_price": validated.get("max_price"),
                    "amenities": amenity_list,
                },
            )
            return Response(results)
        except HotelbedsAPIError as e:
            raise  # Will be handled globally if set up

    @discover_hotel_schema
    @action(detail=False, methods=['GET'])
    def discover(self, request):
        """
        Discover hotels in a specific city

        Parameters:
        - city_code: Required IATA city code
        - language: Optional language code (default: ENG)
        - ratings: Optional list of star ratings (1-5)
        - amenities: Optional list of amenity codes
        - page: Optional page number (default: 1)
        - page_size: Optional items per page (default: 20)
        """
        serializer = HotelDiscoverySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        results = self.service.discover_hotels(
            city_code=serializer.validated_data['city_code'],
            filters=serializer.validated_data
        )
        return Response(results)

    @availability_schema
    @action(detail=False, methods=['POST'])
    def availability(self, request):
        """
        Check hotel availability

        Parameters (in request body):
        - hotel_id: Required hotel ID
        - check_in: Required check-in date (YYYY-MM-DD)
        - check_out: Required check-out date (YYYY-MM-DD)
        - adults: Optional number of adults (default: 2)
        - children: Optional number of children (default: 0)
        """
        serializer = AvailabilityCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        results = self.service.check_availability(
            hotel_id=serializer.validated_data['hotel_id'],
            check_in=serializer.validated_data['check_in'],
            check_out=serializer.validated_data['check_out'],
            adults=serializer.validated_data.get('adults', 2),
            children=serializer.validated_data.get('children', 0)
        )
        return Response(results)

    @book_hotel_schema
    @action(detail=False, methods=['POST'])
    def book(self, request):
        """
        Create a hotel booking

        Parameters (in request body):
        - holder_name: Booking holder first name
        - holder_surname: Booking holder last name
        - holder_email: Booking holder email
        - holder_phone: Booking holder phone
        - rooms: List of rooms to book (each with rate_key and paxes)
        - payment_data: Payment information
        - special_requests: Optional special requests
        """
        serializer = HotelBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking = self.service.create_booking(
            rate_key=serializer.validated_data['rooms'][0]['rate_key'],
            holder_info={
                'name': serializer.validated_data['holder_name'],
                'surname': serializer.validated_data['holder_surname'],
                'email': serializer.validated_data['holder_email'],
                'phone': serializer.validated_data['holder_phone']
            },
            payment_data=serializer.validated_data['payment_data'],
            rooms=serializer.validated_data['rooms']
        )
        return Response(booking, status=status.HTTP_201_CREATED)

    @booking_details_schema
    @action(detail=False, methods=['GET'], url_path='bookings/(?P<reference>[^/.]+)')
    def booking_details(self, request, reference=None):
        """Get booking details by reference"""
        results = self.service.get_booking(reference)
        return Response(results)

    @action(detail=False, methods=['DELETE'], url_path='bookings/(?P<reference>[^/.]+)/cancel')
    def cancel_booking(self, request, reference=None):
        """Cancel booking by reference"""
        results = self.service.cancel_booking(reference)
        return Response(results)

    @hotel_details_schema
    @action(detail=False, methods=['GET'], url_path='hotels/(?P<hotel_id>[^/.]+)/details')
    def hotel_details(self, request, hotel_id=None):
        """Get hotel details by ID"""
        results = self.service.get_hotel_details(hotel_id)
        return Response(results)

    @hotel_reviews_schema
    @action(detail=False, methods=['GET'], url_path='hotels/(?P<hotel_id>[^/.]+)/reviews')
    def hotel_reviews(self, request, hotel_id=None):
        """Get hotel reviews by ID"""
        serializer = HotelReviewsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        results = self.service.get_hotel_reviews(
            hotel_id=hotel_id,
            language=serializer.validated_data.get('language', 'ENG')
        )
        return Response(results)

    @geo_search_schema
    @action(detail=False, methods=['GET'])
    def geo_search(self, request):
        """
        Search hotels by geographic coordinates

        Parameters:
        - latitude: Required latitude
        - longitude: Required longitude
        - radius: Optional search radius (default: 10)
        - unit: Optional distance unit (KM or MI, default: KM)
        """
        serializer = GeoSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        results = self.service.geo_search(
            latitude=serializer.validated_data['latitude'],
            longitude=serializer.validated_data['longitude'],
            radius=serializer.validated_data.get('radius', 10),
            unit=serializer.validated_data.get('unit', 'KM')
        )
        return Response(results)

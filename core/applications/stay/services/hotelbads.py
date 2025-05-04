
from core.applications.stay.client.hotelbeds import HotelbedsAPIClient

import logging
from datetime import date, datetime, timedelta

from core.applications.stay.services.exceptions import HotelbedsAPIError, HotelbedsValidationError

logger = logging.getLogger('hotelbeds.service')

class HotelbedsService:
    """Business logic layer for Hotelbeds API operations"""

    def __init__(self):
        self.client = HotelbedsAPIClient()

    def search_hotels(self, destination, check_in, check_out, adults=2, children=0, filters=None):
        if check_in < date.today():
            raise HotelbedsValidationError("Check-in date cannot be in the past")

        check_in_str = check_in.strftime('%Y-%m-%d')
        check_out_str = check_out.strftime('%Y-%m-%d')

        payload = {
            "stay": {
                "checkIn": check_in_str,
                "checkOut": check_out_str
            },
            "occupancies": [{
                "adults": adults,
                "children": children
            }]
        }

        if ',' in destination:
            lat, lon = destination.split(',')
            payload["geolocation"] = {
                "latitude": float(lat),
                "longitude": float(lon),
                "radius": 20,
                "unit": "km"
            }
        else:
            payload["destination"] = {"code": destination}

        if filters:
            payload_filter = {}
            if filters.get('min_price'):
                payload_filter["minRate"] = filters['min_price']
            if filters.get('max_price'):
                payload_filter["maxRate"] = filters['max_price']
            if filters.get('amenities'):
                payload_filter["amenities"] = filters['amenities']
            if payload_filter:
                payload["filter"] = payload_filter

        try:
            return self.client.search_hotels(payload)
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise HotelbedsAPIError("Hotel search failed") from e

    def discover_hotels(self, city_code, filters=None):
        """
        Discover hotels in a specific city with optional filters

        Args:
            city_code (str): IATA city code
            filters (dict): Optional filters including:
                - language (str): Language code (default: 'ENG')
                - ratings (list): List of star ratings (1-5)
                - amenities (list): List of amenity codes
                - page (int): Pagination start (default: 1)
                - page_size (int): Items per page (default: 20)

        Returns:
            dict: API response with hotel data

        Raises:
            HotelbedsAPIError: If API request fails
            HotelbedsValidationError: If input validation fails
        """
        if not city_code:
            raise HotelbedsValidationError("City code is required")

        params = {
            'cityCode': city_code,
            'language': filters.get('language', 'ENG'),
            'from': filters.get('page', 1),
            'to': filters.get('page_size', 20)
        }

        if filters.get('ratings'):
            params['ratings'] = ','.join(map(str, filters['ratings']))

        try:
            return self.client.get('/hotel-api/1.0/hotels', params=params)
        except Exception as e:
            logger.error(f"Failed to discover hotels: {str(e)}")
            raise HotelbedsAPIError("Failed to discover hotels") from e

    def check_availability(self, hotel_id, check_in, check_out, adults=2, children=0):
        """
        Check room availability for specific hotel and dates

        Args:
            hotel_id (str): Hotel ID
            check_in (date): Check-in date
            check_out (date): Check-out date
            adults (int): Number of adults (default: 2)
            children (int): Number of children (default: 0)

        Returns:
            dict: Availability data

        Raises:
            HotelbedsAPIError: If API request fails
            HotelbedsValidationError: For invalid dates
        """
        if check_in < date.today():
            raise HotelbedsValidationError("Check-in date cannot be in the past")
        if check_out <= check_in:
            raise HotelbedsValidationError("Check-out must be after check-in")

        data = {
            'stay': {
                'checkIn': check_in.strftime('%Y-%m-%d'),
                'checkOut': check_out.strftime('%Y-%m-%d')
            },
            'occupancies': [{
                'rooms': 1,
                'adults': adults,
                'children': children
            }],
            'hotels': {
                'hotel': [hotel_id]
            }
        }

        try:
            return self.client.post('/hotel-api/1.0/checkrates', data=data)
        except Exception as e:
            logger.error(f"Availability check failed: {str(e)}")
            raise HotelbedsAPIError("Failed to check availability") from e

    def create_booking(self, rate_key, holder_info, payment_data, rooms):
        """
        Create a hotel booking

        Args:
            rate_key (str): Rate key from availability check
            holder_info (dict): Booking holder information
            payment_data (dict): Payment information
            rooms (list): List of rooms to book

        Returns:
            dict: Booking confirmation

        Raises:
            HotelbedsAPIError: If booking fails
        """
        data = {
            'holder': holder_info,
            'rooms': rooms,
            'paymentData': payment_data,
            'clientReference': f"BOOKING-{datetime.now().timestamp()}"
        }

        try:
            return self.client.post('/hotel-api/1.0/bookings', data=data)
        except Exception as e:
            logger.error(f"Booking failed: {str(e)}")
            raise HotelbedsAPIError("Failed to create booking") from e

    def get_booking(self, reference):
        """Get booking details by reference"""
        try:
            return self.client.get(f'/hotel-api/1.0/bookings/{reference}')
        except Exception as e:
            logger.error(f"Failed to get booking: {str(e)}")
            raise HotelbedsAPIError("Failed to retrieve booking") from e

    def cancel_booking(self, reference):
        """Cancel a booking by reference"""
        try:
            return self.client.delete(f'/hotel-api/1.0/bookings/{reference}')
        except Exception as e:
            logger.error(f"Failed to cancel booking: {str(e)}")
            raise HotelbedsAPIError("Failed to cancel booking") from e

    def get_hotel_details(self, hotel_id):
        """Get detailed information about a hotel"""
        try:
            return self.client.get(f'/hotel-api/1.0/hotels/{hotel_id}')
        except Exception as e:
            logger.error(f"Failed to get hotel details: {str(e)}")
            raise HotelbedsAPIError("Failed to get hotel details") from e

    def get_hotel_reviews(self, hotel_id, language='ENG'):
        """Get reviews for a specific hotel"""
        try:
            params = {'language': language}
            return self.client.get(f'/hotel-api/1.0/hotels/{hotel_id}/reviews', params=params)
        except Exception as e:
            logger.error(f"Failed to get hotel reviews: {str(e)}")
            raise HotelbedsAPIError("Failed to get hotel reviews") from e

    def geo_search(self, latitude, longitude, radius=10, unit='KM'):
        """Search hotels by geographic coordinates"""
        try:
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'radius': radius,
                'unit': unit
            }
            return self.client.get('/hotel-api/1.0/locations/hotels', params=params)
        except Exception as e:
            logger.error(f"Failed to perform geo search: {str(e)}")
            raise HotelbedsAPIError("Failed to perform geo search") from e

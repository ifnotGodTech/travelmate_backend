import logging
import requests
from django.conf import settings
from django.core.cache import cache
import datetime

logger = logging.getLogger(__name__)

class AmadeusService:
    """
    Utility class for interacting with the Amadeus API for transfers
    """

    def __init__(self):
        self.client_id = settings.AMADEUS_API_TEST_KEY if settings.AMADEUS_API_TESTING else settings.AMADEUS_API_LIVE_KEY
        self.client_secret = settings.AMADEUS_API_TEST_SECRET if settings.AMADEUS_API_TESTING else settings.AMADEUS_API_LIVE_SECRET
        self.base_url = 'https://test.api.amadeus.com'  # Use 'https://api.amadeus.com' for production
        self.token = None

    def get_auth_token(self):
        """
        Get authentication token from Amadeus API
        """
        # Try to get token from cache first
        token = cache.get('amadeus_token')
        if token:
            return token

        # If not in cache, get a new token
        url = f"{self.base_url}/v1/security/oauth2/token"
        payload = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        try:
            response = requests.post(url, data=payload)

            if response.status_code == 200:
                data = response.json()
                token = data['access_token']
                # Cache the token for slightly less than its expiry time
                cache_timeout = data.get('expires_in', 1800) - 60  # Default to 30 mins minus 1 min if not specified
                cache.set('amadeus_token', token, timeout=cache_timeout)
                return token
            else:
                logger.error(f"Failed to get authentication token: {response.status_code} - {response.text}")
                raise Exception(f"Failed to get authentication token: {response.text}")
        except Exception as e:
            logger.error(f"Unexpected error getting auth token: {e}", exc_info=True)
            raise


    def _get_headers(self):
        """
        Get headers for Amadeus API requests, refreshing the token if needed
        """
        if not self.token:
            self.token = self.get_auth_token()

        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    # In AmadeusService.search_transfers
    def search_transfers(self, pickup_location, dropoff_location, pickup_datetime, passengers, transfer_type="PRIVATE", **filters):
        """
        Search for available transfers using Amadeus API with specified criteria
        """
        cache_key = f"transfer_search:{pickup_location}:{dropoff_location}:{pickup_datetime}:{passengers}:{transfer_type}:{filters}"
        cached_results = cache.get(cache_key)

        if cached_results:
            logger.info("Returning cached transfer search results")
            return cached_results

        try:
            # Format the request payload based on successful test example
            payload = {
                "startLocationCode": pickup_location,
                "startDateTime": pickup_datetime.isoformat(),
                "transferType": transfer_type,
                "passengers": passengers
            }
            # Add currency to payload if provided
            if filters.get('currency'):
                payload["currencyCode"] = filters.get('currency').upper()

            # Log the full request for debugging
            headers = self._get_headers()
            # Create a copy of headers without the token for logging
            log_headers = {k: v for k, v in headers.items() if k != 'Authorization'}
            log_headers['Authorization'] = 'Bearer [REDACTED]'

            # Handle end location with the exact field names from the working request
            if filters.get('end_address'):
                payload["endAddressLine"] = filters.get('end_address')

                if filters.get('end_city'):
                    payload["endCityName"] = filters.get('end_city')

                if filters.get('end_country'):
                    payload["endCountryCode"] = filters.get('end_country')

                # Add geocodes only if they are provided
                if filters.get('end_geo_lat') and filters.get('end_geo_long'):
                    # Format geocodes as a comma-separated string as expected by Amadeus API
                    payload["endGeoCode"] = f"{filters.get('end_geo_lat')},{filters.get('end_geo_long')}"
            else:
                # If no specific address is provided, use the dropoff_location code
                payload["endLocationCode"] = dropoff_location

                # Even with a location code, if geocodes are provided, include them
                if filters.get('end_geo_lat') and filters.get('end_geo_long'):
                    payload["endGeoCode"] = f"{filters.get('end_geo_lat')},{filters.get('end_geo_long')}"

            # Add connected flight details if available
            if filters.get('connected_flight') or filters.get('flight_number'):
                flight_number = filters.get('connected_flight') or filters.get('flight_number')
                if flight_number:
                    payload["flightNumber"] = flight_number

                    if filters.get('flight_arrival_time'):
                        payload["flightArrivalTime"] = filters.get('flight_arrival_time')

            # Add price filter if provided
            if filters.get('price_min'):
                payload["minPrice"] = filters.get('price_min')

            if filters.get('price_max'):
                payload["maxPrice"] = filters.get('price_max')

            # Add vehicle type filter if provided
            if filters.get('vehicle_type'):
                payload["vehicleType"] = filters.get('vehicle_type')

            logger.info(f"Sending request to Amadeus API with payload: {payload}")

            # Make the API request
            url = f"{self.base_url}/v1/shopping/transfer-offers"

            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload
            )

            # Handle different error scenarios
            if response.status_code != 200:
                error_msg = f"Amadeus API error: {response.status_code} - {response.text}"
                logger.error(error_msg)

                # Handle token expiration (401 error)
                if response.status_code == 401:
                    # Check if it's a token expiration error
                    try:
                        error_data = response.json()
                        if 'errors' in error_data and any(e.get('code') == 38192 or 'access token expired' in e.get('detail', '').lower() for e in error_data.get('errors', [])):
                            logger.info("Access token expired. Refreshing token and retrying request.")

                            # Clear the cached token
                            cache.delete('amadeus_token')
                            # Reset the token
                            self.token = None
                            # Get a new token
                            self.token = self.get_auth_token()

                            # Retry the request with the new token
                            response = requests.post(
                                url,
                                headers=self._get_headers(),
                                json=payload
                            )

                            if response.status_code == 200:
                                response_data = response.json()
                                if 'data' in response_data:
                                    results = self._process_transfer_response(response_data['data'], filters)
                                    cache.set(cache_key, results, 600)
                                    return results
                    except Exception as e:
                        logger.error(f"Error handling token refresh: {e}", exc_info=True)

                # If we still don't have a successful response
                if "NEED GEOCODES OF THE ADDRESS" in response.text:
                    return [{"error": "Geocodes required for this address. Please provide end_geo_lat and end_geo_long."}]

                # If we have errors but status code 200, try to process the data anyway
                try:
                    response_data = response.json()
                    if 'errors' in response_data and not response_data.get('data'):
                        # Log errors for debugging
                        logger.error(f"API returned errors: {response_data['errors']}")
                        return []
                except Exception:
                    pass

                return []

            response_data = response.json()

            if 'data' not in response_data:
                logger.error("Unexpected response format from Amadeus API")
                logger.error(f"Full response: {response_data}")
                return []

            # Process the response
            results = self._process_transfer_response(response_data['data'], filters)

            # Cache results for 10 minutes
            cache.set(cache_key, results, 600)

            return results
        except Exception as e:
            logger.error(f"Unexpected error in search_transfers: {e}", exc_info=True)
            return []

    def _process_transfer_response(self, data, filters):
        """
        Process and filter the Amadeus Transfer API response
        """
        results = []

        logger.info(f"Processing response data: {data}")

        if data is None:
            logger.error("Received None data from Amadeus API")
            return results

        # If the response is a single object, convert it to a list
        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            logger.error(f"Unexpected data format: {type(data)}")
            return results

        for item in data:
            # Extract vehicle information
            vehicle = item.get('vehicle', {})

            # Extract price information from quotation
            quotation = item.get('quotation', {})
            price_amount = quotation.get('monetaryAmount')
            price_currency = quotation.get('currencyCode')

            # Extract service provider information
            provider = item.get('serviceProvider', {})

            # Extract location information
            start = item.get('start', {})
            end = item.get('end', {})
            end_address = end.get('address', {}) if end else {}

            # Extract distance information
            distance = item.get('distance', {})

            # Calculate duration from start and end datetime if available
            estimated_duration = None
            if start.get('dateTime') and end.get('dateTime'):
                try:
                    start_time = datetime.datetime.fromisoformat(start['dateTime'])
                    end_time = datetime.datetime.fromisoformat(end['dateTime'])
                    duration_minutes = (end_time - start_time).total_seconds() / 60
                    estimated_duration = f"{int(duration_minutes)} minutes"
                except Exception as e:
                    logger.error(f"Error calculating duration: {e}")

            # Format the result
            transfer_info = {
                'id': item.get('id'),
                'vehicle_type': vehicle.get('code'),
                'vehicle_name': vehicle.get('description'),
                'vehicle_image_url': vehicle.get('imageURL'),  # Added this line to capture vehicle image
                'capacity': vehicle.get('seats', [{}])[0].get('count') if vehicle.get('seats') else None,
                'category': vehicle.get('category'),
                'provider': {
                    'name': provider.get('name'),
                    'code': provider.get('code'),
                    'logo_url': provider.get('logoUrl'),
                    'terms_url': provider.get('termsUrl')
                },
                'price': {
                    'amount': price_amount,
                    'currency': price_currency
                },
                'start_location': {
                    'code': start.get('locationCode'),
                    'datetime': start.get('dateTime')
                },
                'end_location': {
                    'address': end_address.get('line'),
                    'city': end_address.get('cityName'),
                    'zipcode': end_address.get('zip'),
                    'country': end_address.get('countryCode'),
                    'coordinates': {
                        'latitude': end_address.get('latitude'),
                        'longitude': end_address.get('longitude')
                    } if end_address.get('latitude') and end_address.get('longitude') else None,
                    'datetime': end.get('dateTime')
                },
                'estimated_duration': estimated_duration,
                'distance': {
                    'value': distance.get('value'),
                    'unit': distance.get('unit')
                } if distance else None,
                'cancellation_rules': item.get('cancellationRules', []),
                'transfer_type': item.get('transferType'),
                'methods_of_payment': item.get('methodsOfPaymentAccepted', []),
                'extra_services': item.get('extraServices', []),  # Added extra services information
                'passenger_characteristics': item.get('passengerCharacteristics', [])  # Added passenger details
            }

            # Apply filters if specified
            if filters.get('vehicle_type') and transfer_info['vehicle_type'] != filters['vehicle_type']:
                continue

            if (filters.get('price_min') or filters.get('price_max')) and price_amount:
                price = float(price_amount)
                if filters.get('price_min') and price < float(filters['price_min']):
                    continue
                if filters.get('price_max') and price > float(filters['price_max']):
                    continue

            results.append(transfer_info)

        return results

    # def create_transfer_booking(self, booking_data, transfer_id):
    #     """
    #     Create a transfer booking with Amadeus API
    #     """
    #     try:
    #         # Include the transfer offer ID as a query parameter
    #         url = f"{self.base_url}/v1/ordering/transfer-orders?offerId={transfer_id}"
    #         headers = self._get_headers()

    #         logger.info(f"Creating transfer booking with payload: {booking_data}")

    #         response = requests.post(
    #             url,
    #             headers=headers,
    #             json=booking_data
    #         )

    #         # Handle token expiration (401 error)
    #         if response.status_code == 401:
    #             error_data = response.json()
    #             if 'errors' in error_data and any(e.get('code') == 38192 or 'access token expired' in e.get('detail', '').lower() for e in error_data.get('errors', [])):
    #                 logger.info("Access token expired. Refreshing token and retrying request.")
    #                 cache.delete('amadeus_token')
    #                 self.token = None
    #                 headers = self._get_headers()

    #                 response = requests.post(
    #                     url,
    #                     headers=headers,
    #                     json=booking_data
    #                 )

    #         if response.status_code == 201:
    #             return response
    #         else:
    #             logger.error(f"Failed to create transfer booking: {response.status_code} - {response.text}")
    #             return response

    #     except Exception as e:
    #         logger.error(f"Unexpected error in create_transfer_booking: {e}", exc_info=True)
    #         raise

    def create_transfer_booking(self, booking_data, transfer_id):
        """
        Create a transfer booking with Amadeus API
        """
        try:
            # Include the transfer offer ID as a query parameter
            url = f"{self.base_url}/v1/ordering/transfer-orders?offerId={transfer_id}"
            headers = self._get_headers()

            logger.info(f"Creating transfer booking with payload: {booking_data}")

            response = requests.post(
                url,
                headers=headers,
                json=booking_data
            )

            # Log Ama-request-Id from response headers
            ama_request_id = response.headers.get('Ama-request-Id')
            logger.info(f"Ama-request-Id: {ama_request_id}")

            # Handle token expiration (401 error)
            if response.status_code == 401:
                error_data = response.json()
                if 'errors' in error_data and any(e.get('code') == 38192 or 'access token expired' in e.get('detail', '').lower() for e in error_data.get('errors', [])):
                    logger.info("Access token expired. Refreshing token and retrying request.")
                    cache.delete('amadeus_token')
                    self.token = None
                    headers = self._get_headers()

                    response = requests.post(
                        url,
                        headers=headers,
                        json=booking_data
                    )

                    # Log Ama-request-Id for retry response
                    ama_request_id = response.headers.get('Ama-request-Id')
                    logger.info(f"Ama-request-Id after retry: {ama_request_id}")

            if response.status_code == 201:
                return response
            else:
                logger.error(f"Failed to create transfer booking: {response.status_code} - {response.text}")
                return response

        except Exception as e:
            logger.error(f"Unexpected error in create_transfer_booking: {e}", exc_info=True)
            raise

    def cancel_transfer_booking(self, booking_reference, confirmation_number=None):
        """
        Cancel a transfer booking with Amadeus API
        """
        try:
            url = f"{self.base_url}/v1/ordering/transfer-orders/{booking_reference}/transfers/cancellation"

            # Add confirmation number as query parameter if provided
            if confirmation_number:
                url += f"?confirmNbr={confirmation_number}"

            headers = self._get_headers()

            logger.info(f"Cancelling transfer booking: {booking_reference}")

            response = requests.delete(
                url,
                headers=headers
            )

            # Handle token expiration (401 error)
            if response.status_code == 401:
                error_data = response.json()
                if 'errors' in error_data and any(e.get('code') == 38192 or 'access token expired' in e.get('detail', '').lower() for e in error_data.get('errors', [])):
                    logger.info("Access token expired. Refreshing token and retrying request.")
                    cache.delete('amadeus_token')
                    self.token = None
                    headers = self._get_headers()

                    response = requests.delete(
                        url,
                        headers=headers
                    )

            if response.status_code == 200:
                return response
            else:
                logger.error(f"Failed to cancel transfer booking: {response.status_code} - {response.text}")
                return response

        except Exception as e:
            logger.error(f"Unexpected error in cancel_transfer_booking: {e}", exc_info=True)
            raise

    def get_transfer_booking_details(self, booking_reference):
        """
        Get details of a specific transfer booking
        """
        try:
            url = f"{self.base_url}/v1/booking/transfer-bookings/{booking_reference}"
            headers = self._get_headers()

            logger.info(f"Getting transfer booking details: {booking_reference}")

            response = requests.get(
                url,
                headers=headers
            )

            # Handle token expiration (401 error)
            if response.status_code == 401:
                error_data = response.json()
                if 'errors' in error_data and any(e.get('code') == 38192 or 'access token expired' in e.get('detail', '').lower() for e in error_data.get('errors', [])):
                    logger.info("Access token expired. Refreshing token and retrying request.")
                    cache.delete('amadeus_token')
                    self.token = None
                    headers = self._get_headers()

                    response = requests.get(
                        url,
                        headers=headers
                    )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get transfer booking details: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Unexpected error in get_transfer_booking_details: {e}", exc_info=True)
            return None

    def _process_booking_response(self, response_data):
        """
        Process the booking confirmation response from Amadeus
        """
        try:
            if not response_data or 'data' not in response_data:
                logger.error("Invalid booking response format")
                return None

            booking_data = response_data['data']

            return {
                'booking_reference': booking_data.get('id'),
                'status': booking_data.get('status'),
                'provider_reference': booking_data.get('providerConfirmationNumber'),
                'vehicle': booking_data.get('vehicle', {}),
                'pickup_details': booking_data.get('pickup', {}),
                'dropoff_details': booking_data.get('dropoff', {}),
                'passenger_count': booking_data.get('passengerCount'),
                'price': booking_data.get('price', {}),
                'cancellation_policy': booking_data.get('cancellationPolicy', {}),
                'created_at': booking_data.get('createdAt'),
                'updated_at': booking_data.get('updatedAt')
            }
        except Exception as e:
            logger.error(f"Error processing booking response: {e}", exc_info=True)
            return None

import requests
from django.conf import settings
from django.core.cache import cache
from typing import Dict, List, Any, Optional
import json

class AmadeusAPI:
    """
    Utility class for interacting with the Amadeus API
    """

    def __init__(self):
        self.client_id = settings.AMADEUS_API_TEST_KEY if settings.AMADEUS_API_TESTING else settings.AMADEUS_API_LIVE_KEY
        self.client_secret = settings.AMADEUS_API_TEST_SECRET if settings.AMADEUS_API_TESTING else settings.AMADEUS_API_LIVE_SECRET
        self.base_url = 'https://test.api.amadeus.com'  # Use 'https://api.amadeus.com' for production
        self.token = None

    def get_auth_token(self) -> str:
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

        response = requests.post(url, data=payload)

        if response.status_code == 200:
            data = response.json()
            token = data['access_token']
            # Cache the token for slightly less than its expiry time
            cache.set('amadeus_token', token, timeout=data['expires_in'] - 60)
            return token
        else:
            raise Exception(f"Failed to get authentication token: {response.text}")

    def _get_headers(self) -> Dict:
        """
        Get headers for Amadeus API requests
        """
        if not self.token:
            self.token = self.get_auth_token()

        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def search_flights(self, origin: str, destination: str, departure_date: str,
                  return_date: Optional[str] = None, adults: int = 1,
                  travel_class: str = 'ECONOMY', non_stop: bool = False,
                  currency: str = 'USD', max_results: int = 20) -> Dict:

        url = f"{self.base_url}/v2/shopping/flight-offers"

        payload = {
            'originLocationCode': origin,
            'destinationLocationCode': destination,
            'departureDate': departure_date,
            'adults': adults,
            'travelClass': travel_class,
            # Convert boolean to lowercase string
            'nonStop': str(non_stop).lower(),
            'currencyCode': currency,
            'max': max_results
        }

        if return_date:
            payload['returnDate'] = return_date

        response = requests.get(url, headers=self._get_headers(), params=payload)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to search flights: {response.text}")

    def search_multi_city_flights(self, origin_destinations: List[Dict],
                                 adults: int = 1, travel_class: str = 'ECONOMY',
                                 currency: str = 'USD', max_results: int = 20) -> Dict:
        """
        Search for multi-city flights using Amadeus Flight Offers Search API

        Args:
            origin_destinations: List of origin-destination pairs with dates
                [{'origin': 'NYC', 'destination': 'LON', 'date': '2025-06-01'},
                 {'origin': 'LON', 'destination': 'PAR', 'date': '2025-06-05'},
                 {'origin': 'PAR', 'destination': 'NYC', 'date': '2025-06-10'}]
            adults: Number of adults
            travel_class: Travel class (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)
            currency: Currency code
            max_results: Maximum number of results to return

        Returns:
            Dict containing flight offers
        """
        url = f"{self.base_url}/v2/shopping/flight-offers"

        # Prepare origin destinations in the format expected by Amadeus
        origin_destinations_formatted = []
        for od in origin_destinations:
            origin_destinations_formatted.append({
                'id': str(len(origin_destinations_formatted) + 1),
                'originLocationCode': od['origin'],
                'destinationLocationCode': od['destination'],
                'departureDateTimeRange': {
                    'date': od['date']
                }
            })

        travelers = []
        for i in range(adults):
            travelers.append({
                'id': str(i + 1),  # Unique ID for each traveler
                'travelerType': 'ADULT'
            })

        payload = {
            'originDestinations': origin_destinations_formatted,
            'travelers': travelers,
            'sources': ['GDS'],
            'searchCriteria': {
                'maxFlightOffers': max_results,
                'flightFilters': {
                    'cabinRestrictions': [
                        {
                            'cabin': travel_class,
                            'coverage': 'MOST_SEGMENTS',
                            'originDestinationIds': [str(i+1) for i in range(len(origin_destinations_formatted))]
                        }
                    ]
                }
            }
        }

        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to search multi-city flights: {response.text}")

    def price_flight_offers(self, flight_offers: List[Dict]) -> Dict:
        """
        Price flight offers using Amadeus Flight Offers Price API

        Args:
            flight_offers: List of flight offers from the search API
          but
        Returns:
            Dict containing priced flight offers
        """
        url = f"{self.base_url}/v1/shopping/flight-offers/pricing"

        payload = {
            'data': {
                'type': 'flight-offers-pricing',
                'flightOffers': flight_offers
            }
        }

        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to price flight offers: {response.text}")

    def create_flight_order(self, flight_offer: Dict, travelers: List[Dict]) -> Dict:
        """
        Create a flight order using Amadeus Flight Orders API

        Args:
            flight_offer: Flight offer from the pricing API
            travelers: List of traveler information

        Returns:
            Dict containing the created flight order
        """
        url = f"{self.base_url}/v1/booking/flight-orders"

        payload = {
            'data': {
                'type': 'flight-order',
                'flightOffers': [flight_offer],
                'travelers': travelers
            }
        }

        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload
        )

        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to create flight order: {response.text}")

    def get_flight_order(self, order_id: str) -> Dict:
        """
        Get a flight order using Amadeus Flight Orders API

        Args:
            order_id: Flight order ID

        Returns:
            Dict containing the flight order
        """
        url = f"{self.base_url}/v1/booking/flight-orders/{order_id}"

        response = requests.get(
            url,
            headers=self._get_headers()
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get flight order: {response.text}")

    def delete_flight_order(self, order_id: str) -> bool:
        """
        Delete a flight order using Amadeus Flight Orders API

        Args:
            order_id: Flight order ID

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/v1/booking/flight-orders/{order_id}"

        response = requests.delete(
            url,
            headers=self._get_headers()
        )

        return response.status_code == 200

    def search_airports(self, keyword, subType=None):
        """
        Search for airports using the Amadeus API
        """
        try:
            print(f"[DEBUG] Searching airports with keyword: {keyword}, subType: {subType}")
            print(f"[DEBUG] Base URL: {self.base_url}")

            headers = self._get_headers()
            print(f"[DEBUG] Headers (truncated auth): {headers}")

            params = {
                'keyword': keyword,
                'subType': ','.join(subType) if subType else 'AIRPORT,CITY'
            }
            print(f"[DEBUG] Request params: {params}")

            response = requests.get(
                f"{self.base_url}/v1/reference-data/locations",
                headers=headers,
                params=params
            )

            print(f"[DEBUG] Amadeus API Status Code: {response.status_code}")
            print(f"[DEBUG] Amadeus API Response Headers: {response.headers}")

            if response.status_code != 200:
                print(f"[DEBUG] Error response: {response.text}")

            response_json = response.json()
            print(f"[DEBUG] Response JSON: {json.dumps(response_json, indent=2)}")

            return response_json
        except json.JSONDecodeError as je:
            print(f"[DEBUG] JSON Decode Error: {str(je)}")
            print(f"[DEBUG] Raw response: {response.text}")
            raise Exception(f"Error parsing Amadeus response: {str(je)}")
        except requests.RequestException as re:
            print(f"[DEBUG] Request Exception: {str(re)}")
            raise Exception(f"Error connecting to Amadeus API: {str(re)}")
        except Exception as e:
            print(f"[DEBUG] Unexpected error: {str(e)}")
            print(f"[DEBUG] Error type: {type(e).__name__}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            raise Exception(f"Error searching airports: {str(e)}")


    def search_cities(self, keyword, country_code=None, max_results=10, include=None):
        """
        Search for cities and their airports using the Amadeus API
        """
        try:
            params = {
                'keyword': keyword,
                'max': max_results
            }

            # Add optional parameters if provided
            if country_code:
                params['countryCode'] = country_code
            if include:
                params['include'] = include

            response = requests.get(
                f"{self.base_url}/v1/reference-data/locations/cities",
                headers=self._get_headers(),
                params=params
            )

            return response.json()
        except Exception as e:
            raise Exception(f"Error searching cities: {str(e)}")

    def get_flight_details(self, flight_id: str) -> Dict:
        """
        Retrieve details of a specific flight offer by ID from cache

        Args:
            flight_id (str): The ID of the flight offer

        Returns:
            Dict: Flight offer details
        """
        # Try to get from cache
        cache_key = f"flight_offer_{flight_id}"
        flight_details = cache.get(cache_key)

        if flight_details:
            return flight_details

        # If not in cache, we need to inform the user
        # that the flight details are no longer available
        raise Exception("Flight details not found. Please perform a new search.")

from amadeus import Client
from django.conf import settings
import inspect
import logging

logger = logging.getLogger(__name__)

class AmadeusClient:
    def __init__(self):
        # Determine keys based on the environment
        self.api_key = (
            settings.AMADEUS_API_TEST_KEY if settings.AMADEUS_API_TESTING else settings.AMADEUS_API_LIVE_KEY
        )
        self.api_secret = (
            settings.AMADEUS_API_TEST_SECRET if settings.AMADEUS_API_TESTING else settings.AMADEUS_API_LIVE_SECRET
        )

        # Initialize Amadeus Client
        try:
            self.client = Client(
                client_id=self.api_key,
                client_secret=self.api_secret,
                hostname="test" if settings.AMADEUS_API_TESTING else "production"
            )
            logger.info("Amadeus client initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing Amadeus client: {e}")
            self.client = None

    def get_client(self):
        if not self.client:
            raise ValueError("Amadeus client is not initialized properly.")
        return self.client


# Global instance to use throughout the application
amadeus_client = AmadeusClient().get_client()

# print(amadeus_client.shopping.hotel_offers_search.get.__doc__, "xxxxxxxxxxxxxxxxxxxxxxxxxxx")
print(amadeus_client.reference_data.locations.hotels.by_city.get.__doc__, "mmmmmmmmmmmmmmmmmmmmmmmmm")
# print("cccccccccccccccccccccccccccccccccccccccc")
# help(amadeus_client.reference_data.locations.hotels.by_city.get)
# print(inspect.signature(amadeus_client.reference_data.locations.hotels.by_city.get),",,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,")
# print("ccccccccccccccccccccccccccccccccccccccccccccccc")
# print(dir(amadeus_client.shopping.hotel_offers_search), "ooooooooooooooooooooooooo")
# help(amadeus_client.shopping.hotel_offers_search.get)
# help(amadeus_client.reference_data.locations.hotels.by_city.get)
# print(dir(amadeus_client), "<<<<<<<<<<<<<<====================>>>>>>>>>>>>>>>>>")
# print(dir(amadeus_client.shopping), "<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>")
# print(dir(amadeus_client.shopping.hotel_offers_search), "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")
# print(amadeus_client.booking.hotel_bookings.post.__doc__, "qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq")

# print(dir(amadeus_client.reference_data), "zzz/zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")
# print(dir(amadeus_client.reference_data.locations), "OOOOOOOOOOOOOOOOOOOOOOO")
# print(dir(amadeus_client.reference_data.locations.hotels), "mmmmmmmmmmmmmmmmmmmmmmmmmmmmm")

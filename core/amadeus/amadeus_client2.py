import logging
from amadeus import Client as AmadeusClientBase
from django.conf import settings

logger = logging.getLogger(__name__)

class BookingAmadeusClient:
    def __init__(self):
        self.environment = "test" if settings.AMADEUS_API_TESTING else "production"
        self.credentials = self._get_credentials()
        self.client = self._initialize_client()

    def _get_credentials(self):
        return {
            "client_id": settings.AMADEUS_API_TEST_KEY if settings.AMADEUS_API_TESTING else settings.AMADEUS_API_LIVE_KEY,
            "client_secret": settings.AMADEUS_API_TEST_SECRET if settings.AMADEUS_API_TESTING else settings.AMADEUS_API_LIVE_SECRET
        }

    def _initialize_client(self):
        return AmadeusClientBase(
            client_id=self.credentials["client_id"],
            client_secret=self.credentials["client_secret"],
            hostname=self.environment
        )

    def get_client(self):
        return self.client

from amadeus import Client
from django.conf import settings

class AmadeusClient:
    def __init__(self):
        # Determine keys based on environment
        self.api_key = (
            settings.AMADUS_API_TEST_KEY if settings.AMADUS_API_TESTING else settings.AMADUS_API_LIVE_KEY
        )
        self.api_secret = (
            settings.AMADUS_API_TEST_SECRET if settings.AMADUS_API_TESTING else settings.AMADUS_API_LIVE_SECRET
        )

        # Set the correct API environment
        self.client = Client(
            client_id=self.api_key,
            client_secret=self.api_secret,
            hostname="test" if settings.AMADUS_API_TESTING else "production",
        )

    def get_client(self):
        return self.client


# Create a global instance
amadeus_client = AmadeusClient().get_client()

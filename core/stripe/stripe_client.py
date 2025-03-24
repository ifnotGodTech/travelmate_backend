import stripe
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class StripeClient:
    def __init__(self):
        # Use test keys if in testing mode, else use live keys
        self.api_key = settings.STRIPE_PUBLISHABLE_TEST_KEY if settings.STRIPE_API_TESTING else settings.STRIPE_SECRET_LIVE_KEY

        # Initialize Stripe with the selected API key
        try:
            stripe.api_key = self.api_key
            self.client = stripe
            logger.info("Stripe client initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing Stripe client: {e}")
            self.client = None

    def get_client(self):
        if not self.client:
            raise ValueError("Stripe client is not initialized properly.")
        return self.client


# Create a global instance to use throughout the app
stripe_client = StripeClient().get_client()
print(dir(stripe_client), "<<<<<<<<<<<<<< Stripe Methods >>>>>>>>>>>>>>")

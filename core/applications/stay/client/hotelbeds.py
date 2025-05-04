import hashlib
import logging
import requests
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)

class HotelbedsAPIClient:
    def __init__(self):
        # Get configuration from settings
        config = settings.HOTELBEDS_CONFIG
        self.use_test_env = config.get("testing", True)

        # Determine environment-specific configurations
        env_config = config["test"] if self.use_test_env else config["production"]

        self.api_key = env_config.get("api_key")
        self.api_secret = env_config.get("api_secret")
        self.base_url = env_config.get("base_url", "").rstrip("/") + "/hotel-api/1.0/"

        if not self.api_key or not self.api_secret:
            raise ValueError("Hotelbeds API credentials are not set correctly.")

        mode = "TEST" if self.use_test_env else "PRODUCTION"
        logger.info(f"Initialized Hotelbeds client in {mode} mode")

    def _generate_signature(self):
        """
        Generate SHA256 signature: SHA256(apiKey + sharedSecret + timestamp)
        """
        try:
            timestamp = str(int(datetime.utcnow().timestamp()))  # Timestamp in seconds
            raw_string = self.api_key + self.api_secret + timestamp
            signature = hashlib.sha256(raw_string.encode('utf-8')).hexdigest()
            logger.debug(f"Generated signature: {signature} at {timestamp}")
            return signature, timestamp
        except Exception as e:
            logger.error(f"Signature generation failed: {e}")
            raise

    def _get_headers(self):
        """
        Prepare request headers including the generated signature.
        """
        signature, timestamp = self._generate_signature()
        return {
            'Api-Key': self.api_key,
            'X-Signature': signature,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Timestamp': timestamp  # Add timestamp to the header
        }

    def _send_request(self, method, endpoint, payload=None):
        """
        Generic method to send GET, POST, etc. requests.
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            logger.info(f"Making {method} request to {url} with payload: {payload}")
            response = requests.request(method, url, json=payload, headers=headers, timeout=30)

            # Check for successful response
            logger.info(f"Received response {response.status_code}")
            response.raise_for_status()  # Raise exception for HTTP errors (4xx, 5xx)
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.error("Authentication failed: Request signature verification failed")
            logger.error(f"Request failed with status {response.status_code}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to {url} failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
            raise

    def search_hotels(self, payload):
        """
        Make a POST request to the Hotelbeds hotels endpoint.
        """
        try:
            return self._send_request("POST", "hotels", payload)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

# __init__.py
from .amadeus_client import AmadeusClient as GeneralAmadeusClient, amadeus_client
from .amadeus_client2 import BookingAmadeusClient

__all__ = [
    "GeneralAmadeusClient",
    "BookingAmadeusClient",
    "amadeus_client"
]

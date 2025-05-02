class HotelbedsAPIError(Exception):
    """Base exception class for all Hotelbeds API-related errors.

    Attributes:
        message (str): Human-readable error description.
        status_code (int, optional): HTTP status code if applicable.
        details (dict, optional): Additional error details from the API.
    """
    def __init__(self, message: str, status_code: int = None, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class HotelbedsValidationError(HotelbedsAPIError):
    """Raised when input data fails validation before sending to Hotelbeds API.

    Example:
        >>> raise HotelbedsValidationError("Check-in date cannot be in the past")
    """
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=400, details=details)


class HotelbedsAuthenticationError(HotelbedsAPIError):
    """Raised when API authentication fails (invalid API key, expired token, etc.).

    Example:
        >>> raise HotelbedsAuthenticationError("Invalid API key", status_code=401)
    """
    def __init__(self, message: str, status_code: int = 401, details: dict = None):
        super().__init__(message, status_code, details)


class HotelbedsRateLimitError(HotelbedsAPIError):
    """Raised when the Hotelbeds API rate limit is exceeded.

    Example:
        >>> raise HotelbedsRateLimitError("API rate limit exceeded", status_code=429)
    """
    def __init__(self, message: str, status_code: int = 429, details: dict = None):
        super().__init__(message, status_code, details)


class HotelbedsBookingError(HotelbedsAPIError):
    """Raised when a booking operation fails (e.g., insufficient inventory, payment declined).

    Example:
        >>> raise HotelbedsBookingError("Room no longer available", status_code=400)
    """
    def __init__(self, message: str, status_code: int = 400, details: dict = None):
        super().__init__(message, status_code, details)

import base64
from datetime import datetime
from time import sleep

import hashlib
import hmac
import secrets
import time
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

import pyotp
from django.conf import settings

from core.applications.users.models import User


class TokenGenerator:
    """
    A secure token generator for password reset mechanisms using HOTP (HMAC-based One-Time Password).

    The generated token is a 4-digit numeric code consisting of:
    - 2 digits from the timestamp (ensuring freshness).
    - 2-digit OTP (ensuring security).

    This ensures that tokens are unique, time-sensitive, and secure.
    """

    key_salt = "django.contrib.auth.tokens.PasswordResetTokenGenerator"
    algorithm = None
    _secret = None

    def __init__(self):
        """Initialize the token generator with a default hashing algorithm."""
        self.algorithm = self.algorithm or "sha256"

    @property
    def secret(self):
        """
        Returns the secret key used for token generation.
        Falls back to Django's SECRET_KEY if not explicitly set.
        """
        return self._secret or settings.SECRET_KEY

    @secret.setter
    def secret(self, value):
        """Allows setting a custom secret key for token generation."""
        self._secret = value

    def make_token(self, user: User) -> str:
        """
        Generates a unique 4-digit token for password reset.

        The function ensures that the token always has 4 digits by recursively
        regenerating if necessary (though this should rarely happen).

        Args:
            user (User): The user requesting the password reset.

        Returns:
            str: A 4-digit token.
        """
        sleep(1)  # Prevent brute force attacks by introducing a slight delay.
        token = self._make_token_with_timestamp(user, self._num_seconds(self._now()))
        DIGIT = 4
        return token if len(token) == DIGIT else self.make_token(user)

    def check_token(self, user: User, token: str) -> bool:
        """
        Validates whether the given token is correct for the user.

        Args:
            user (User): The user attempting to use the token.
            token (str): The token provided for verification.

        Returns:
            bool: True if the token is valid, False otherwise.
        """
        if not (user and token):
            return False

        # Ensure token length is exactly 4 characters
        if len(token) != 4:
            return False

        try:
            # Split the token into timestamp part and OTP part
            ts_part, otp = token[:2], token[2:]
        except ValueError:
            return False

        # Generate the expected OTP
        hash_val = base64.b32encode(self._make_hash_value(user, ts_part).encode())
        OTP = pyotp.HOTP(hash_val, digits=2)

        return OTP.verify(int(otp), int(ts_part))

    def _make_token_with_timestamp(self, user: User, timestamp: int) -> str:
        """
        Generates a token using a hashed timestamp and OTP.

        Args:
            user (User): The user requesting the token.
            timestamp (int): The current timestamp.

        Returns:
            str: A 4-digit token.
        """
        ts_part = self._get_timestamp_digits(
            str(timestamp),
        )  # Extract last 2 digits of timestamp
        key = base64.b32encode(self._make_hash_value(user, ts_part).encode())

        OTP = pyotp.HOTP(key, digits=2)  # Generate 2-digit OTP
        otp = OTP.at(int(ts_part))  # Generate OTP based on timestamp

        return f"{ts_part}{otp}"  # Ensure 4-digit token

    def _make_hash_value(self, user: User, timestamp: str) -> str:
        """
        Creates a unique hash value for the user and timestamp.

        This ensures token uniqueness by incorporating:
        - The user's primary key
        - The hashed password (which changes on reset)
        - The last login timestamp (if available)
        - The email address (if available)

        Args:
            user (User): The user for whom the token is generated.
            timestamp (str): The timestamp segment included in the token.

        Returns:
            str: A hashed string for token generation.
        """
        login_timestamp = (
            ""
            if user.last_login is None
            else user.last_login.replace(microsecond=0, tzinfo=None)
        )
        email = getattr(user, user.get_email_field_name(), "") or ""
        return f"{user.pk}{user.password}{login_timestamp}{timestamp}{email}"

    def _get_timestamp_digits(self, timestamp: str) -> str:
        """
        Extracts the last 2 digits of the timestamp.

        Args:
            timestamp (str): The full timestamp string.

        Returns:
            str: A 2-character string representing the last two digits of the timestamp.
        """
        return timestamp[-2:]

    def _num_seconds(self, dt: datetime) -> int:
        """
        Converts a datetime object into seconds since January 1, 2001.

        Args:
            dt (datetime): The current datetime.

        Returns:
            int: Number of seconds since 2001-01-01.
        """
        return int((dt - datetime(2001, 1, 1)).total_seconds())

    def _now(self) -> datetime:
        """
        Returns the current timestamp.

        Used to allow for easy mocking in unit tests.

        Returns:
            datetime: The current timestamp.
        """
        return datetime.now()


class InvitationTokenGenerator:
    """
    Token generator for email invitations to non-users.

    Generates secure tokens with expiry based on
    HMAC-SHA256(email + timestamp + secret).
    """

    key_salt = "core.applications.users.tokens.InvitationTokenGenerator.TravelMate"
    timeout = 60 * 60 * 24 * 7  # 7 days expiry

    def make_token(self, email: str) -> str:
        timestamp = int(time.time())
        ts_b64 = urlsafe_base64_encode(force_bytes(str(timestamp)))
        email_b64 = urlsafe_base64_encode(force_bytes(email))
        nonce = secrets.token_urlsafe(24)  # Adds randomness

        hash_value = f"{email}{timestamp}{nonce}{self.key_salt}"
        digest = hmac.new(
            key=force_bytes(settings.SECRET_KEY),
            msg=force_bytes(hash_value),
            digestmod=hashlib.sha512,
        ).hexdigest()

        return f"{email_b64}.{ts_b64}.{nonce}.{digest}"

    def check_token(self, token: str) -> str | None:
        try:
            email_b64, ts_b64, nonce, digest = token.split(".")
            email = urlsafe_base64_decode(email_b64).decode()
            timestamp = int(urlsafe_base64_decode(ts_b64).decode())
        except Exception:
            return None

        if int(time.time()) - timestamp > self.timeout:
            return None

        expected_hash_value = f"{email}{timestamp}{nonce}{self.key_salt}"
        expected_digest = hmac.new(
            key=force_bytes(settings.SECRET_KEY),
            msg=force_bytes(expected_hash_value),
            digestmod=hashlib.sha512,
        ).hexdigest()

        if hmac.compare_digest(digest, expected_digest):
            return email
        return None

# Create a default instance of the token generator
default_token_generator = TokenGenerator()

# A default instance for usage elsewhere
default_invitation_token_generator = InvitationTokenGenerator()

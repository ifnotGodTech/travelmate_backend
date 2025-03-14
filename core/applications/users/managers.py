from typing import TYPE_CHECKING
import base64
import pyotp
from django.core.cache import cache
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager as DjangoUserManager

if TYPE_CHECKING:
    from .models import User  # noqa: F401


class UserManager(DjangoUserManager["User"]):
    """Custom manager for the User model."""

    def _create_user(self, email: str, password: str | None, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            msg = "The given email must be set"
            raise ValueError(msg)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            msg = "Superuser must have is_staff=True."
            raise ValueError(msg)
        if extra_fields.get("is_superuser") is not True:
            msg = "Superuser must have is_superuser=True."
            raise ValueError(msg)

        return self._create_user(email, password, **extra_fields)


class OTPManager:
    """
    Handles OTP generation, storage, and verification.
    """

    @staticmethod
    def generate_otp(email: str) -> str:
        """
        Generate a 4-digit OTP for email verification and store it in cache.
        Args:
            email (str): The email for which OTP is being generated.

        Returns:
            str: The generated OTP.
        """
        secret_key = base64.b32encode(email.encode()).decode()  # Use email as key base
        otp = pyotp.HOTP(secret_key, digits=4).at(0)  # Generate 4-digit OTP

        # Store OTP in cache with 5-minute expiration
        cache.set(email, otp, timeout=300)  # 5 minutes expiry
        return otp

    @staticmethod
    def verify_otp(email: str, otp: str) -> bool:
        """
        Verify the OTP entered by the user.
        Args:
            email (str): The email to validate OTP against.
            otp (str): The OTP entered by the user.

        Returns:
            bool: True if OTP is valid, else False.
        """
        stored_otp = cache.get(email)  # Retrieve OTP from cache
        if stored_otp and stored_otp == otp:
            cache.delete(email)  # Remove OTP after successful verification
            return True
        return False

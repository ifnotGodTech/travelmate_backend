import base64
import pyotp
from django.core.cache import cache


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

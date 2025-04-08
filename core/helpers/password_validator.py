import re

# from core.helpers.custom_exceptions import CustomError
from django.core.exceptions import ValidationError


# def validate_password_strength(password):
#     """
#     Validates password strength:
#     - At least 8 characters
#     - One uppercase letter
#     - One lowercase letter
#     - One digit
#     - One special character
#     """
#     if len(password) < 8:
#         msg = "Password must be at least 8 characters long."
#         raise CustomError.BadRequest({"password": msg})
#     if not re.search(r"[A-Z]", password):
#         msg = "Password must contain at least one uppercase letter."
#         raise CustomError.BadRequest({"password": msg})
#     if not re.search(r"[a-z]", password):
#         msg = "Password must contain at least one lowercase letter."
#         raise CustomError.BadRequest({"password": msg})
#     if not re.search(r"\d", password):
#         msg = "Password must contain at least one digit."
#         raise CustomError.BadRequest({"password": msg})
#     if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
#         msg = "Password must contain at least one special character."
#         raise CustomError.BadRequest({"password": msg})
#     return password


class CustomPasswordValidator:
    """Enforces strong password rules."""

    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        if not any(char.isdigit() for char in password):
            raise ValidationError("Password must contain at least one digit.")
        if not any(char.isupper() for char in password):
            raise ValidationError("Password must contain at least one uppercase letter.")
        if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/~" for char in password):
            raise ValidationError("Password must contain at least one special character.")
        if "password" in password.lower():
            raise ValidationError("Password should not contain the word 'password'.")

    def get_help_text(self):
        return "Your password must be at least 8 characters long, include one uppercase letter, one number, and one special character."

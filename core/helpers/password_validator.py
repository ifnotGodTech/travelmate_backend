import re

from core.helpers.custom_exceptions import CustomError


def validate_password_strength(password):
    """
    Validates password strength:
    - At least 8 characters
    - One uppercase letter
    - One lowercase letter
    - One digit
    - One special character
    """
    if len(password) < 8:
        msg = "Password must be at least 8 characters long."
        raise CustomError.BadRequest({"password": msg})
    if not re.search(r"[A-Z]", password):
        msg = "Password must contain at least one uppercase letter."
        raise CustomError.BadRequest({"password": msg})
    if not re.search(r"[a-z]", password):
        msg = "Password must contain at least one lowercase letter."
        raise CustomError.BadRequest({"password": msg})
    if not re.search(r"\d", password):
        msg = "Password must contain at least one digit."
        raise CustomError.BadRequest({"password": msg})
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        msg = "Password must contain at least one special character."
        raise CustomError.BadRequest({"password": msg})
    return password

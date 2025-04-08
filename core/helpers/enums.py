from django.db.models import TextChoices


class GenderChoice(TextChoices):
    MALE = ("Male", "Male")
    FEMALE = ("Female", "Female")


class BookingStatus(TextChoices):
    PENDING = ("Pending", "Pending")
    CONFIRMED = ("Confirmed", "Confirmed")
    CHECKED_IN = ("Checked In", "Checked In")
    CHECKED_OUT = ("Checked Out", "Checked Out")
    CANCELLED = ("Cancelled", "Cancelled")
    REFUNDED = ("Refunded", "Refunded")


class Account_Delete_Reason_Choices(TextChoices):
    FOUND_ANOTHER_APP = ("Found another app", "Found another app")
    TOO_MANY_NOTIFICATIONS = ("Too many notifications", "Too many notifications")
    OVERLOADED_WITH_CONTENT = ("Overloaded with content", "Overloaded with content")
    SECURITY_CONCERN = ("Security concern", "Security concern")
    OTHERS = ("Others", "Others")

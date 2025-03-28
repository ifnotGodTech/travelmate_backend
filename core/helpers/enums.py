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

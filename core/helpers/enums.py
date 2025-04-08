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

class BookingType(TextChoices):
    CAR = "car", "Car Rental"
    FLIGHT = "flight", "Flight"
    HOTEL = "hotel", "Hotel"

class PassengerGenderChoice(TextChoices):
    MALE = ("M", "Male")
    FEMALE = ("F", "Female")
    OTHER = ("O", "Other")


class FlightBookingTypeChoice(TextChoices):
    ONE_WAY = ("ONE_WAY", "One Way")
    ROUND_TRIP = ("ROUND_TRIP", "Round Trip")
    MULTI_CITY = ("MULTI_CITY", "Multi City")


class PassengerTitleChoice(TextChoices):
    MR = ("MR", "Mr")
    MS = ("MS", "Ms")
    MRS = ("MRS", "Mrs")
    MISS = ("MISS", "Miss")
    DR = ("DR", "Dr")

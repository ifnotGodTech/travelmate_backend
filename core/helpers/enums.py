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

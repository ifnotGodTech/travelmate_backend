from django.db import models
from core.applications.users.models import User
from core.applications.stay.models import Booking
from django.utils import timezone
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
import auto_prefetch
from core.helpers.enums import PassengerGenderChoice, FlightBookingTypeChoice, PassengerTitleChoice


class ServiceFeeSetting(models.Model):
    """
    Model to store and manage service fee settings
    """
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Service Fee: {self.percentage}%"

    @classmethod
    def get_current_fee(cls):
        """
        Get the currently active service fee
        """
        try:
            return cls.objects.filter(is_active=True).latest('created_at').percentage
        except cls.DoesNotExist:
            # Fallback to a default if no active fee is set
            return Decimal('5.00')

class Passenger(models.Model):
    TITLE_CHOICES = [
        ('MR', 'Mr'),
        ('MS', 'Ms'),
        ('MRS', 'Mrs'),
        ('MISS', 'Miss'),
        ('DR', 'Dr'),
    ]

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    title = models.CharField(max_length=4, choices=PassengerTitleChoice.choices)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=PassengerGenderChoice.choices)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    passport_number = models.CharField(max_length=50, blank=True, null=True)
    passport_expiry = models.DateField(blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True, null=True)
    address_line1 = models.CharField(max_length=100, blank=True, null=True)
    address_line2 = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=2, blank=True, null=True)

    def clean(self):
        super().clean()
        if self.phone:
            # Remove all non-digit characters
            self.phone = ''.join(filter(str.isdigit, self.phone))
            # Ensure minimum length
            if len(self.phone) < 6:
                raise ValidationError("Phone number must be at least 6 digits")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class FlightBooking(auto_prefetch.Model):
    """
    Flight-specific booking details that extend the base Booking model
    """


    booking = auto_prefetch.OneToOneField(
        'stay.Booking',
        on_delete=models.CASCADE,
        related_name='flight_booking'
    )

    def generate_booking_reference():
        """Generate a unique booking reference"""
        return uuid.uuid4().hex[:10].upper()

    booking_reference = models.CharField(
        max_length=100,
        unique=True,
        default=generate_booking_reference
    )
    booking_type = models.CharField(max_length=10, choices=FlightBookingTypeChoice.choices)
    currency = models.CharField(max_length=3, default='USD')
    service_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    base_flight_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    admin_notes = models.TextField(blank=True, null=True)
    cancelled_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='cancelled_flight_bookings'
    )
    cancellation_date = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.booking_reference} - {self.booking.user.username}"
    class Meta(auto_prefetch.Model.Meta):
        pass



class Flight(auto_prefetch.Model):
    flight_booking = auto_prefetch.ForeignKey(
        FlightBooking,
        on_delete=models.CASCADE,
        related_name='flights'
    )

    # Basic flight info
    flight_number = models.CharField(max_length=10)
    airline_code = models.CharField(max_length=3)
    airline_name = models.CharField(max_length=100, blank=True)
    operating_airline = models.CharField(max_length=3, blank=True)  # For codeshare flights

    # Departure info
    departure_airport = models.CharField(max_length=3)
    departure_terminal = models.CharField(max_length=10, blank=True)
    departure_city = models.CharField(max_length=100)
    departure_datetime = models.DateTimeField()

    # Arrival info
    arrival_airport = models.CharField(max_length=3)
    arrival_terminal = models.CharField(max_length=10, blank=True)
    arrival_city = models.CharField(max_length=100)
    arrival_datetime = models.DateTimeField()

    # Aircraft info
    aircraft_code = models.CharField(max_length=10, blank=True)
    aircraft_name = models.CharField(max_length=50, blank=True)

    # Segment info
    segment_id = models.CharField(max_length=100)  # From Amadeus API
    number_of_stops = models.PositiveSmallIntegerField(default=0)
    duration = models.DurationField(blank=True, null=True)

    # Fare info
    cabin_class = models.CharField(max_length=20, default='ECONOMY')
    fare_basis = models.CharField(max_length=20, blank=True)  # e.g. 'PI7QUSL1'
    fare_class = models.CharField(max_length=1, blank=True)  # e.g. 'L'
    fare_brand = models.CharField(max_length=50, blank=True)  # e.g. 'BLUE BASIC'
    fare_brand_label = models.CharField(max_length=100, blank=True)
    included_checked_bags = models.PositiveSmallIntegerField(default=0)

    # For multi-city support
    itinerary_index = models.PositiveSmallIntegerField(
        default=0,
        help_text="Index for ordering flights in multi-city itineraries"
    )

    # Additional metadata
    blacklisted_in_eu = models.BooleanField(default=False)
    instant_ticketing_required = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.airline_code}{self.flight_number}: {self.departure_airport} to {self.arrival_airport}"

    class Meta(auto_prefetch.Model.Meta):
        ordering = ['itinerary_index', 'departure_datetime']




class PassengerBooking(auto_prefetch.Model):
    flight_booking = auto_prefetch.ForeignKey(FlightBooking, on_delete=models.CASCADE, related_name='passenger_bookings')
    passenger = auto_prefetch.ForeignKey(Passenger, on_delete=models.CASCADE)
    ticket_number = models.CharField(max_length=50, blank=True, null=True)
    seat_number = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.passenger} - {self.flight_booking.booking_reference}"

class PaymentDetail(auto_prefetch.Model):
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    booking = auto_prefetch.OneToOneField('stay.Booking', on_delete=models.CASCADE, related_name='flight_payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    payment_date = models.DateTimeField(blank=True, null=True)
    additional_details = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.booking.id} - {self.payment_status}"

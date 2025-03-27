from django.db import models
from core.applications.users.models import User
from django.utils import timezone
from decimal import Decimal

class CarServiceFee(models.Model):
    """
    Model for storing car rental service fee configuration
    """
    FEE_TYPE_CHOICES = [
        ('STANDARD', 'Standard Car Rental'),
        ('PREMIUM', 'Premium Cars'),
        ('LUXURY', 'Luxury Vehicles'),
        ('TRANSFER', 'Transfer Service'),
    ]

    fee_type = models.CharField(
        max_length=20,
        choices=FEE_TYPE_CHOICES,
        default='STANDARD'
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),  # Default 10%
        help_text="Percentage fee (e.g., 10.50 for 10.5%)"
    )
    minimum_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text="Minimum fee amount in currency"
    )
    is_active = models.BooleanField(default=True)
    effective_from = models.DateTimeField(default=timezone.now)
    effective_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Car Service Fee"
        verbose_name_plural = "Car Service Fees"
        ordering = ['fee_type']
        constraints = [
            models.UniqueConstraint(
                fields=['fee_type'],
                condition=models.Q(is_active=True),
                name='unique_active_fee_per_type'
            )
        ]

    def __str__(self):
        return f"Car {self.get_fee_type_display()} - {self.percentage}%"

    @classmethod
    def get_current_fee(cls, fee_type='STANDARD'):
        try:
            now = timezone.now()
            fee = cls.objects.get(
                fee_type=fee_type,
                is_active=True,
                effective_from__lte=now,
                effective_to__gte=now
            )
            return {
                'percentage': fee.percentage,
                'minimum_fee': fee.minimum_fee
            }
        except cls.DoesNotExist:
            # Return default values if no active fee configured
            return {
                'percentage': Decimal('10.00'),
                'minimum_fee': Decimal('5.00')
            }



class Location(models.Model):
    code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    airport_code = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.code or self.city or 'Unknown'})"

    class Meta:
        unique_together = ['code', 'city', 'country']

class CarCompany(models.Model):
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='car_companies/', null=True, blank=True)

class CarCategory(models.Model):
    name = models.CharField(max_length=100)  # SUV, Economy, Compact, etc.
    description = models.TextField(blank=True)

class Car(models.Model):
    TRANSMISSION_CHOICES = [
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
    ]

    model = models.CharField(max_length=255)
    company = models.ForeignKey(CarCompany, on_delete=models.CASCADE)
    category = models.ForeignKey(CarCategory, on_delete=models.CASCADE)
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES)
    passenger_capacity = models.IntegerField()
    base_price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_acceptable_price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='cars/', null=True, blank=True)

class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('AMADEUS_FAILED', 'Amadeus Booking Failed'),
        ('REFUND_PENDING', 'Refund Pending'),
        ('REFUNDED', 'Refunded'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )


    user = models.ForeignKey(User, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True)
    pickup_location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='pickup_bookings')
    dropoff_location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='dropoff_bookings')
    pickup_date = models.DateField()
    pickup_time = models.TimeField()
    dropoff_date = models.DateField()
    dropoff_time = models.TimeField()
    child_seats = models.IntegerField(default=0)
    passengers = models.IntegerField(default=1)
    named_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    booking_reference = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    amadeus_booking_reference = models.CharField(max_length=100, blank=True, null=True)
    base_transfer_cost = models.DecimalField(max_digits=10, decimal_places=2)
    service_fee = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    transfer_id = models.CharField(max_length=50, null=True, blank=True)

    def update_status(self, new_status):
        self.status = new_status
        self.save()


class StatusHistory(models.Model):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    status = models.CharField(max_length=20, choices=Booking.STATUS_CHOICES)
    changed_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-changed_at']
        verbose_name_plural = 'Status Histories'

class Payment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
        ('REFUND_PENDING', 'Refund Pending'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    currency = models.CharField(max_length=3, default='USD')
    transaction_date = models.DateTimeField(default=timezone.now)
    additional_details = models.JSONField(default=dict)

from django.db import models

from core.helpers.enums import BookingStatus
from core.helpers.models import UIDTimeBasedModel
import auto_prefetch

class Booking(UIDTimeBasedModel):
    """
    A model that handles all the bookings
    """
    user = auto_prefetch.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="user_bookings",
        verbose_name="User"
    )

    status = models.CharField(
        max_length=20, choices=BookingStatus.choices,
        default=BookingStatus.PENDING
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

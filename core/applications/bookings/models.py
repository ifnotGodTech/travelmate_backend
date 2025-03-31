from django.db import models
from django.contrib.auth import get_user_model
from core.applications.stay.models import Booking

User = get_user_model()

class BookingHistory(models.Model):
    """
    Universal history tracking for all booking types
    """
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='history_entries')
    status = models.CharField(max_length=50)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    booking_type = models.CharField(max_length=20, choices=[('car', 'Car'), ('flight', 'Flight')])

    # Store changes as JSON
    field_changes = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-changed_at']

from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.applications.bookings.models import BookingHistory

User = get_user_model()

class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user representation for history entries"""

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']


class BookingHistorySerializer(serializers.ModelSerializer):
    """Serializer for booking history entries"""

    changed_by = UserMinimalSerializer(read_only=True)

    class Meta:
        model = BookingHistory
        fields = [
            'id', 'booking', 'status', 'changed_at', 'notes',
            'changed_by', 'booking_type', 'field_changes'
        ]
        read_only_fields = fields

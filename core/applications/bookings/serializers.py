from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.applications.bookings.models import BookingHistory
from drf_spectacular.utils import extend_schema_field

User = get_user_model()

class UserMinimalSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'first_name', 'last_name']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_first_name(self, obj) -> str | None:
        return obj.profile.first_name if hasattr(obj, 'profile') else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_last_name(self, obj) -> str | None:
        return obj.profile.last_name if hasattr(obj, 'profile') else None


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

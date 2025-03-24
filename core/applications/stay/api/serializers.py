from core.applications.stay.models import Booking
from rest_framework import serializers


class BookingSerializer:
    class BaseBookingSerializer(serializers.ModelSerializer):
        class Meta:
            model = Booking
            fields = "__all__"

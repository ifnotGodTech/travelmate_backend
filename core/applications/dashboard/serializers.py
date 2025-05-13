from rest_framework import serializers
from core.applications.bookings.models import Booking
from core.applications.users.models import User
from core.applications.flights.models import FlightBooking
from core.applications.cars.models import CarBooking

class DashboardStatsSerializer(serializers.Serializer):
    total_bookings = serializers.IntegerField(
        help_text="Total number of bookings in the system"
    )

class UserActivitySerializer(serializers.ModelSerializer):
    user_full_name = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    amount = serializers.DecimalField(source='total_price', max_digits=10, decimal_places=2)
    date = serializers.DateTimeField(source='created_at')
    booking_type = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ['user_full_name', 'profile_picture', 'booking_type', 'amount', 'date']

    def get_user_full_name(self, obj):
        try:
            return f"{obj.user.profile.first_name} {obj.user.profile.last_name}"
        except (AttributeError, User.profile.RelatedObjectDoesNotExist):
            return ""

    def get_profile_picture(self, obj):
        try:
            if obj.user.profile.profile_pics:
                return obj.user.profile.profile_pics.url
        except (AttributeError, User.profile.RelatedObjectDoesNotExist):
            pass
        return None

    def get_booking_type(self, obj):
        # Check if it's a flight booking
        if hasattr(obj, 'flight_booking'):
            return 'Flight Booking'
        # Check if it's a car booking
        elif hasattr(obj, 'car_booking'):
            return 'Car Booking'
        return None

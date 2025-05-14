from rest_framework import serializers
from core.applications.bookings.models import Booking
from core.applications.users.models import User
from core.applications.flights.models import FlightBooking
from core.applications.cars.models import CarBooking
from core.applications.stay.models import Booking as StayBooking
from core.applications.tickets.models import Ticket, Message as TicketMessage
from core.applications.chat.models import ChatMessage, ChatSession
from django.db.models import Sum, Count
from decimal import Decimal

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

class BookingTypeSerializer(serializers.ModelSerializer):
    booking_type = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ['booking_type']

    def get_booking_type(self, obj):
        # Check if it's a flight booking
        if hasattr(obj, 'flight_booking'):
            return 'Flight Booking'
        # Check if it's a car booking
        elif hasattr(obj, 'car_booking'):
            return 'Car Booking'
        return None

class RevenueSerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    car_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    flight_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(default='USD')

class MessageSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField()
    title = serializers.CharField()
    content = serializers.CharField()
    sender = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    link = serializers.SerializerMethodField()

    def get_sender(self, obj):
        if hasattr(obj, 'sender'):
            return {
                'id': obj.sender.id,
                'name': f"{obj.sender.profile.first_name} {obj.sender.profile.last_name}" if hasattr(obj.sender, 'profile') else obj.sender.email,
                'email': obj.sender.email
            }
        return None

    def get_link(self, obj):
        if hasattr(obj, 'ticket'):
            return f"/admin/tickets/{obj.ticket.id}"
        elif hasattr(obj, 'session'):
            return f"/admin/chat/{obj.session.id}"
        return None

class DashboardOverviewSerializer(serializers.Serializer):
    stats = DashboardStatsSerializer()
    revenue = RevenueSerializer()
    recent_activities = UserActivitySerializer(many=True)
    messages = MessageSerializer(many=True)

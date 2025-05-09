from core.helpers.enums import FlightBookingTypeChoice
from rest_framework import serializers
from .models import Passenger, FlightBooking, Flight, PassengerBooking, PaymentDetail
from core.applications.stay.models import Booking
from datetime import datetime
from django.core.exceptions import ValidationError


class PassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = '__all__'

    def validate_phone(self, value):
        if value:
            digits = ''.join(filter(str.isdigit, str(value)))
            if len(digits) < 6:
                raise ValidationError("Phone number must be at least 6 digits")
            return digits
        return value

class FlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        exclude = ['flight_booking']
        read_only_fields = ['created_at', 'updated_at']

class PassengerBookingSerializer(serializers.ModelSerializer):
    passenger = PassengerSerializer()

    class Meta:
        model = PassengerBooking
        exclude = ['flight_booking']

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'user', 'status', 'total_price', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class PaymentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentDetail
        exclude = ['booking']

class FlightBookingSerializer(serializers.ModelSerializer):
    booking = BookingSerializer(read_only=True)
    flights = FlightSerializer(many=True, read_only=True)
    passenger_bookings = PassengerBookingSerializer(many=True, read_only=True)
    payment_details = PaymentDetailSerializer(source='booking.payment_detail', read_only=True)

    class Meta:
        model = FlightBooking
        fields = [
            'id', 'booking', 'booking_reference', 'booking_type', 'currency',
            'service_fee', 'base_flight_cost', 'admin_notes', 'cancelled_by',
            'cancellation_date', 'cancellation_reason', 'flights',
            'passenger_bookings', 'payment_details'
        ]
        read_only_fields = ['booking_reference', 'created_at', 'updated_at']

# Input serializers for creating flight bookings
class PassengerInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = '__all__'

class FlightInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        exclude = ['flight_booking', 'id', 'created_at', 'updated_at']

class FlightBookingInputSerializer(serializers.Serializer):
    booking_type = serializers.ChoiceField(choices=FlightBookingTypeChoice.choices)
    flight_offer_ids = serializers.ListField(
        child=serializers.CharField(),
        min_length=1
    )
    passengers = PassengerInputSerializer(many=True)

    def validate(self, data):
        """
        Validate the booking type against the number of flight offers.
        """
        booking_type = data.get('booking_type')
        flight_offer_ids = data.get('flight_offer_ids')

        if booking_type == 'ONE_WAY' and len(flight_offer_ids) != 1:
            raise serializers.ValidationError("One-way bookings must have exactly one flight offer.")
        elif booking_type == 'ROUND_TRIP' and len(flight_offer_ids) != 2:
            raise serializers.ValidationError("Round-trip bookings must have exactly two flight offers.")
        elif booking_type == 'MULTI_CITY' and len(flight_offer_ids) < 2:
            raise serializers.ValidationError("Multi-city bookings must have at least two flight offers.")

        return data

class FlightSearchSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=3)
    destination = serializers.CharField(max_length=3)
    departure_date = serializers.DateField()
    return_date = serializers.DateField(required=False)
    adults = serializers.IntegerField(min_value=1, default=1)
    children = serializers.IntegerField(min_value=0, default=0,
        help_text="Passengers aged 2-11 years")
    infants = serializers.IntegerField(min_value=0, default=0,
        help_text="Passengers aged under 2 years")
    travel_class = serializers.ChoiceField(
        choices=['ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST'],
        default='ECONOMY'
    )
    non_stop = serializers.BooleanField(default=False)
    currency = serializers.CharField(max_length=3, default='USD')

    def validate(self, data):
        """
        Validate that departure date is in the future
        """
        departure_date = data.get('departure_date')
        return_date = data.get('return_date')
        today = datetime.now().date()

        if departure_date and departure_date < today:
            raise serializers.ValidationError("Departure date must be in the future")

        if return_date and return_date < departure_date:
            raise serializers.ValidationError("Return date must be after departure date")

        # Validate passenger counts
        adults = data.get('adults', 1)
        children = data.get('children', 0)
        infants = data.get('infants', 0)

        if infants > adults:
            raise serializers.ValidationError("Number of infants cannot exceed number of adults")

        total_passengers = adults + children + infants
        if total_passengers > 9:
            raise serializers.ValidationError("Maximum 9 passengers allowed per booking")

        return data

class FlightSegmentSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=3)
    destination = serializers.CharField(max_length=3)
    departure_date = serializers.DateField()

class MultiCityFlightSearchSerializer(serializers.Serializer):
    segments = FlightSegmentSerializer(many=True, min_length=2)
    adults = serializers.IntegerField(min_value=1, default=1)
    children = serializers.IntegerField(min_value=0, default=0,
        help_text="Passengers aged 2-11 years")
    infants = serializers.IntegerField(min_value=0, default=0,
        help_text="Passengers aged under 2 years")
    travel_class = serializers.ChoiceField(
        choices=['ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST'],
        default='ECONOMY'
    )
    currency = serializers.CharField(max_length=3, default='USD')

    def validate(self, data):
        """
        Validate passenger counts and segments
        """
        # Validate passenger counts
        adults = data.get('adults', 1)
        children = data.get('children', 0)
        infants = data.get('infants', 0)

        if infants > adults:
            raise serializers.ValidationError("Number of infants cannot exceed number of adults")

        total_passengers = adults + children + infants
        if total_passengers > 9:
            raise serializers.ValidationError("Maximum 9 passengers allowed per booking")

        return data

    def validate_segments(self, value):
        """
        Validate that at least 2 segments are provided and dates are valid
        """
        if len(value) < 2:
            raise serializers.ValidationError("At least 2 segments are required for multi-city flights")

        # Validate that all departure dates are in the future
        today = datetime.now().date()
        for segment in value:
            if segment['departure_date'] < today:
                raise serializers.ValidationError("All departure dates must be in the future")

        # Validate that segments are in chronological order
        for i in range(1, len(value)):
            if value[i]['departure_date'] < value[i-1]['departure_date']:
                raise serializers.ValidationError("Flight segments must be in chronological order")

        return value

class FlightOfferSerializer(serializers.Serializer):
    """
    Serializer for flight offers selected by the user
    """
    flight_offer_id = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3)
    flight_offer_data = serializers.JSONField()

class BookingConfirmationSerializer(serializers.Serializer):
    """
    Serializer for booking confirmation with service fee details
    """
    booking_reference = serializers.CharField(max_length=100)
    booking_status = serializers.CharField()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    base_flight_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    service_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    service_fee_percentage = serializers.FloatField()
    currency = serializers.CharField(max_length=3)
    flights = serializers.ListField(child=serializers.JSONField())
    passengers = serializers.ListField(child=serializers.JSONField())
    payment_status = serializers.CharField()

class PaymentInputSerializer(serializers.Serializer):
    payment_method_id = serializers.CharField(
        required=True,
        help_text="Stripe payment method ID"
    )

class CancellationSerializer(serializers.Serializer):
    """
    Serializer for cancelling a booking
    """
    reason = serializers.CharField(required=False, allow_blank=True)

class FlightOfferPricingSerializer(serializers.Serializer):
    """
    Serializer for flight offer pricing details
    """
    flight_offer_ids = serializers.ListField(
        child=serializers.CharField(),
        min_length=1
    )
    include_service_fee = serializers.BooleanField(default=True)

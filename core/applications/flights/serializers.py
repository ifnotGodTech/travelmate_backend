from rest_framework import serializers
from .models import Passenger, FlightBooking, Flight, PassengerBooking, PaymentDetail
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
        exclude = ['booking']

class PassengerBookingSerializer(serializers.ModelSerializer):
    passenger = PassengerSerializer()

    class Meta:
        model = PassengerBooking
        exclude = ['booking']

class PaymentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentDetail
        exclude = ['booking']

class FlightBookingSerializer(serializers.ModelSerializer):
    flights = FlightSerializer(many=True, read_only=True)
    passenger_bookings = PassengerBookingSerializer(many=True, read_only=True)
    payment = PaymentDetailSerializer(read_only=True)

    class Meta:
        model = FlightBooking
        fields = '__all__'
        read_only_fields = ['booking_reference', 'user', 'created_at', 'updated_at']

# Input serializers for creating flight bookings
class PassengerInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = '__all__'

class FlightInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        exclude = ['booking', 'id']

class FlightBookingInputSerializer(serializers.Serializer):
    booking_type = serializers.ChoiceField(choices=FlightBooking.BOOKING_TYPE_CHOICES)
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
        today = datetime.now().date()

        if departure_date and departure_date < today:
            raise serializers.ValidationError("Departure date must be in the future")

        # Validate return date if provided
        return_date = data.get('return_date')
        if return_date and return_date < departure_date:
            raise serializers.ValidationError("Return date must be after departure date")

        return data


class FlightSegmentSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=3)
    destination = serializers.CharField(max_length=3)
    departure_date = serializers.DateField()



class MultiCityFlightSearchSerializer(serializers.Serializer):
    segments = FlightSegmentSerializer(many=True, min_length=2)
    adults = serializers.IntegerField(min_value=1, default=1)
    travel_class = serializers.ChoiceField(
        choices=['ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST'],
        default='ECONOMY'
    )
    currency = serializers.CharField(max_length=3, default='USD')

    def validate_segments(self, value):
        """
        Validate that at least 2 segments are provided
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

    # This would typically include the complete flight offer data from Amadeus
    # but for simplicity, we're just including the ID and price
    flight_offer_data = serializers.JSONField()

class BookingConfirmationSerializer(serializers.Serializer):
    """
    Serializer for booking confirmation with service fee details
    """
    booking_reference = serializers.CharField()
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

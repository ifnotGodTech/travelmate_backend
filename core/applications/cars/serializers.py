# serializers.py
from rest_framework import serializers
from decimal import Decimal, ROUND_HALF_UP
from drf_spectacular.utils import extend_schema_field
from .models import CarServiceFee, Location, Car, CarBooking, Payment, CarCategory, CarCompany, StatusHistory
from core.applications.stay.models import Booking
from core.applications.users.models import User

class CarServiceFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarServiceFee
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class CarCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CarCategory
        fields = '__all__'

class CarCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = CarCompany
        fields = '__all__'

class CarSerializer(serializers.ModelSerializer):
    company = CarCompanySerializer(read_only=True)
    category = CarCategorySerializer(read_only=True)

    class Meta:
        model = Car
        fields = '__all__'

class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusHistory
        fields = '__all__'
        read_only_fields = ('changed_at',)

class CarBookingSerializer(serializers.ModelSerializer):
    """
    Serializer for the CarBooking model with flexible API
    """
    # Nested serializers for read operations
    pickup_location_details = LocationSerializer(source='pickup_location', read_only=True)
    dropoff_location_details = LocationSerializer(source='dropoff_location', read_only=True)
    car_details = CarSerializer(source='car', read_only=True)
    status_history = serializers.SerializerMethodField()

    # Base booking fields that we'll handle in create/update
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True, required=False)
    status = serializers.CharField(required=False, write_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, write_only=True
    )

    class Meta:
        model = CarBooking
        fields = [
            'id', 'user', 'status', 'total_price',  # Base booking fields (write-only)
            'car', 'car_details',
            'pickup_location', 'pickup_location_details',
            'dropoff_location', 'dropoff_location_details',
            'pickup_date', 'pickup_time',
            'dropoff_date', 'dropoff_time',
            'child_seats', 'passengers',
            'named_price', 'booking_reference',
            'amadeus_booking_reference',
            'base_transfer_cost', 'service_fee',
            'currency', 'transfer_id',
            'status_history'
        ]
        extra_kwargs = {
            'pickup_date': {'required': False, 'allow_null': True},
            'pickup_time': {'required': False, 'allow_null': True},
            'dropoff_date': {'required': False, 'allow_null': True},
            'dropoff_time': {'required': False, 'allow_null': True},
            'pickup_location': {'required': False, 'allow_null': True},
            'dropoff_location': {'required': False, 'allow_null': True},
            'service_fee': {
                'max_digits': 10,
                'decimal_places': 2,
                'coerce_to_string': False,
                'required': False
            },
            'transfer_id': {'required': False},
        }

    @extend_schema_field(str)
    def get_status_history(self, obj):
        """
        Get the status history for the related Booking
        """
        history = StatusHistory.objects.filter(booking=obj.booking)
        return StatusHistorySerializer(history, many=True).data

    def validate(self, data):
        """
        Custom validation that works with minimal input
        """
        # For transfer bookings, check if transfer_id is provided
        if 'transfer_id' in data:
            # You can add any additional validation specific to transfer bookings here
            pass

        # Add default values if needed
        if 'status' not in data:
            data['status'] = 'PENDING'

        return data

    def create(self, validated_data):
        """
        Custom create method that handles both simple and detailed requests
        """
        # Extract booking-related fields
        user = validated_data.pop('user', None)
        status = validated_data.pop('status', 'PENDING')
        total_price = validated_data.pop('total_price', Decimal('0.00'))

        # If user is not provided but we have a request context with user
        if not user and self.context and 'request' in self.context:
            user = self.context['request'].user

        # Create base Booking first
        if not user:
            raise serializers.ValidationError({'user': 'User is required'})

        booking = Booking.objects.create(
            user=user,
            status=status,
            total_price=total_price
        )

        # Create CarBooking with the base booking
        car_booking = CarBooking.objects.create(booking=booking, **validated_data)

        return car_booking

    def update(self, instance, validated_data):
        """
        Custom update method that handles both the base Booking and CarBooking
        """
        # Extract and handle booking-related fields
        user = validated_data.pop('user', None)
        status = validated_data.pop('status', None)
        total_price = validated_data.pop('total_price', None)

        # Update the base Booking if necessary
        booking = instance.booking
        if user:
            booking.user = user
        if status:
            booking.status = status
        if total_price is not None:
            booking.total_price = total_price

        # Save the booking if any field was updated
        if user or status or total_price is not None:
            booking.save()

        # Update the CarBooking instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Payment model
    """
    booking_details = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = (
            'transaction_id',
            'status',
            'created_at',
            'transaction_date',
            'additional_details'
        )

    @extend_schema_field(str)
    def get_booking_details(self, obj):
        """
        Get the booking details including car booking information
        """
        # First get the base booking data
        booking_data = {
            'id': obj.booking.id,
            'status': obj.booking.status,
            'total_price': obj.booking.total_price,
            'user': obj.booking.user.id,
            'created_at': obj.booking.created_at,
            'updated_at': obj.booking.updated_at
        }

        # Try to get related car booking data
        try:
            car_booking = obj.booking.car_booking
            # Add car booking fields that you want to expose
            car_booking_data = {
                'transfer_id': car_booking.transfer_id,
                'booking_reference': car_booking.booking_reference,
                'pickup_date': car_booking.pickup_date,
                'dropoff_date': car_booking.dropoff_date,
                # Add more fields as needed
            }
            booking_data.update(car_booking_data)
        except CarBooking.DoesNotExist:
            pass

        return booking_data


class TransferSearchSerializer(serializers.Serializer):
    """Empty serializer just to satisfy the schema generation"""
    pass

# serializers.py
from rest_framework import serializers
from decimal import Decimal, ROUND_HALF_UP
from .models import CarServiceFee, Location, Car, Booking, Payment, CarCategory, CarCompany, StatusHistory

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

class BookingSerializer(serializers.ModelSerializer):
    # Location details
    pickup_location_details = LocationSerializer(source='pickup_location', read_only=True)
    dropoff_location_details = LocationSerializer(source='dropoff_location', read_only=True)
    status_history = StatusHistorySerializer(many=True, read_only=True)

    # Optional car field for backward compatibility
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Booking
        fields = '__all__'
        extra_kwargs = {
            'pickup_date': {'required': False, 'allow_null': True},
            'pickup_time': {'required': False, 'allow_null': True},
            'dropoff_date': {'required': False, 'allow_null': True},
            'dropoff_time': {'required': False, 'allow_null': True},
            'pickup_location': {'required': False, 'allow_null': True},
            'dropoff_location': {'required': False, 'allow_null': True},
            'total_price': {
                'max_digits': 10,
                'decimal_places': 2,
                'coerce_to_string': False,
            },
            'service_fee': {
                'max_digits': 10,
                'decimal_places': 2,
                'coerce_to_string': False,
            },
        }

    def validate(self, data):
        """
        Custom validation for booking
        """
        # Ensure decimal fields are rounded to 2 decimal places
        if 'total_price' in data:
            data['total_price'] = Decimal(str(data['total_price'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if 'service_fee' in data:
            data['service_fee'] = Decimal(str(data['service_fee'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # For transfer bookings, ensure transfer-specific fields are present
        if 'transfer_id' in self.initial_data:
            # Validate transfer-specific requirements
            required_transfer_fields = [
                'pickup_date', 'pickup_time',
                'total_price',
                'transfer_id',
                'pickup_location',
                'end_address',
                'currency'
            ]

            for field in required_transfer_fields:
                if field not in data and field not in self.initial_data:
                    raise serializers.ValidationError({field: "This field is required for transfer bookings"})

        return data

    def create(self, validated_data):
        """
        Custom create method to handle both car and transfer bookings
        """
        # Remove any null or empty values
        cleaned_data = {k: v for k, v in validated_data.items() if v is not None}

        return super().create(cleaned_data)



class PaymentSerializer(serializers.ModelSerializer):
    booking_details = BookingSerializer(source='booking', read_only=True)

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

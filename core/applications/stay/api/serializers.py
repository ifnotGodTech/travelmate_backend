from rest_framework import serializers
from datetime import date, datetime


class HotelSearchSerializer(serializers.Serializer):
    destination = serializers.CharField(required=True)
    check_in = serializers.CharField(required=True)
    check_out = serializers.CharField(required=True)
    adults = serializers.IntegerField(min_value=1, max_value=10, default=2)
    children = serializers.IntegerField(min_value=0, max_value=10, default=0)
    min_price = serializers.IntegerField(min_value=0, required=False)
    max_price = serializers.IntegerField(min_value=0, required=False)
    amenities = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        # Parse the date strings first
        try:
            check_in = datetime.strptime(data['check_in'], '%Y-%m-%d').date()
            check_out = datetime.strptime(data['check_out'], '%Y-%m-%d').date()
        except ValueError:
            raise serializers.ValidationError("Dates must be in YYYY-MM-DD format.")

        # Store the parsed dates back in the data dict
        data['check_in'] = check_in
        data['check_out'] = check_out

        if check_in >= check_out:
            raise serializers.ValidationError("Check-out must be after check-in.")

        if check_in < date.today():
            raise serializers.ValidationError("Check-in cannot be in the past.")

        min_price = data.get('min_price')
        max_price = data.get('max_price')

        if min_price is not None and max_price is not None:
            if max_price <= min_price:
                raise serializers.ValidationError("Max price must be greater than min price.")

        return data


class HotelDiscoverySerializer(serializers.Serializer):
    city_code = serializers.CharField(max_length=10, required=True)
    language = serializers.CharField(max_length=3, default="ENG")
    ratings = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=5),
        required=False
    )
    amenities = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False
    )
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)

class AvailabilityCheckSerializer(serializers.Serializer):
    hotel_id = serializers.CharField(max_length=10, required=True)
    check_in = serializers.DateField(required=True)
    check_out = serializers.DateField(required=True)
    adults = serializers.IntegerField(min_value=1, max_value=10, default=2)
    children = serializers.IntegerField(min_value=0, max_value=10, default=0)

    def validate(self, data):
        if data["check_in"] < date.today():
            raise serializers.ValidationError("Check-in date cannot be in the past")
        if data["check_out"] <= data["check_in"]:
            raise serializers.ValidationError("Check-out must be after check-in")
        return data

class PaxSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['AD', 'CH'])
    name = serializers.CharField(max_length=100)
    surname = serializers.CharField(max_length=100)
    age = serializers.IntegerField(required=False, min_value=0, max_value=120)

class RoomBookingSerializer(serializers.Serializer):
    rate_key = serializers.CharField(required=True)
    paxes = serializers.ListField(
        child=PaxSerializer(),
        min_length=1
    )

class PaymentDataSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(
        choices=['CREDIT_CARD', 'PAYPAL', 'BANK_TRANSFER'],
        required=True
    )
    card_number = serializers.CharField(required=False, max_length=19)
    expiry_date = serializers.CharField(required=False, max_length=5)
    cvv = serializers.CharField(required=False, max_length=4)

class HotelBookingSerializer(serializers.Serializer):
    holder_name = serializers.CharField(max_length=100, required=True)
    holder_surname = serializers.CharField(max_length=100, required=True)
    holder_email = serializers.EmailField(required=True)
    holder_phone = serializers.CharField(max_length=20, required=True)
    rooms = serializers.ListField(
        child=RoomBookingSerializer(),
        min_length=1
    )
    payment_data = PaymentDataSerializer(required=True)
    special_requests = serializers.CharField(required=False, allow_blank=True)

class GeoSearchSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    radius = serializers.IntegerField(min_value=1, max_value=100, default=10)
    unit = serializers.ChoiceField(choices=['KM', 'MI'], default='KM')

class HotelReviewsSerializer(serializers.Serializer):
    hotel_id = serializers.CharField(max_length=10, required=True)
    language = serializers.CharField(max_length=3, default="ENG")

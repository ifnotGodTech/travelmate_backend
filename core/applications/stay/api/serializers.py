from rest_framework import serializers

class HotelSearchSerializer(serializers.Serializer):
    city_code = serializers.CharField(max_length=3)
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    adults = serializers.IntegerField(min_value=1)

class GuestSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.EmailField()

class PaymentSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=["creditCard"])
    vendor_code = serializers.CharField()
    card_number = serializers.CharField()
    expiry_date = serializers.CharField()

class HotelBookingSerializer(serializers.Serializer):
    offer_id = serializers.CharField()
    guests = GuestSerializer(many=True)
    payments = PaymentSerializer(many=True)

from django.contrib import admin
from django.conf import settings
from allauth.account.decorators import secure_admin_login
from django.utils.translation import gettext_lazy as _


from .models import (
    ServiceFeeSetting,
    Passenger,
    FlightBooking,
    Flight,
    PassengerBooking,
    PaymentDetail
)


# Only apply this if the setting is True
if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]

@admin.register(ServiceFeeSetting)
class ServiceFeeSettingAdmin(admin.ModelAdmin):
    list_display = ('percentage', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('description',)

@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'title', 'email', 'phone', 'nationality')
    list_filter = ('title', 'gender', 'nationality')
    search_fields = ('first_name', 'last_name', 'email', 'passport_number')

@admin.register(FlightBooking)
class FlightBookingAdmin(admin.ModelAdmin):
    list_display = ('booking_reference', 'user', 'booking_status', 'booking_type',
                    'total_price', 'currency', 'created_at')
    list_filter = ('booking_status', 'booking_type', 'created_at')
    search_fields = ('booking_reference', 'user__username')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ('flight_number', 'airline_name', 'departure_airport', 'departure_city',
                    'departure_datetime', 'arrival_airport', 'arrival_city', 'arrival_datetime')
    list_filter = ('airline_name', 'departure_airport', 'arrival_airport', 'cabin_class')
    search_fields = ('flight_number', 'airline_name', 'segment_id')

@admin.register(PassengerBooking)
class PassengerBookingAdmin(admin.ModelAdmin):
    list_display = ('passenger', 'booking', 'ticket_number', 'seat_number')
    list_filter = ('booking__booking_status',)
    search_fields = ('passenger__first_name', 'passenger__last_name', 'ticket_number')

@admin.register(PaymentDetail)
class PaymentDetailAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'currency', 'payment_method',
                    'payment_status', 'payment_date')
    list_filter = ('payment_status', 'payment_method')
    search_fields = ('booking__booking_reference', 'transaction_id')
    readonly_fields = ('payment_date',)

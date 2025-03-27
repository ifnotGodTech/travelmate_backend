from django.contrib import admin
from django.conf import settings
from allauth.account.decorators import secure_admin_login
from django.utils.html import format_html
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _


from .models import (
    CarServiceFee,
    Location,
    CarCompany,
    CarCategory,
    Car,
    Booking,
    StatusHistory,
    Payment
)


# Only apply this if the setting is True
if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]

@admin.register(CarServiceFee)
class CarServiceFeeAdmin(admin.ModelAdmin):
    list_display = ('fee_type', 'percentage', 'minimum_fee', 'is_active', 'effective_from', 'effective_to')
    list_filter = ('fee_type', 'is_active')
    search_fields = ('fee_type',)

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'country', 'latitude', 'longitude')
    list_filter = ('city', 'country')
    search_fields = ('name', 'address')

@admin.register(CarCompany)
class CarCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_logo')
    search_fields = ('name',)

    @admin.display(
        description='Logo'
    )
    def display_logo(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.logo.url)
        return 'No Logo'

@admin.register(CarCategory)
class CarCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('model', 'company', 'category', 'transmission', 'passenger_capacity', 'base_price_per_day')
    list_filter = ('company', 'category', 'transmission')
    search_fields = ('model',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_reference', 'user', 'car', 'status', 'pickup_date', 'dropoff_date', 'total_price')
    list_filter = ('status', 'pickup_date', 'dropoff_date')
    search_fields = ('booking_reference', 'user__username', 'car__model')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('booking', 'status', 'changed_at')
    list_filter = ('status', 'changed_at')
    search_fields = ('booking__booking_reference',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'status', 'payment_method', 'transaction_date')
    list_filter = ('status', 'payment_method')
    search_fields = ('booking__booking_reference', 'transaction_id')
    readonly_fields = ('created_at',)

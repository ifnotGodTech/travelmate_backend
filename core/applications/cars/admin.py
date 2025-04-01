from django.contrib import admin
from django.conf import settings
from allauth.account.decorators import secure_admin_login
from django.utils.html import format_html
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import TabularInline


from .models import (
    CarServiceFee,
    Location,
    CarCompany,
    CarCategory,
    Car,
    CarBooking,
    StatusHistory,
    Payment,
)
from core.applications.stay.models import Booking


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
    ordering = ('fee_type',)
    list_editable = ('is_active', 'percentage', 'minimum_fee')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'city', 'country', 'airport_code')
    list_filter = ('country', 'city')
    search_fields = ('name', 'code', 'city', 'country', 'airport_code')
    ordering = ('name',)


@admin.register(CarCompany)
class CarCompanyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(CarCategory)
class CarCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('model', 'company', 'category', 'transmission', 'passenger_capacity', 'base_price_per_day')
    list_filter = ('company', 'category', 'transmission')
    search_fields = ('model', 'company__name')
    ordering = ('model',)
    raw_id_fields = ('company', 'category')


class StatusHistoryInline(TabularInline):
    model = StatusHistory
    extra = 0
    readonly_fields = ('changed_at',)
    fields = ('status', 'changed_at', 'notes')


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = ('created_at', 'transaction_date')
    fields = ('status', 'amount', 'payment_method', 'transaction_id', 'currency', 'transaction_date')


class CarBookingInline(admin.StackedInline):
    model = CarBooking
    extra = 0
    raw_id_fields = ('car', 'pickup_location', 'dropoff_location')
    fields = (
        'car', 'pickup_location', 'dropoff_location',
        'pickup_date', 'pickup_time', 'dropoff_date', 'dropoff_time',
        'child_seats', 'passengers', 'named_price', 'booking_reference',
        'amadeus_booking_reference', 'base_transfer_cost', 'service_fee',
        'currency', 'transfer_id'
    )


class BookingAdmin(admin.ModelAdmin):
    inlines = [CarBookingInline, StatusHistoryInline, PaymentInline]
    list_display = ('id', 'user', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('id', 'user__email', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)


@admin.register(CarBooking)
class CarBookingAdmin(admin.ModelAdmin):
    list_display = (
        'booking_reference',
        'car',
        'pickup_location',
        'dropoff_location',
        'pickup_date',
        'dropoff_date',
        'passengers',
        'status_display',
        'cancelled_by_display',
        'has_special_requests'
    )
    list_filter = (
        'pickup_location',
        'dropoff_location',
        'booking__status',
        'pickup_date'
    )
    search_fields = (
        'booking_reference',
        'amadeus_booking_reference',
        'car__model',
        'booking__user__email',
        'booking__user__first_name',
        'booking__user__last_name'
    )
    raw_id_fields = ('car', 'pickup_location', 'dropoff_location', 'booking', 'cancelled_by')
    date_hierarchy = 'pickup_date'
    readonly_fields = ('get_created_at', 'get_updated_at', 'cancellation_details')

    @admin.display(
        description="Created At"
    )
    def get_created_at(self, obj):
        return obj.booking.created_at if obj.booking else None  # Fetch from related Booking

    @admin.display(
        description="Updated At"
    )
    def get_updated_at(self, obj):
        return obj.booking.updated_at if obj.booking else None  # Fetch from related Booking


    fieldsets = (
        ('Booking Information', {
            'fields': (
                'booking',
                'booking_reference',
                'amadeus_booking_reference',
                'transfer_id'
            )
        }),
        ('Car Details', {
            'fields': (
                'car',
                'base_transfer_cost',
                'service_fee',
                'currency',
                'named_price'
            )
        }),
        ('Trip Details', {
            'fields': (
                'pickup_location',
                'dropoff_location',
                'pickup_date',
                'pickup_time',
                'dropoff_date',
                'dropoff_time',
                'passengers',
                'child_seats'
            )
        }),
        ('Special Requests', {
            'fields': ('special_requests',)
        }),
        ('Admin Information', {
            'fields': (
                'admin_notes',
                'cancellation_reason',
                'cancelled_by'
            ),
            'classes': ('collapse',)
        }),
    )

    @admin.display(
        description='Status',
        ordering='booking__status',
    )
    def status_display(self, obj):
        return obj.booking.get_status_display()

    @admin.display(
        description='Cancelled By'
    )
    def cancelled_by_display(self, obj):
        return obj.cancelled_by.get_full_name() if obj.cancelled_by else None

    @admin.display(
        description='Special Requests',
        boolean=True,
    )
    def has_special_requests(self, obj):
        return bool(obj.special_requests)

    @admin.display(
        description="Cancellation Details"
    )
    def cancellation_details(self, obj):
        if obj.cancellation_reason:
            return format_html(
                "<strong>Cancelled by:</strong> {}<br>"
                "<strong>Reason:</strong> {}",
                obj.cancelled_by if obj.cancelled_by else "System",
                obj.cancellation_reason
            )
        return "Not cancelled"


@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('booking', 'status', 'changed_at')
    list_filter = ('status',)
    search_fields = ('booking__id', 'notes')
    date_hierarchy = 'changed_at'
    readonly_fields = ('changed_at',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'booking_display',
        'amount_display',
        'status',
        'payment_method',
        'refund_status',
        'transaction_date'
    )
    list_filter = (
        'status',
        'payment_method',
        'currency',
        ('refund_date', admin.DateFieldListFilter)
    )
    search_fields = (
        'booking__id',
        'transaction_id',
        'booking__user__email'
    )
    date_hierarchy = 'transaction_date'
    readonly_fields = (
        'created_at',
        'refund_details_display',
        'payment_split'
    )
    fieldsets = (
        ('Payment Information', {
            'fields': (
                'booking',
                'status',
                'amount',
                'currency',
                'payment_method',
                'transaction_id'
            )
        }),
        ('Dates', {
            'fields': (
                'transaction_date',
                'created_at'
            )
        }),
        ('Refund Information', {
            'fields': (
                'refund_amount',
                'refund_date',
                'refund_reason',
                'refund_details_display'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Details', {
            'fields': ('additional_details', 'payment_split'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(
        description='Booking',
        ordering='booking__id',
    )
    def booking_display(self, obj):
        return f"Booking #{obj.booking.id}"

    @admin.display(
        description='Amount'
    )
    def amount_display(self, obj):
        return f"{obj.currency} {obj.amount}"

    @admin.display(
        description='Refund'
    )
    def refund_status(self, obj):
        if obj.status == 'REFUNDED':
            return format_html(
                '<span style="color: green;">✓ Fully Refunded</span>'
            )
        elif obj.status == 'PARTIALLY_REFUNDED':
            return format_html(
                '<span style="color: orange;">↻ Partially Refunded ({}{})</span>',
                obj.currency,
                obj.refund_amount
            )
        return "-"

    @admin.display(
        description="Refund Details"
    )
    def refund_details_display(self, obj):
        if obj.refund_amount:
            return format_html(
                "<strong>Amount:</strong> {} {}<br>"
                "<strong>Date:</strong> {}<br>"
                "<strong>Reason:</strong> {}",
                obj.currency,
                obj.refund_amount,
                obj.refund_date,
                obj.refund_reason or "Not specified"
            )
        return "No refund processed"

    @admin.display(
        description="Payment Breakdown"
    )
    def payment_split(self, obj):
        details = obj.additional_details or {}
        if 'service_fee' in details:
            return format_html(
                "<strong>Total:</strong> {} {}<br>"
                "<strong>Service Fee:</strong> {} {} ({}%)<br>"
                "<strong>Transfer Cost:</strong> {} {}",
                obj.currency,
                details.get('total_price', obj.amount),
                obj.currency,
                details.get('service_fee', 0),
                details.get('service_fee_percentage', 0),
                obj.currency,
                details.get('transfer_cost', obj.amount)
            )
        return "No split details available"



# Override the default Booking admin if it's already registered
if admin.site.is_registered(Booking):
    admin.site.unregister(Booking)
admin.site.register(Booking, BookingAdmin)

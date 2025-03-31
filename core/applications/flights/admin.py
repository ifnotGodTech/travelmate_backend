from django.utils import timezone
from django.contrib import admin
from django.conf import settings
from allauth.account.decorators import secure_admin_login
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.db.models import Sum
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
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    search_fields = ('percentage', 'description')
    ordering = ('-created_at',)
    actions = ['deactivate_fees']

    @admin.action(
        description="Deactivate selected service fees"
    )
    def deactivate_fees(self, request, queryset):
        queryset.update(is_active=False)


class PassengerBookingInline(admin.TabularInline):
    model = PassengerBooking
    extra = 1
    raw_id_fields = ('passenger',)
    fields = ('passenger', 'ticket_number', 'seat_number')


class FlightInline(admin.TabularInline):
    model = Flight
    extra = 1
    fields = (
        'flight_number', 'airline_name',
        'departure_airport', 'arrival_airport',
        'departure_datetime', 'arrival_datetime',
        'cabin_class'
    )
    readonly_fields = ('segment_id',)


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'email', 'phone',
        'passport_number', 'nationality',
        'passport_expiry_status'
    )
    list_filter = ('title', 'gender', 'nationality')
    search_fields = (
        'first_name', 'last_name', 'email',
        'phone', 'passport_number'
    )
    ordering = ('last_name', 'first_name')
    readonly_fields = ('passport_expiry_status',)
    fieldsets = (
        (None, {
            'fields': (
                'title', 'first_name', 'last_name',
                'date_of_birth', 'gender'
            )
        }),
        ('Contact Information', {
            'fields': ('email', 'phone')
        }),
        ('Passport Details', {
            'fields': (
                'passport_number',
                'passport_expiry',
                'passport_expiry_status',
                'nationality'
            )
        }),
        ('Address', {
            'fields': (
                'address_line1', 'address_line2',
                'city', 'postal_code', 'country'
            ),
            'classes': ('collapse',)
        }),
    )

    @admin.display(
        description='Full Name'
    )
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    @admin.display(
        description='Passport Status'
    )
    def passport_expiry_status(self, obj):
        if obj.passport_expiry:
            if obj.passport_expiry < timezone.now().date():
                return format_html(
                    '<span style="color: red;">EXPIRED ({})</span>',
                    obj.passport_expiry
                )
            elif obj.passport_expiry < timezone.now().date() + timezone.timedelta(days=180):
                return format_html(
                    '<span style="color: orange;">Expires soon ({})</span>',
                    obj.passport_expiry
                )
            return format_html(
                '<span style="color: green;">Valid until {}</span>',
                obj.passport_expiry
            )
        return "No passport"


class PaymentStatusFilter(SimpleListFilter):
    title = 'Payment Status'
    parameter_name = 'payment_status'

    def lookups(self, request, model_admin):
        return PaymentDetail.PAYMENT_STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(payment__payment_status=self.value())
        return queryset


class CancellationFilter(SimpleListFilter):
    title = 'Cancellation Status'
    parameter_name = 'is_cancelled'

    def lookups(self, request, model_admin):
        return (
            ('cancelled', 'Cancelled'),
            ('active', 'Active'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'cancelled':
            return queryset.filter(cancellation_date__isnull=False)
        if self.value() == 'active':
            return queryset.filter(cancellation_date__isnull=True)
        return queryset


@admin.register(FlightBooking)
class FlightBookingAdmin(admin.ModelAdmin):
    list_display = (
        'booking_reference',
        'user_info',
        'booking_type',
        'total_amount',
        'payment_status',
        'cancellation_status',
        'created_at'
    )
    list_filter = (
        'booking_type',
        PaymentStatusFilter,
        CancellationFilter,
        ('cancellation_date', admin.DateFieldListFilter)
    )
    search_fields = (
        'booking_reference',
        'booking__user__username',
        'booking__user__email',
        'booking__user__first_name',
        'booking__user__last_name'
    )
    readonly_fields = (
        'booking_reference',
        'service_fee',
        'base_flight_cost',
        'cancellation_details'
    )
    inlines = [PassengerBookingInline, FlightInline]
    raw_id_fields = ('booking', 'cancelled_by')
    ordering = ('-booking__created_at',)
    actions = ['cancel_bookings']
    fieldsets = (
        ('Booking Information', {
            'fields': (
                'booking',
                'booking_reference',
                'booking_type',
                'currency'
            )
        }),
        ('Pricing', {
            'fields': (
                'base_flight_cost',
                'service_fee',
            )
        }),
        ('Cancellation Details', {
            'fields': (
                'cancellation_date',
                'cancelled_by',
                'cancellation_reason',
                'admin_notes',
                'cancellation_details'
            ),
            'classes': ('collapse',)
        }),
    )

    @admin.display(
        description='User'
    )
    def user_info(self, obj):
        user = obj.booking.user
        return f"{user.get_full_name()} ({user.email})"

    @admin.display(
        description='Total Amount'
    )
    def total_amount(self, obj):
        if obj.booking.flight_payment:
            return f"{obj.booking.flight_payment.amount} {obj.booking.flight_payment.currency}"
        return "-"

    @admin.display(
        description='Payment Status'
    )
    def payment_status(self, obj):
        if obj.booking.flight_payment:
            return obj.booking.flight_payment.get_payment_status_display()
        return "-"

    @admin.display(
        description='Created At'
    )
    def created_at(self, obj):
        return obj.booking.created_at

    @admin.display(
        description='Status'
    )
    def cancellation_status(self, obj):
        if obj.cancellation_date:
            return format_html(
                '<span style="color: red;">Cancelled</span>'
            )
        return format_html(
            '<span style="color: green;">Active</span>'
        )

    @admin.display(
        description="Cancellation Details"
    )
    def cancellation_details(self, obj):
        if obj.cancellation_date:
            return format_html(
                "<strong>Cancelled by:</strong> {}<br>"
                "<strong>Date:</strong> {}<br>"
                "<strong>Reason:</strong> {}",
                obj.cancelled_by if obj.cancelled_by else "System",
                obj.cancellation_date,
                obj.cancellation_reason or "Not specified"
            )
        return "Not cancelled"

    @admin.action(
        description="Cancel selected bookings"
    )
    def cancel_bookings(self, request, queryset):
        updated = queryset.filter(cancellation_date__isnull=True).update(
            cancellation_date=timezone.now(),
            cancelled_by=request.user,
            cancellation_reason="Cancelled by admin"
        )
        self.message_user(request, f"{updated} bookings were cancelled.")


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = (
        'flight_number',
        'airline_name',
        'route',
        'departure_datetime',
        'arrival_datetime',
        'flight_duration',
        'cabin_class'
    )
    list_filter = (
        'airline_name',
        'cabin_class',
        ('departure_datetime', admin.DateFieldListFilter)
    )
    search_fields = (
        'flight_number',
        'departure_airport',
        'arrival_airport',
        'flight_booking__booking_reference'
    )
    raw_id_fields = ('flight_booking',)
    readonly_fields = ('segment_id',)

    @admin.display(
        description='Route'
    )
    def route(self, obj):
        return f"{obj.departure_airport} → {obj.arrival_airport}"

    @admin.display(
        description='Duration'
    )
    def flight_duration(self, obj):
        if obj.departure_datetime and obj.arrival_datetime:
            duration = obj.arrival_datetime - obj.departure_datetime
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes = remainder // 60
            return f"{int(hours)}h {int(minutes)}m"
        return "-"


@admin.register(PassengerBooking)
class PassengerBookingAdmin(admin.ModelAdmin):
    list_display = (
        'passenger',
        'booking_reference',
        'flight_info',
        'ticket_info',
        'seat_number'
    )
    list_filter = (
        'flight_booking__booking_type',
    )
    search_fields = (
        'passenger__first_name',
        'passenger__last_name',
        'flight_booking__booking_reference',
        'ticket_number'
    )
    raw_id_fields = ('passenger', 'flight_booking')
    list_select_related = ('passenger', 'flight_booking')

    @admin.display(
        description='Booking Reference'
    )
    def booking_reference(self, obj):
        return obj.flight_booking.booking_reference

    @admin.display(
        description='Flight(s)'
    )
    def flight_info(self, obj):
        flights = obj.flight_booking.flights.all()
        if flights.exists():
            return ", ".join([f"{flight.flight_number} ({flight.departure_airport}→{flight.arrival_airport})" for flight in flights])
        return "-"

    @admin.display(
        description='Ticket'
    )
    def ticket_info(self, obj):
        if obj.ticket_number:
            return obj.ticket_number
        return format_html('<span style="color: orange;">No ticket issued</span>')


@admin.register(PaymentDetail)
class PaymentDetailAdmin(admin.ModelAdmin):
    list_display = (
        'booking_id',
        'amount_with_currency',
        'payment_method',
        'payment_status',
        'payment_date',
        'refund_status',
        'transaction_id'
    )
    list_filter = (
        'payment_status',
        'payment_method',
        ('payment_date', admin.DateFieldListFilter)
    )
    search_fields = (
        'booking__id',
        'transaction_id',
        'booking__user__email'
    )
    readonly_fields = (
        'booking',
        'amount',
        'currency',
        'payment_split',
        'refund_details'
    )
    ordering = ('-payment_date',)
    actions = ['process_refunds']
    fieldsets = (
        ('Payment Information', {
            'fields': (
                'booking',
                'amount',
                'currency',
                'payment_method',
                'payment_status',
                'payment_date',
                'transaction_id'
            )
        }),
        ('Refund Information', {
            'fields': (
                'refund_details',
            ),
            'classes': ('collapse',)
        }),
        ('Additional Details', {
            'fields': ('additional_details', 'payment_split'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(
        description='Booking ID'
    )
    def booking_id(self, obj):
        return obj.booking.id

    @admin.display(
        description='Amount'
    )
    def amount_with_currency(self, obj):
        return f"{obj.amount} {obj.currency}"

    @admin.display(
        description='Refund'
    )
    def refund_status(self, obj):
        if obj.payment_status == 'REFUNDED':
            return format_html(
                '<span style="color: green;">✓ Refunded</span>'
            )
        return "-"

    @admin.display(
        description="Payment Breakdown"
    )
    def payment_split(self, obj):
        details = obj.additional_details or {}
        if 'service_fee' in details:
            return format_html(
                "<strong>Total:</strong> {} {}<br>"
                "<strong>Service Fee:</strong> {} {} ({}%)<br>"
                "<strong>Flight Cost:</strong> {} {}",
                obj.currency,
                details.get('total_price', obj.amount),
                obj.currency,
                details.get('service_fee', 0),
                details.get('service_fee_percentage', 0),
                obj.currency,
                details.get('flight_cost', obj.amount)
            )
        return "No split details available"

    @admin.display(
        description="Refund Details"
    )
    def refund_details(self, obj):
        if obj.payment_status == 'REFUNDED':
            return format_html(
                "<strong>Refunded:</strong> {} {}<br>"
                "<strong>Date:</strong> {}",
                obj.currency,
                obj.amount,
                obj.payment_date
            )
        return "No refund processed"

    @admin.action(
        description="Mark selected as refunded"
    )
    def process_refunds(self, request, queryset):
        # This would be connected to your actual refund processing logic
        queryset = queryset.filter(payment_status='COMPLETED')
        updated = queryset.update(payment_status='REFUNDED')
        self.message_user(request, f"{updated} payments marked as refunded.")

from core.applications.bookings.models import BookingHistory
from core.applications.bookings.serializers import BookingHistorySerializer
from core.applications.cars.serializers import CarBookingSerializer, PaymentSerializer
from core.applications.cars.views import CarBookingViewSet
from core.applications.flights.serializers import FlightBookingSerializer
from core.applications.flights.views import FlightBookingViewSet
from core.applications.stay.models import Booking
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from .schemas import apply_unified_booking_schema
from django.utils import timezone
import stripe
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from drf_spectacular.types import OpenApiTypes

from core.applications.flights.models import Flight, FlightBooking, PassengerBooking, PaymentDetail
from core.applications.cars.models import CarBooking, Payment, StatusHistory



@extend_schema_view(
    list=extend_schema(
        description="List all bookings with filtering options for date range and booking type",
        parameters=[
            OpenApiParameter(
                name='start_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter bookings created on or after this date',
                required=False
            ),
            OpenApiParameter(
                name='end_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter bookings created on or before this date',
                required=False
            ),
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by booking type (car, flight)',
                required=False,
                enum=['car', 'flight']
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by booking status',
                required=False
            ),
        ]
    ),
    retrieve=extend_schema(
        description="Get detailed booking information for any booking type",
        parameters=[
            OpenApiParameter(
                name='pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='ID of the booking to retrieve',
                required=True
            )
        ]
    )
)
@apply_unified_booking_schema
class UnifiedBookingAdminViewSet(viewsets.ViewSet):
    """
    Admin-only operations for managing both car and flight bookings
    """
    lookup_field = 'pk'
    lookup_url_kwarg = 'pk'
    permission_classes = [IsAdminUser]

    queryset = Booking.objects.all()


    def list(self, request):
        """
        List all bookings with filtering options for date range and booking type
        """
        # Get filter parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        booking_type = request.query_params.get('type')  # 'car', 'flight' or None for all
        status_filter = request.query_params.get('status')

        # Base query for all bookings
        bookings = Booking.objects.all().order_by('-created_at')

        # Apply date filters if provided
        if start_date:
            bookings = bookings.filter(created_at__gte=start_date)
        if end_date:
            bookings = bookings.filter(created_at__lte=end_date)

        # Apply status filter if provided
        if status_filter:
            bookings = bookings.filter(status=status_filter)

        result = []
        for booking in bookings:
            # Determine booking type and get specific booking object
            booking_data = {
                'id': booking.id,
                'created_at': booking.created_at,
                'status': booking.status,
                'user': f"{booking.user.first_name} {booking.user.last_name}",
                'email': booking.user.email,
                'total_amount': None,  # Will be populated based on booking type
                'booking_type': None,  # Will be populated below
                'specific_id': None,   # Will store car_booking.id or flight_booking.id
                'details': {},         # Will contain type-specific details
            }

            # Check if it's a car booking
            try:
                car_booking = CarBooking.objects.get(booking=booking)
                if booking_type and booking_type.lower() != 'car':
                    continue  # Skip if filtering for another type

                booking_data['booking_type'] = 'car'
                booking_data['specific_id'] = car_booking.id
                booking_data['details'] = {
                    'pickup_date': car_booking.pickup_date,
                    'dropoff_date': car_booking.dropoff_date,
                    'car_model': car_booking.car.model if car_booking.car else 'N/A',
                }
                payment = Payment.objects.filter(booking=booking, status='COMPLETED').first()
                if payment:
                    booking_data['total_amount'] = payment.amount

                result.append(booking_data)
                continue
            except CarBooking.DoesNotExist:
                pass

            # Check if it's a flight booking
            try:
                flight_booking = FlightBooking.objects.get(booking=booking)
                if booking_type and booking_type.lower() != 'flight':
                    continue  # Skip if filtering for another type

                booking_data['booking_type'] = 'flight'
                booking_data['specific_id'] = flight_booking.id

                # Get first flight for summary
                first_flight = Flight.objects.filter(flight_booking=flight_booking).order_by('departure_datetime').first()
                if first_flight:
                    booking_data['details'] = {
                        'departure': first_flight.departure_airport,
                        'arrival': first_flight.arrival_airport,
                        'departure_date': first_flight.departure_datetime.date(),
                        'flight_number': f"{first_flight.airline_code}{first_flight.flight_number}",
                    }

                payment = PaymentDetail.objects.filter(booking=booking, payment_status='COMPLETED').first()
                if payment:
                    booking_data['total_amount'] = payment.amount

                result.append(booking_data)
            except FlightBooking.DoesNotExist:
                pass

             # Check if it's a Hotel booking
            # try:
            #     hotel_booking = HotelBooking.objects.get(booking=booking)
            #     if booking_type and booking_type.lower() != 'hotel':
            #         continue  # Skip if filtering for another type

            #     booking_data['booking_type'] = 'hotel'
            #     booking_data['specific_id'] = hotel_booking.id

            #     # Add hotel details
            #     booking_data['details'] = {
            #         'hotel_name': hotel_booking.hotel_name,
            #         'hotel_id': hotel_booking.hotel_id,
            #         'check_in': hotel_booking.check_in_date,
            #         'check_out': hotel_booking.check_out_date,
            #         'guests': hotel_booking.num_guests,
            #         'room_type': hotel_booking.room_type,
            #     }

            #     # Get payment details if available
            #     # Assuming you have a PaymentDetail model for hotel bookings similar to flights
            #     payment = PaymentDetail.objects.filter(booking=booking, payment_status='COMPLETED').first()
            #     if payment:
            #         booking_data['total_amount'] = payment.amount

            #     result.append(booking_data)
            # except HotelBooking.DoesNotExist:
            #     pass

        return Response(result, status=status.HTTP_200_OK)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='pk',
                description='Primary key of the booking',
                required=True,
                type=int,
            )
        ]
    )

    def retrieve(self, request, pk=None):
        """
        Get detailed booking information for any booking type
        """
        try:
            booking = Booking.objects.get(pk=pk)
            booking_type = self._determine_booking_type(booking)

            if booking_type == 'car':
                return self._get_car_booking_details(booking)
            elif booking_type == 'flight':
                return self._get_flight_booking_details(booking)
            else:
                return Response(
                    {"error": "Unknown booking type"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='pk',
                description='Booking ID',
                required=True,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH
            )
        ]
    )

    @action(detail=True, methods=['patch'])
    def update_booking(self, request, pk=None):
        """
        Update any booking type
        """
        try:
            booking = Booking.objects.get(pk=pk)
            booking_type = self._determine_booking_type(booking)

            if booking_type == 'car':
                return self._update_car_booking(booking, request)
            elif booking_type == 'flight':
                return self._update_flight_booking(booking, request)
            else:
                return Response(
                    {"error": "Unknown booking type"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )


    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='pk',
                description='Booking ID',
                required=True,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH
            )
        ]
    )

    @action(detail=True, methods=['post'])
    def cancel_booking(self, request, pk=None):
        """
        Cancel any booking type with optional refund
        """
        try:
            booking = Booking.objects.get(pk=pk)
            booking_type = self._determine_booking_type(booking)

            if booking.status == 'CANCELLED':
                return Response(
                    {"error": "Booking is already cancelled"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            process_refund = request.data.get('process_refund', False)
            refund_amount = request.data.get('refund_amount')
            cancellation_reason = request.data.get('reason', 'Admin cancellation')

            if booking_type == 'car':
                return self._cancel_car_booking(booking, request, process_refund, refund_amount, cancellation_reason)
            elif booking_type == 'flight':
                return self._cancel_flight_booking(booking, request, process_refund, refund_amount, cancellation_reason)
            else:
                return Response(
                    {"error": "Unknown booking type"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    # Helper methods
    def _determine_booking_type(self, booking):
        """Determine if a booking is for a car or flight"""
        try:
            CarBooking.objects.get(booking=booking)
            return 'car'
        except CarBooking.DoesNotExist:
            try:
                FlightBooking.objects.get(booking=booking)
                return 'flight'
            except FlightBooking.DoesNotExist:
                return None

    def _get_car_booking_details(self, booking):
        """Get detailed car booking information"""
        try:
            car_booking = CarBooking.objects.get(booking=booking)

            # Get basic booking data
            booking_data = CarBookingSerializer(car_booking).data

            # Add user details
            user = booking.user
            user_data = {
                'user': {
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'phone_number': user.phone_number if hasattr(user, 'phone_number') else None,
                }
            }

            # Add payment details
            payments = Payment.objects.filter(booking=booking)
            payment_data = {
                'payments': PaymentSerializer(payments, many=True).data
            }

            # Add car details
            car_data = {
                'car': {
                    'model': car_booking.car.model if car_booking.car else None,
                    'passenger_capacity': car_booking.car.passenger_capacity if car_booking.car else None,
                    'company': car_booking.car.company.name if car_booking.car and car_booking.car.company else None,
                }
            }

            # Add status history
            status_history = StatusHistory.objects.filter(booking=booking).order_by('-changed_at')
            history_data = {
                'status_history': [
                    {
                        'status': sh.status,
                        'changed_at': sh.changed_at,
                        'notes': sh.notes
                    } for sh in status_history
                ]
            }

            # Combine all data and add booking type
            response_data = {
                **booking_data,
                **user_data,
                **payment_data,
                **car_data,
                **history_data,
                'booking_type': 'car'
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except CarBooking.DoesNotExist:
            return Response(
                {"error": "Car booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def _get_flight_booking_details(self, booking):
        """Get detailed flight booking information"""
        try:
            flight_booking = FlightBooking.objects.get(booking=booking)

            # Get all related data
            booking_data = FlightBookingSerializer(flight_booking).data

            # Add user details
            user = booking.user
            user_data = {
                'user': {
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'phone_number': user.phone_number if hasattr(user, 'phone_number') else None,
                    'address': user.address if hasattr(user, 'address') else None,
                }
            }

            # Add flight details
            flights = Flight.objects.filter(flight_booking=flight_booking)
            flight_data = {
                'flights': [
                    {
                        'id': flight.id,
                        'departure_airport': flight.departure_airport,
                        'arrival_airport': flight.arrival_airport,
                        'departure_datetime': flight.departure_datetime,
                        'arrival_datetime': flight.arrival_datetime,
                        'airline_code': flight.airline_code,
                        'flight_number': flight.flight_number,
                        'cabin_class': flight.cabin_class,
                        'segment_id': flight.segment_id
                    } for flight in flights
                ]
            }

            # Add passenger details
            passenger_bookings = PassengerBooking.objects.filter(flight_booking=flight_booking)
            passenger_data = {
                'passengers': [
                    {
                        'first_name': pb.passenger.first_name,
                        'last_name': pb.passenger.last_name,
                        'email': pb.passenger.email,
                        'phone': pb.passenger.phone,
                        'passport_number': pb.passenger.passport_number,
                        'passport_expiry': pb.passenger.passport_expiry,
                        'nationality': pb.passenger.nationality,
                        'ticket_number': pb.ticket_number
                    } for pb in passenger_bookings
                ]
            }

            # Combine all data and add booking type
            response_data = {
                **booking_data,
                **user_data,
                **flight_data,
                **passenger_data,
                'booking_type': 'flight'
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except FlightBooking.DoesNotExist:
            return Response(
                {"error": "Flight booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def _update_car_booking(self, booking, request):
        """Update car booking details"""
        try:
            car_booking = CarBooking.objects.get(booking=booking)

            # Only allow updating certain fields
            allowed_fields = [
                'pickup_date', 'pickup_time',
                'dropoff_date', 'dropoff_time',
                'passengers', 'child_seats',
                'special_requests'
            ]
            update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

            if not update_data:
                return Response(
                    {"error": "No valid fields provided for update"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Store original values for history
            original_values = {field: getattr(car_booking, field) for field in update_data.keys()}

            # Update the booking
            for field, value in update_data.items():
                setattr(car_booking, field, value)
            car_booking.save()

            # Record change in history with before/after values
            field_changes = {
                field: {
                    'from': str(original_values[field]),
                    'to': str(update_data[field])
                } for field in update_data.keys()
            }

            self._record_booking_history(
                booking=booking,
                status='UPDATED',
                notes=f"Car booking updated by admin: {', '.join(update_data.keys())}",
                field_changes=field_changes
            )

            # For backward compatibility, also add to the old StatusHistory if it exists
            if hasattr(car_booking, 'StatusHistory'):
                StatusHistory.objects.create(
                    booking=car_booking.booking,
                    status='UPDATED',
                    changed_at=timezone.now(),
                    notes=f"Booking updated by admin: {', '.join(update_data.keys())}"
                )

            return Response(
                {"message": "Car booking updated successfully", "updated_fields": list(update_data.keys())},
                status=status.HTTP_200_OK
            )

        except CarBooking.DoesNotExist:
            return Response(
                {"error": "Car booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )



    def _update_flight_booking(self, booking, request):
        """Update flight details"""
        try:
            flight_booking = FlightBooking.objects.get(booking=booking)
            flight_id = request.data.get('flight_id')

            if not flight_id:
                return Response(
                    {"error": "flight_id is required in request data"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                flight = Flight.objects.get(id=flight_id, flight_booking=flight_booking)
            except Flight.DoesNotExist:
                return Response(
                    {"error": "Flight not found for this booking"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Only allow updating certain fields
            allowed_fields = ['departure_datetime', 'arrival_datetime', 'flight_number']
            update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

            if not update_data:
                return Response(
                    {"error": "No valid fields provided for update"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Store original values for history
            original_values = {field: getattr(flight, field) for field in update_data.keys()}

            # Update the flight
            for field, value in update_data.items():
                setattr(flight, field, value)
            flight.save()

            # Record change in history with before/after values
            field_changes = {
                field: {
                    'from': str(original_values[field]),
                    'to': str(update_data[field])
                } for field in update_data.keys()
            }

            self._record_booking_history(
                booking=booking,
                status='FLIGHT_UPDATED',
                notes=f"Flight #{flight_id} updated by admin: {', '.join(update_data.keys())}",
                field_changes=field_changes
            )

            return Response(
                {"message": "Flight updated successfully", "updated_fields": list(update_data.keys())},
                status=status.HTTP_200_OK
            )

        except FlightBooking.DoesNotExist:
            return Response(
                {"error": "Flight booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )



    def _cancel_car_booking(self, booking, request, process_refund, refund_amount, cancellation_reason):
        """Cancel a car booking with optional refund"""
        try:
            car_booking = CarBooking.objects.get(booking=booking)

            # Call the existing cancellation logic from CarBookingViewSet
            view = CarBookingViewSet()
            view.request = request
            view.format_kwarg = {}

            response = view.cancel_booking(request, pk=car_booking.id)

            if response.status_code == 200:
                # Add admin-specific cancellation notes
                car_booking.admin_notes = cancellation_reason
                car_booking.cancellation_reason = cancellation_reason
                car_booking.cancelled_by = request.user
                car_booking.save()

                # Add to new history tracking
                self._record_booking_history(
                    booking=booking,
                    status='CANCELLED',
                    notes=f"Car booking cancelled by admin: {cancellation_reason}",
                    field_changes={'cancellation_reason': cancellation_reason}
                )

                # Process refund if requested
                if process_refund:
                    refund_result = self._process_car_refund(
                        booking,
                        refund_amount=refund_amount,
                        reason=cancellation_reason
                    )

                    if 'error' in refund_result:
                        # Record refund failure
                        self._record_booking_history(
                            booking=booking,
                            status='REFUND_FAILED',
                            notes=f"Refund failed: {refund_result['error']}",
                            field_changes={'refund_error': refund_result['error']}
                        )

                        return Response(
                            {"message": "Booking cancelled but refund failed", "refund_error": refund_result['error']},
                            status=status.HTTP_207_MULTI_STATUS
                        )
                    else:
                        # Record successful refund
                        self._record_booking_history(
                            booking=booking,
                            status='REFUNDED',
                            notes=f"Refund processed: {refund_result['refund_id']}",
                            field_changes={'refund_details': refund_result}
                        )

                    return Response(
                        {"message": "Car booking cancelled and refund processed", "refund_details": refund_result},
                        status=status.HTTP_200_OK
                    )

                return Response(
                    {"message": "Car booking cancelled successfully (no refund processed)"},
                    status=status.HTTP_200_OK
                )
            else:
                return response

        except CarBooking.DoesNotExist:
            return Response(
                {"error": "Car booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def _cancel_flight_booking(self, booking, request, process_refund, refund_amount, cancellation_reason):
        """Cancel a flight booking with optional refund"""
        try:
            flight_booking = FlightBooking.objects.get(booking=booking)

            # Call the existing cancellation logic from FlightBookingViewSet
            view = FlightBookingViewSet()
            view.request = request
            view.format_kwarg = {}

            response = view.cancel_booking(request, pk=flight_booking.id)

            if response.status_code == 200:
                # Add admin-specific cancellation notes
                flight_booking.admin_notes = cancellation_reason
                flight_booking.save()

                # Add to new history tracking
                self._record_booking_history(
                    booking=booking,
                    status='CANCELLED',
                    notes=f"Flight booking cancelled by admin: {cancellation_reason}",
                    field_changes={'cancellation_reason': cancellation_reason}
                )

                # Process refund if requested
                if process_refund:
                    refund_result = self._process_flight_refund(
                        booking,
                        refund_amount=refund_amount,
                        reason=cancellation_reason
                    )

                    if 'error' in refund_result:
                        # Record refund failure
                        self._record_booking_history(
                            booking=booking,
                            status='REFUND_FAILED',
                            notes=f"Refund failed: {refund_result['error']}",
                            field_changes={'refund_error': refund_result['error']}
                        )

                        return Response(
                            {"message": "Booking cancelled but refund failed", "refund_error": refund_result['error']},
                            status=status.HTTP_207_MULTI_STATUS
                        )
                    else:
                        # Record successful refund
                        self._record_booking_history(
                            booking=booking,
                            status='REFUNDED',
                            notes=f"Refund processed: {refund_result['refund_id']}",
                            field_changes={'refund_details': refund_result}
                        )

                    return Response(
                        {"message": "Flight booking cancelled and refund processed", "refund_details": refund_result},
                        status=status.HTTP_200_OK
                    )

                return Response(
                    {"message": "Flight booking cancelled successfully (no refund processed)"},
                    status=status.HTTP_200_OK
                )
            else:
                return response

        except FlightBooking.DoesNotExist:
            return Response(
                {"error": "Flight booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def _process_car_refund(self, booking, refund_amount=None, reason=None):
        """Process refund for car booking through Stripe"""
        try:
            # Get the payment details
            payment = Payment.objects.filter(
                booking=booking,
                status='COMPLETED'
            ).first()

            if not payment:
                return {'error': 'No completed payment found for this booking'}

            stripe.api_key = (
                settings.STRIPE_SECRET_TEST_KEY
                if settings.AMADEUS_API_TESTING
                else settings.STRIPE_LIVE_SECRET_KEY
            )

            # Calculate refund amount (full or partial)
            amount_to_refund = refund_amount or payment.amount * 100  # Convert to cents

            # Create refund
            refund = stripe.Refund.create(
                payment_intent=payment.transaction_id,
                amount=int(amount_to_refund),
                reason='requested_by_customer' if not reason else 'other',
                metadata={
                    'admin_refund': 'true',
                    'booking_id': booking.id,
                    'reason': reason or 'Admin-initiated refund',
                    'admin_user': self.request.user.email
                }
            )

            # Update payment record
            payment.refund_amount = (refund_amount or payment.amount)
            payment.refund_date = timezone.now()
            new_status = 'REFUNDED' if (not refund_amount or refund_amount == payment.amount) else 'PARTIALLY_REFUNDED'
            payment.status = new_status
            payment.additional_details['refund_id'] = refund.id
            payment.save()

            # Add to unified history tracking
            refund_details = {
                'refund_id': refund.id,
                'amount_refunded': refund.amount / 100,
                'currency': refund.currency,
                'status': refund.status,
                'original_payment_id': payment.transaction_id
            }

            self._record_booking_history(
                booking=booking,
                status=new_status,
                notes=f"Refund processed by admin: {reason or 'No reason provided'}",
                field_changes=refund_details
            )

            # For backward compatibility
            if hasattr(booking, 'StatusHistory'):
                StatusHistory.objects.create(
                    booking=booking,
                    status=new_status,
                    changed_at=timezone.now(),
                    notes=f"Refund processed by admin: {reason or 'No reason provided'}"
                )

            return {
                'refund_id': refund.id,
                'amount_refunded': refund.amount / 100,
                'currency': refund.currency,
                'status': refund.status
            }

        except stripe.error.StripeError as e:
            return {'error': str(e), 'type': type(e).__name__}
        except Exception as e:
            return {'error': str(e)}

    def _process_flight_refund(self, booking, refund_amount=None, reason=None):
        """Process refund for flight booking through Stripe"""
        try:
            # Get the payment details
            payment = PaymentDetail.objects.filter(
                booking=booking,
                payment_status='COMPLETED'
            ).first()

            if not payment:
                return {'error': 'No completed payment found for this booking'}

            stripe.api_key = (
                settings.STRIPE_SECRET_TEST_KEY
                if settings.AMADEUS_API_TESTING
                else settings.STRIPE_LIVE_SECRET_KEY
            )

            # Calculate refund amount (full or partial)
            amount_to_refund = refund_amount or payment.amount * 100  # Convert to cents

            # Create refund
            refund = stripe.Refund.create(
                payment_intent=payment.transaction_id,
                amount=int(amount_to_refund),
                reason='requested_by_customer' if not reason else 'other',
                metadata={
                    'admin_refund': 'true',
                    'booking_id': booking.id,
                    'reason': reason or 'Admin-initiated refund'
                }
            )

            # Update payment record
            payment.refund_amount = (refund_amount or payment.amount)
            payment.refund_date = timezone.now()
            payment.payment_status = 'REFUNDED' if (not refund_amount or refund_amount == payment.amount) else 'PARTIALLY_REFUNDED'
            payment.additional_details['refund_id'] = refund.id
            payment.save()

            return {
                'refund_id': refund.id,
                'amount_refunded': refund.amount / 100,
                'currency': refund.currency,
                'status': refund.status
            }

        except stripe.error.StripeError as e:
            return {'error': str(e), 'type': type(e).__name__}
        except Exception as e:
            return {'error': str(e)}


    def _record_booking_history(self, booking, status, notes, changed_by=None, field_changes=None):
        """
        Universal method to record booking history for any booking type
        """
        booking_type = self._determine_booking_type(booking)

        BookingHistory.objects.create(
            booking=booking,
            status=status,
            notes=notes,
            changed_by=changed_by or self.request.user,
            booking_type=booking_type,
            field_changes=field_changes or {}
        )


    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='pk',
                description='Booking ID',
                required=True,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH
            )
        ]
    )

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        Get the full history trail for any booking type
        """
        try:
            booking = Booking.objects.get(pk=pk)

            # Get all history entries for this booking
            history_entries = BookingHistory.objects.filter(booking=booking)
            history_data = BookingHistorySerializer(history_entries, many=True).data

            # Also include legacy status history if it exists (for car bookings)
            try:
                legacy_history = StatusHistory.objects.filter(booking=booking)
                legacy_data = [
                    {
                        'id': f"legacy-{entry.id}",
                        'status': entry.status,
                        'changed_at': entry.changed_at,
                        'notes': entry.notes,
                        'changed_by': None,
                        'booking_type': self._determine_booking_type(booking),
                        'field_changes': {},
                        'legacy': True
                    }
                    for entry in legacy_history
                ]

                # Combine both histories
                combined_history = list(history_data) + legacy_data
                # Sort by timestamp
                combined_history.sort(key=lambda x: x['changed_at'], reverse=True)

                return Response(combined_history, status=status.HTTP_200_OK)

            except:
                # If no legacy history, just return the new history
                return Response(history_data, status=status.HTTP_200_OK)

        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )

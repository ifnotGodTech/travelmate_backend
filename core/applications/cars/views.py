from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils.crypto import get_random_string
from datetime import datetime
from rest_framework.permissions import IsAdminUser
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
import stripe
from django.conf import settings
from rest_framework.exceptions import APIException
from django.db import transaction

from .utils import AmadeusService
from .models import CarBooking, Location, Car, Booking, Payment, CarCategory, CarCompany, StatusHistory, CarServiceFee
from .serializers import (
    CarBookingSerializer, LocationSerializer, CarSerializer,
    PaymentSerializer, CarCategorySerializer, CarCompanySerializer, CarServiceFeeSerializer, TransferSearchSerializer
)

from .car_schemas import (
    location_schema,
    car_category_schema,
    car_company_schema,
    transfer_search_schema,
    car_booking_schema,
    payment_schema
)

from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

amadeus_service = AmadeusService()


class StripePaymentProcessor:
    """
    Payment processor specifically for car bookings
    (Maintaining transfer booking naming conventions)
    """
    def __init__(self, vehicle_type='STANDARD'):
        # Get fee configuration based on vehicle type
        fee_config = CarServiceFee.get_current_fee(vehicle_type)
        self.service_rate_percentage = fee_config['percentage'] / Decimal('100')
        self.minimum_fee = fee_config['minimum_fee']

        # Stripe configuration
        stripe.api_key = (
            settings.STRIPE_SECRET_TEST_KEY
            if settings.AMADEUS_API_TESTING
            else settings.STRIPE_LIVE_SECRET_KEY
        )

    def calculate_total_price(self, base_price):
        """
        Calculate total price including service fee
        Applies either percentage or minimum fee, whichever is higher
        """
        percentage_fee = base_price * self.service_rate_percentage
        service_fee = max(percentage_fee, self.minimum_fee)
        return base_price + service_fee

    def split_payment(self, total_price):
        """
        Split payment between service and actual transfer cost
        """
        percentage_fee = total_price * self.service_rate_percentage
        service_fee = max(percentage_fee, self.minimum_fee)
        transfer_cost = total_price - service_fee

        return {
            'total_price': total_price,
            'transfer_cost': transfer_cost,
            'service_fee': service_fee,
            'service_fee_percentage': float(self.service_rate_percentage * 100),
            'minimum_fee': float(self.minimum_fee)
        }

    def create_payment_intent(self, booking=None, car_booking=None, payment_method=None):
        """
        Create Stripe Payment Intent for car booking
        """
        try:
            # Use total_price from booking and currency from car_booking
            total_price = self.calculate_total_price(Decimal(str(booking.total_price)))
            currency = car_booking.currency.lower()

            payment_split = self.split_payment(total_price)

            payment_intent = stripe.PaymentIntent.create(
                amount=int(float(total_price) * 100),  # Convert to cents
                currency=currency,
                payment_method=payment_method,
                confirm=True,
                automatic_payment_methods={
                    "enabled": True,
                    "allow_redirects": "never"  # Prevents redirect-based payments
                },
                metadata={
                    'booking_id': booking.id,
                    'transfer_cost': float(payment_split['transfer_cost']),  # Convert to float
                    'service_fee': float(payment_split['service_fee']),
                    'service_fee_percentage': float(payment_split['service_fee_percentage']),
                    'minimum_fee': float(payment_split['minimum_fee']),
                    'vehicle_type': getattr(car_booking, 'vehicle_type', 'STANDARD')
                }
            )

            return {
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'payment_split': payment_split
            }

        except stripe.error.StripeError as e:
            return {
                'error': str(e),
                'type': type(e).__name__
            }

@location_schema
class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if len(query) < 3:
            return Response({'error': 'Query must be at least 3 characters long'}, status=status.HTTP_400_BAD_REQUEST)

        cache_key = f"location_search:{query}"
        cached_results = cache.get(cache_key)

        if cached_results:
            return Response(cached_results)

        locations = Location.objects.filter(name__icontains=query) | \
                    Location.objects.filter(city__icontains=query) | \
                    Location.objects.filter(country__icontains=query)

        serializer = self.get_serializer(locations, many=True)
        cache.set(cache_key, serializer.data, 3600)  # Cache for 1 hour

        return Response(serializer.data)

@car_category_schema
class CarCategoryViewSet(viewsets.ModelViewSet):
    queryset = CarCategory.objects.all()
    serializer_class = CarCategorySerializer

@car_company_schema
class CarCompanyViewSet(viewsets.ModelViewSet):
    queryset = CarCompany.objects.all()
    serializer_class = CarCompanySerializer



@transfer_search_schema
class TransferSearchViewSet(viewsets.ViewSet):
    serializer_class = TransferSearchSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'])
    def search(self, request):
        """
        Search for transfers with a POST request
        """
        data = request.data

        # Get required parameters
        pickup_location = data.get('pickup_location')
        dropoff_location = data.get('dropoff_location')
        pickup_date = data.get('pickup_date')
        pickup_time = data.get('pickup_time')
        passengers = data.get('passengers', 1)  # Make passengers optional with default value of 1
        transfer_type = data.get('transfer_type', 'PRIVATE')
        currency = data.get('currency', 'EUR')

        # Validate required parameters
        if not all([pickup_location, pickup_date, pickup_time]):
            return Response(
                {'error': 'Missing required parameters: pickup_location, pickup_date, pickup_time'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate required parameters
        if not all([pickup_location, pickup_date, pickup_time]):
            return Response(
                {'error': 'Missing required parameters: pickup_location, pickup_date, pickup_time'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # For city destinations, we need an address
        if not data.get('end_address') and not dropoff_location.isalpha():
            return Response(
                {'error': 'Please provide an end_address for the destination'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate currency format (optional)
        if currency and not isinstance(currency, str) or len(currency) != 3:
            return Response(
                {'error': 'Currency must be a valid 3-letter code (e.g. EUR, USD)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check for geocodes but don't require them
        if data.get('end_address') and not (data.get('end_geo_lat') and data.get('end_geo_long')):
            logger.warning("Address provided without geocodes. Amadeus API might require them.")

        # Get filter parameters, ensuring price_min and price_max are properly validated
        try:
            price_min = float(data.get('price_min')) if data.get('price_min') else None
            price_max = float(data.get('price_max')) if data.get('price_max') else None

            # Validate price range if both are provided
            if price_min is not None and price_max is not None and price_min > price_max:
                return Response(
                    {'error': 'price_min cannot be greater than price_max'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {'error': 'price_min and price_max must be valid numbers'},
                status=status.HTTP_400_BAD_REQUEST
            )

        filters = {
            'vehicle_type': data.get('vehicle_type'),
            'price_min': price_min,
            'price_max': price_max,
            'end_address': data.get('end_address'),
            'end_city': data.get('end_city'),
            'end_zipcode': data.get('end_zipcode'),
            'end_country': data.get('end_country'),
            'end_name': data.get('end_name'),
            'end_geo_lat': data.get('end_geo_lat'),
            'end_geo_long': data.get('end_geo_long'),
            'connected_flight': data.get('connected_flight'),
            'flight_number': data.get('flight_number'),
            'flight_departure_time': data.get('flight_departure_time'),
            'flight_departure_location': data.get('flight_departure_location'),
            'flight_arrival_time': data.get('flight_arrival_time'),
            'flight_arrival_location': data.get('flight_arrival_location'),
            'currency': currency.upper()
        }

        try:
            # Parse datetime
            pickup_datetime = datetime.strptime(f"{pickup_date} {pickup_time}", "%Y-%m-%d %H:%M")

            # Get current datetime
            now = datetime.now()

            # Check if the pickup datetime is in the past
            if pickup_datetime < now:
                return Response(
                    {'error': 'Pickup date and time cannot be in the past'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Search transfers via Amadeus API
            transfers = amadeus_service.search_transfers(
                pickup_location,
                dropoff_location,
                pickup_datetime,
                int(passengers),
                transfer_type,
                **filters
            )

            # If we got an error about geocodes, return a more helpful message
            if transfers and isinstance(transfers, list) and len(transfers) == 1 and 'error' in transfers[0] and 'Geocodes required' in transfers[0]['error']:
                return Response({
                    'error': 'The Amadeus API requires geocodes for this address. Please provide end_geo_lat and end_geo_long.',
                    'suggestion': 'You can use a geocoding service like Google Maps API to get coordinates for the address.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Store both individual transfer details and overall search results
            search_results_cache_key = 'recent_transfer_search_results'
            cache.set(search_results_cache_key, transfers, 3600)

            # Cache each transfer individually for details lookup
            for transfer in transfers:
                if 'id' in transfer:
                    cache_key = f"transfer_details:{transfer['id']}"
                    cache.set(cache_key, transfer, 3600)  # Cache for 1 hour

            return Response(transfers)
        except ValueError:
            return Response({'error': 'Invalid date/time format'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def details(self, request):
        """
        Get details of a specific transfer by ID
        """
        transfer_id = request.query_params.get('transfer_id')

        if not transfer_id:
            return Response(
                {'error': 'Missing required parameter: transfer_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Try to get from cache first
        cache_key = f"transfer_details:{transfer_id}"
        transfer_details = cache.get(cache_key)

        if transfer_details:
            return Response(transfer_details)
        else:
            # Could implement a direct fetch from Amadeus API here if needed
            return Response(
                {'error': 'Transfer details not found or expired'},
                status=status.HTTP_404_NOT_FOUND
            )


class TransferBookingError(APIException):
    status_code = 400
    default_detail = 'Transfer booking error occurred'
    default_code = 'transfer_booking_error'

    def __init__(self, detail=None, code=None):
        super().__init__(detail=detail, code=code)
        if code:
            self.status_code = code

@car_booking_schema
class CarBookingViewSet(viewsets.ModelViewSet):
    queryset = CarBooking.objects.all()
    serializer_class = CarBookingSerializer

    def get_queryset(self):
        """Filter bookings to only show the current user's bookings"""
        if self.request.user.is_staff:
            return CarBooking.objects.all()
        return CarBooking.objects.filter(booking__user=self.request.user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            # Get transfer details from request
            transfer_id = request.data.get('transfer_id')
            cache_key = f"transfer_details:{transfer_id}"
            transfer_details = cache.get(cache_key)

            # Extract customer details from request
            customer_details = request.data.get('customer', {})

            # Validate required customer fields
            required_fields = ['firstName', 'lastName', 'contacts']
            for field in required_fields:
                if field not in customer_details:
                    raise TransferBookingError(
                        detail=f'Missing required customer field: {field}',
                        code=status.HTTP_400_BAD_REQUEST
                    )

            # Further validation for contacts
            contacts = customer_details.get('contacts', {})
            if not contacts.get('email') or not contacts.get('phoneNumber'):
                raise TransferBookingError(
                    detail='Email and phone number are required',
                    code=status.HTTP_400_BAD_REQUEST
                )

            # Logging for debugging
            logger.info(f"Transfer ID: {transfer_id}")
            logger.info(f"Transfer details: {transfer_details}")

            if not transfer_details:
                raise TransferBookingError(
                    detail='Transfer details not found or expired. Please search for transfers again.',
                    code=status.HTTP_404_NOT_FOUND
                )

            # Extract details from transfer_details
            price_info = transfer_details.get('price', {})
            start_location = transfer_details.get('start_location', {})
            end_location = transfer_details.get('end_location', {})

            # Find or create Location objects
            try:
                pickup_location_obj, _ = Location.objects.get_or_create(
                    code=start_location.get('code'),
                    defaults={
                        'name': start_location.get('code'),
                        'city': start_location.get('code'),  # Fallback
                        'country': 'GB'  # Default, should be dynamic
                    }
                )

                dropoff_location_obj, _ = Location.objects.get_or_create(
                    code=end_location.get('code') or end_location.get('city'),
                    defaults={
                        'name': end_location.get('city', 'Unknown'),
                        'city': end_location.get('city'),
                        'address': end_location.get('address'),
                        'country': end_location.get('country', 'GB')
                    }
                )
            except Exception as e:
                logger.error(f"Error creating location objects: {str(e)}")
                raise TransferBookingError(
                    detail='Could not create location objects',
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Add car information
            try:
                # Fetch the vehicle name and type
                car_model = transfer_details.get('vehicle_name', 'Unknown')
                car_type = transfer_details.get('vehicle_type', 'SDN')

                # Ensure there's at least one CarCategory
                default_category, _ = CarCategory.objects.get_or_create(
                    name="Standard", defaults={"description": "Default category for standard vehicles"}
                )

                # Ensure there's at least one CarCompany
                default_company, _ = CarCompany.objects.get_or_create(
                    name="Default Company"
                )

                # Get or create the Car object
                car, created = Car.objects.get_or_create(
                    model=car_model,
                    defaults={
                        'passenger_capacity': transfer_details.get('capacity', 3),
                        'base_price_per_day': Decimal('0.00'),
                        'minimum_acceptable_price': Decimal('0.00'),
                        'transmission': 'automatic',
                        'category': default_category,
                        'company': default_company,
                    }
                )
            except Exception as e:
                logger.error(f"Error creating car object: {str(e)}")
                raise TransferBookingError(
                    detail='Could not create car object',
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Extract price information
            base_price = Decimal(str(price_info.get('amount', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            currency = price_info.get('currency', 'USD')

            if not base_price:
                raise TransferBookingError(
                    detail='Price information not available',
                    code=status.HTTP_400_BAD_REQUEST
                )

            # Calculate service fee
            stripe_processor = StripePaymentProcessor(
                vehicle_type=transfer_details.get('vehicle_type', 'STANDARD')
            )
            percentage_fee = base_price * stripe_processor.service_rate_percentage
            service_fee = max(percentage_fee, stripe_processor.minimum_fee)
            total_price = base_price + service_fee

            # Ensure decimal places are rounded
            base_price = base_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            service_fee = service_fee.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_price = total_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # Prepare booking data for our new serializer
            booking_data = {
                'user': request.user.id,  # Will be handled by serializer if not provided
                'status': 'PENDING',
                'total_price': total_price,
                'car': car.id,
                'transfer_id': transfer_id,
                'pickup_location': pickup_location_obj.id,
                'dropoff_location': dropoff_location_obj.id,
                'pickup_date': start_location.get('datetime')[:10],
                'pickup_time': start_location.get('datetime')[11:16],
                'dropoff_date': end_location.get('datetime')[:10],
                'dropoff_time': end_location.get('datetime')[11:16],
                'passengers': request.data.get('passengers', 1),
                'child_seats': request.data.get('child_seats', 0),
                'base_transfer_cost': base_price,
                'service_fee': service_fee,
                'booking_reference': get_random_string(10).upper(),
                'currency': price_info.get('currency', 'EUR'),
                'customer_first_name': customer_details.get('firstName'),
                'customer_last_name': customer_details.get('lastName'),
                'customer_title': customer_details.get('title', ''),
                'customer_email': contacts.get('email'),
                'customer_phone': contacts.get('phoneNumber')
            }

            # Validate and save booking using our new serializer
            serializer = self.get_serializer(data=booking_data)
            serializer.is_valid(raise_exception=True)
            car_booking = serializer.save()

            # Create initial status history record
            # Note: We now need to access the base booking through car_booking.booking
            StatusHistory.objects.create(
                booking=car_booking.booking,
                status='PENDING',
                changed_at=timezone.now(),
                notes='Booking created'
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except TransferBookingError as e:
            raise
        except Exception as e:
            logger.error(f"Error creating transfer booking: {str(e)}", exc_info=True)
            raise TransferBookingError(detail="An unexpected error occurred while creating booking")

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def process_payment(self, request, pk=None):
        try:
            car_booking = self.get_object()
            booking = car_booking.booking  # Get the base booking

            # Validate booking status
            if booking.status != 'PENDING':
                raise TransferBookingError(
                    detail="Booking is not in a pending state",
                    code=status.HTTP_400_BAD_REQUEST
                )

            # Validate payment method
            payment_method = request.data.get('payment_method_id')
            if not payment_method:
                raise TransferBookingError(
                    detail="Payment method ID is required",
                    code=status.HTTP_400_BAD_REQUEST
                )

            # Process payment
            payment_successful, payment_result = self._process_payment_with_gateway(
                booking,
                payment_method
            )

            if not payment_successful:
                raise TransferBookingError(
                    detail=payment_result,
                    code=status.HTTP_400_BAD_REQUEST
                )

            # Create Amadeus booking
            try:
                amadeus_booking_successful = self._create_amadeus_booking(car_booking)
                if not amadeus_booking_successful:
                    raise Exception("Failed to create Amadeus booking")

            except Exception as amadeus_error:
                # Refund payment if Amadeus booking fails
                try:
                    if 'payment_intent_id' in payment_result:
                        stripe.Refund.create(
                            payment_intent=payment_result['payment_intent_id']
                        )
                        StatusHistory.objects.create(
                            booking=booking,
                            status='REFUNDED',
                            changed_at=timezone.now(),
                            notes=f"Refund initiated due to Amadeus booking failure: {str(amadeus_error)}"
                        )
                except Exception as refund_error:
                    logger.error(f"Refund failed: {str(refund_error)}")

                booking.status = 'AMADEUS_FAILED'
                booking.save()

                raise TransferBookingError(
                    detail=str(amadeus_error),
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response({
                'booking': CarBookingSerializer(car_booking).data,
                'payment_details': payment_result
            }, status=status.HTTP_200_OK)

        except TransferBookingError as e:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in process_payment: {str(e)}", exc_info=True)
            raise TransferBookingError(detail="An unexpected error occurred during payment processing")

    def _process_payment_with_gateway(self, booking, payment_method):
        """
        Process payment with Stripe, capturing service fee split
        """
        try:
            stripe_processor = StripePaymentProcessor()
            car_booking = booking.car_booking  # Get the car_booking object

            # Create payment intent - pass both objects or necessary data
            payment_result = stripe_processor.create_payment_intent(
                booking=booking,           # for total_price
                car_booking=car_booking,   # for currency
                payment_method=payment_method
            )

            # Check for errors
            if 'error' in payment_result:
                return False, payment_result['error']

            # Extract payment split details
            payment_split = payment_result.get('payment_split', {})

            # Create payment record with detailed split
            Payment.objects.create(
                booking=booking,
                amount=float(payment_split.get('total_price', booking.total_price)),
                currency=car_booking.currency,  # Use car_booking.currency here
                payment_method='STRIPE',
                transaction_id=payment_result.get('payment_intent_id'),
                status='COMPLETED',
                transaction_date=timezone.now(),
                additional_details={
                    'transfer_cost': float(payment_split.get('transfer_cost', 0)),
                    'service_fee': float(payment_split.get('service_fee', 0)),
                    'payment_intent_id': payment_result.get('payment_intent_id'),
                    'service_fee_percentage': float(payment_split.get('service_fee_percentage', 0))
                }
            )

            return True, payment_result
        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}", exc_info=True)
            return False, str(e)


    def _create_amadeus_booking(self, car_booking):
        """
        Create the actual booking with Amadeus API
        Modified to work with CarBooking model
        """
        try:
            amadeus_service = AmadeusService()
            booking = car_booking.booking  # Access the base Booking

            # Retrieve the original transfer details from cache
            cache_key = f"transfer_details:{car_booking.transfer_id}"
            transfer_details = cache.get(cache_key)

            if not transfer_details:
                logger.error(f"No transfer details found for transfer_id: {car_booking.transfer_id}")
                return False

            # Get location objects from database
            pickup_location = Location.objects.get(id=car_booking.pickup_location_id)
            dropoff_location = Location.objects.get(id=car_booking.dropoff_location_id)

            # Prepare payload for Amadeus API
            amadeus_payload = {
                "data": {
                    "type": "transferBooking",
                    "transferId": car_booking.transfer_id,
                    "customer": {
                                    "firstName": car_booking.customer_first_name,
                                    "lastName": car_booking.customer_last_name,
                                    "title": car_booking.customer_title,
                                    "email": car_booking.customer_email,
                                    "phone": car_booking.customer_phone,
                                    "countryCode": pickup_location.country or "US"
                                },
                    "pickup": {
                        "locationId": pickup_location.code,
                        "date": car_booking.pickup_date.strftime('%Y-%m-%d'),
                        "time": car_booking.pickup_time.strftime('%H:%M'),
                        "address": {
                            "line1": pickup_location.address or transfer_details.get('start_location', {}).get('address', ''),
                            "city": pickup_location.city,
                            "postalCode": transfer_details.get('start_location', {}).get('postalCode', ''),
                            "country": pickup_location.country,
                        }
                    },
                    "dropoff": {
                        "locationId": dropoff_location.code,
                        "address": {
                            "line1": dropoff_location.address or '',
                            "city": dropoff_location.city,
                            "country": dropoff_location.country,
                        }
                    },
                    "passengers": car_booking.passengers,
                    "vehicle": {
                        "type": transfer_details.get('vehicle_type', 'STANDARD')
                    },
                    "price": {
                        "amount": float(car_booking.base_transfer_cost),
                        "currency": car_booking.currency
                    },
                    "remarks": f"Booking created via API for booking {car_booking.booking_reference}"
                }
            }

            # If there are child seats, add them to the payload
            if car_booking.child_seats > 0:
                amadeus_payload["data"]["extras"] = [
                    {"type": "CHILD_SEAT", "quantity": car_booking.child_seats}
                ]

            # Log the complete payload for debugging
            logger.info(f"Creating transfer booking with payload: {amadeus_payload}")

            # Make API call to create booking
            response = amadeus_service.create_transfer_booking(amadeus_payload)

            if response.status_code != 201:
                error_msg = f"Amadeus API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False

            # Process successful response
            response_data = response.json()
            car_booking.amadeus_booking_reference = response_data.get('data', {}).get('id')

            # Update the base booking status
            booking.status = 'CONFIRMED'
            booking.save()

            # Save the car booking with the amadeus reference
            car_booking.save()

            # Add to status history
            StatusHistory.objects.create(
                booking=booking,
                status='CONFIRMED',
                changed_at=timezone.now(),
                notes=f"Amadeus booking reference: {car_booking.amadeus_booking_reference}"
            )

            return True

        except Exception as e:
            logger.error(f"Error creating Amadeus booking: {str(e)}", exc_info=True)
            return False

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel_booking(self, request, pk=None):
        try:
            car_booking = self.get_object()
            booking = car_booking.booking  # Get the base booking

            if booking.status == 'CANCELLED':
                raise TransferBookingError(
                    detail="This booking is already cancelled",
                    code=status.HTTP_400_BAD_REQUEST
                )

            # Call Amadeus API to cancel booking
            if car_booking.amadeus_booking_reference:
                amadeus_service = AmadeusService()
                cancellation_successful = amadeus_service.cancel_transfer_booking(
                    car_booking.amadeus_booking_reference
                )

                if not cancellation_successful:
                    raise TransferBookingError(
                        detail="Failed to cancel booking with Amadeus",
                        code=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            # Update booking status
            booking.status = 'CANCELLED'
            booking.save()

            # Add to status history
            StatusHistory.objects.create(
                booking=booking,
                status='CANCELLED',
                changed_at=timezone.now(),
                notes="Booking cancelled by user"
            )

            # Initiate refund if applicable
            if request.data.get('request_refund', False):
                try:
                    payment = booking.payments.filter(status='COMPLETED').first()
                    if payment:
                        stripe.Refund.create(
                            payment_intent=payment.transaction_id
                        )
                        payment.status = 'REFUND_PENDING'
                        payment.save()

                        StatusHistory.objects.create(
                            booking=booking,
                            status='REFUND_PENDING',
                            changed_at=timezone.now(),
                            notes="Refund initiated"
                        )
                except Exception as e:
                    logger.error(f"Error processing refund: {str(e)}")

            return Response(
                CarBookingSerializer(car_booking).data,
                status=status.HTTP_200_OK
            )

        except TransferBookingError as e:
            raise
        except Exception as e:
            logger.error(f"Error cancelling booking: {str(e)}", exc_info=True)
            raise TransferBookingError(
                detail="An unexpected error occurred while cancelling booking",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@payment_schema
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_queryset(self):
        """
        Return only payments for the current user's bookings
        """
        return Payment.objects.filter(booking__user=self.request.user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            booking_id = request.data.get('booking_id')
            payment_method = request.data.get('payment_method')

            if not booking_id or not payment_method:
                raise TransferBookingError(
                    detail="Both booking_id and payment_method are required",
                    code=status.HTTP_400_BAD_REQUEST
                )

            booking = get_object_or_404(Booking, id=booking_id, user=request.user)

            # Validate booking status
            if booking.status != 'PENDING':
                raise TransferBookingError(
                    detail="Payment can only be processed for pending bookings",
                    code=status.HTTP_400_BAD_REQUEST
                )

            # In a real implementation, this would be handled by process_payment action
            # This endpoint should only be used for recording manual payments or other gateways
            payment_data = {
                'booking': booking_id,
                'amount': booking.total_price,
                'currency': booking.currency,
                'payment_method': payment_method,
                'transaction_id': get_random_string(20),
                'status': 'COMPLETED',
                'transaction_date': timezone.now(),
                'additional_details': {
                    'manual_processing': True,
                    'notes': 'Manually recorded payment'
                }
            }

            serializer = self.get_serializer(data=payment_data)
            serializer.is_valid(raise_exception=True)
            payment = serializer.save()

            # Update booking status
            booking.update_status('CONFIRMED')

            # Add status history
            StatusHistory.objects.create(
                booking=booking,
                status='CONFIRMED',
                changed_at=timezone.now(),
                notes=f"Payment recorded manually via {payment_method}"
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except TransferBookingError as e:
            raise
        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}", exc_info=True)
            raise TransferBookingError(
                detail="An unexpected error occurred while recording payment",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def refund(self, request, pk=None):
        """
        Initiate a refund for a payment
        """
        try:
            payment = self.get_object()

            if payment.status != 'COMPLETED':
                raise TransferBookingError(
                    detail="Only completed payments can be refunded",
                    code=status.HTTP_400_BAD_REQUEST
                )

            # For Stripe payments
            if payment.payment_method == 'STRIPE' and payment.transaction_id:
                try:
                    refund = stripe.Refund.create(
                        payment_intent=payment.transaction_id
                    )
                    payment.status = 'REFUNDED'
                    payment.additional_details['refund_id'] = refund.id
                    payment.save()

                    # Update booking status if this was the only payment
                    if payment.booking.payments.filter(status='COMPLETED').count() == 0:
                        payment.booking.update_status('CANCELLED')
                        StatusHistory.objects.create(
                            booking=payment.booking,
                            status='CANCELLED',
                            changed_at=timezone.now(),
                            notes="Booking cancelled due to full refund"
                        )

                    return Response(
                        {"status": "refund_processed", "refund_id": refund.id},
                        status=status.HTTP_200_OK
                    )

                except Exception as e:
                    logger.error(f"Stripe refund failed: {str(e)}")
                    raise TransferBookingError(
                        detail=f"Refund processing failed: {str(e)}",
                        code=status.HTTP_502_BAD_GATEWAY
                    )

            # For non-Stripe payments
            else:
                payment.status = 'REFUNDED'
                payment.save()

                return Response(
                    {"status": "refund_recorded"},
                    status=status.HTTP_200_OK
                )

        except TransferBookingError as e:
            raise
        except Exception as e:
            logger.error(f"Error processing refund: {str(e)}", exc_info=True)
            raise TransferBookingError(
                detail="An unexpected error occurred while processing refund",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

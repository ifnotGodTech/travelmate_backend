from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse
import uuid
import requests
from .models import FlightBooking, Flight, Passenger, PassengerBooking, PaymentDetail, ServiceFeeSetting
from .serializers import (
    FlightBookingSerializer,
    FlightBookingInputSerializer,
    PaymentInputSerializer
)

from .utils import AmadeusAPI
from .serializers import FlightSearchSerializer, MultiCityFlightSearchSerializer
from datetime import datetime
import stripe
from django.conf import settings
from decimal import Decimal

class StripePaymentProcessor:
    """
    Payment processor for handling Stripe payments with custom rate
    """
    def __init__(self):
        # Retrieve service fee from the model
        self.service_rate_percentage = ServiceFeeSetting.get_current_fee() / Decimal('100')


        # Set up Stripe with the appropriate key based on testing mode
        stripe.api_key = (
            settings.STRIPE_SECRET_TEST_KEY
            if settings.AMADEUS_API_TESTING
            else settings.STRIPE_LIVE_SECRET_KEY
        )

    def calculate_total_price(self, amadeus_price):
        """
        Calculate total price including Amadeus price and service rate

        Args:
            amadeus_price (Decimal): Base price from Amadeus

        Returns:
            Decimal: Total price with service rate
        """
        service_fee = amadeus_price * self.service_rate_percentage
        return amadeus_price + service_fee

    def split_payment(self, total_price):
        """
        Split payment between service and actual flight cost

        Args:
            total_price (Decimal): Total price including service rate

        Returns:
            Dict: Split of service fee and flight cost
        """
        service_fee = total_price * self.service_rate_percentage
        flight_cost = total_price - service_fee

        return {
            'total_price': total_price,
            'flight_cost': flight_cost,
            'service_fee': service_fee,
            'service_fee_percentage': float(self.service_rate_percentage * 100)
        }

    def create_payment_intent(self, booking, payment_method):
        """
        Create a Stripe Payment Intent

        Args:
            booking (FlightBooking): Booking instance
            payment_method (str): Stripe payment method ID

        Returns:
            Dict: Stripe payment intent details
        """
        try:
            # Calculate total price with service rate
            total_price = self.calculate_total_price(booking.total_price)
            payment_split = self.split_payment(total_price)

            # Create Payment Intent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(total_price * 100),  # Convert to cents
                currency=booking.currency.lower(),
                payment_method=payment_method,
                confirm=True,
                automatic_payment_methods={
                    "enabled": True,
                    "allow_redirects": "never"
                },
                metadata={
                    'booking_id': booking.id,
                    'flight_cost': float(payment_split['flight_cost']),
                    'service_fee': float(payment_split['service_fee']),
                    'service_fee_percentage': float(payment_split['service_fee_percentage'])
                }
            )

            return {
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'payment_split': {
                'total_price': float(payment_split['total_price']),
                'flight_cost': float(payment_split['flight_cost']),
                'service_fee': float(payment_split['service_fee']),
                'service_fee_percentage': float(payment_split['service_fee_percentage'])
            }
            }

        except stripe.error.StripeError as e:
            # Handle Stripe-specific errors
            return {
                'error': str(e),
                'type': type(e).__name__
            }


class FlightBookingViewSet(viewsets.ModelViewSet):
    queryset = FlightBooking.objects.all()
    serializer_class = FlightBookingSerializer

    def get_queryset(self):
        """
        Filter bookings to return only those belonging to the current user
        """
        return FlightBooking.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def create_booking(self, request):
        """
        Create a new flight booking with passenger details and flight offer IDs
        """
        serializer = FlightBookingInputSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        flight_offer_ids = serializer.validated_data['flight_offer_ids']
        passengers_data = serializer.validated_data['passengers']
        booking_type = serializer.validated_data['booking_type']

        # Retrieve full flight offers from cache
        flight_offers = []
        for offer_id in flight_offer_ids:
            cache_key = f"flight_offer_{offer_id}"
            cached_offer = cache.get(cache_key)

            if not cached_offer:
                return Response(
                    {"error": f"Flight offer {offer_id} not found. Please perform a new search."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            flight_offers.append(cached_offer)

        # Calculate pricing with service fee
        stripe_processor = StripePaymentProcessor()
        base_price = Decimal(str(flight_offers[0].get('price', {}).get('total', 0)))

        # Calculate total price with service fee
        total_price_with_service = stripe_processor.calculate_total_price(base_price)
        service_fee = total_price_with_service - base_price

        # Create the booking
        booking = FlightBooking.objects.create(
            booking_reference=uuid.uuid4().hex[:10].upper(),
            user=request.user,
            booking_type=booking_type,
            total_price=total_price_with_service,
            base_flight_cost=base_price,
            service_fee=service_fee,
            currency='USD',  # Default currency, should ideally come from flight offer
        )

        # Create flight records from the cached flight offers
        for flight_offer in flight_offers:
            Flight.objects.create(
                booking=booking,
                departure_airport=flight_offer['itineraries'][0]['segments'][0]['departure']['iataCode'],
                arrival_airport=flight_offer['itineraries'][0]['segments'][-1]['arrival']['iataCode'],
                departure_datetime=datetime.strptime(
                    flight_offer['itineraries'][0]['segments'][0]['departure']['at'],
                    '%Y-%m-%dT%H:%M:%S'
                ),
                arrival_datetime=datetime.strptime(
                    flight_offer['itineraries'][0]['segments'][-1]['arrival']['at'],
                    '%Y-%m-%dT%H:%M:%S'
                ),
                airline_code=flight_offer['itineraries'][0]['segments'][0]['carrierCode'],
                flight_number=flight_offer['itineraries'][0]['segments'][0]['number'],
                cabin_class=flight_offer.get('class', 'ECONOMY'),
                segment_id=flight_offer['itineraries'][0]['segments'][0]['id']
            )

        # Create passenger records and link them to the booking
        for passenger_data in passengers_data:
            try:
                # Try to find the passenger by email AND passport number
                passenger = Passenger.objects.get(
                    email=passenger_data['email'],
                    passport_number=passenger_data['passport_number']
                )

                # Update existing passenger info
                for key, value in passenger_data.items():
                    setattr(passenger, key, value)
                passenger.save()

            except Passenger.DoesNotExist:
                # Create a new passenger
                passenger = Passenger.objects.create(**passenger_data)
            except Passenger.MultipleObjectsReturned:
                # Handle the case where multiple passengers match
                passenger = Passenger.objects.filter(
                    email=passenger_data['email'],
                    passport_number=passenger_data['passport_number']
                ).order_by('-id').first()

                # Update this passenger with the new data
                for key, value in passenger_data.items():
                    setattr(passenger, key, value)
                passenger.save()

            # Create passenger booking link
            PassengerBooking.objects.create(
                booking=booking,
                passenger=passenger
            )

        # Return the booking data
        return Response(
            FlightBookingSerializer(booking).data,
            status=status.HTTP_201_CREATED
        )


    @action(detail=True, methods=['post'])
    @transaction.atomic
    def process_payment(self, request, pk=None):
        """
        Process payment for a booking
        """
        booking = self.get_object()

        if booking.booking_status != 'PENDING':
            return Response(
                {"error": "This booking is not in a pending state and cannot be paid for."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PaymentInputSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Process payment with Stripe
        payment_successful, payment_result = self._process_payment_with_gateway(
            booking,
            serializer.validated_data
        )

        if payment_successful:
            # Create Amadeus booking
            amadeus_booking_successful = self._create_amadeus_booking(booking)

            if amadeus_booking_successful:
                return Response(
                    {
                        'booking': FlightBookingSerializer(booking).data,
                        'payment_details': payment_result
                    },
                    status=status.HTTP_200_OK
                )
            else:
                # Refund the payment if Amadeus booking fails
                stripe.Refund.create(
                    payment_intent=payment_result['payment_intent_id']
                )

                booking.booking_status = 'PENDING'
                booking.save()

                return Response(
                    {"error": "Failed to create booking with Amadeus"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {"error": payment_result},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancel_booking(self, request, pk=None):
        """
        Cancel a booking
        """
        booking = self.get_object()

        if booking.booking_status == 'CANCELLED':
            return Response(
                {"error": "This booking is already cancelled"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Here you would call Amadeus API to cancel the booking
        amadeus_cancellation_successful = self._cancel_amadeus_booking(booking)

        if amadeus_cancellation_successful:
            booking.booking_status = 'CANCELLED'
            booking.save()

            return Response(
                FlightBookingSerializer(booking).data,
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Failed to cancel booking with Amadeus"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    def _calculate_total_price(self, flights_data, num_passengers):
        """
        Calculate the total price based on Amadeus flight prices and service fee
        """
        stripe_processor = StripePaymentProcessor()

        total = Decimal('0.00')

        for flight in flights_data:
            # Assuming flight data includes the base price from Amadeus
            base_price = Decimal(str(flight.get('price', 0)))

            # Calculate total price including service fee for each flight
            total += stripe_processor.calculate_total_price(base_price)

        return total * num_passengers


    def _process_payment_with_gateway(self, booking, payment_data):
        try:
            payment_method = payment_data.get('payment_method_id')
            if not payment_method:
                return False, "Payment method ID is required"

            stripe_processor = StripePaymentProcessor()
            payment_result = stripe_processor.create_payment_intent(
                booking,
                payment_method
            )

            if 'error' in payment_result:
                return False, payment_result['error']

            payment_split = payment_result.get('payment_split', {})

            # Check if payment exists first
            payment, created = PaymentDetail.objects.update_or_create(
                booking=booking,
                defaults={
                    'amount': float(payment_split.get('total_price', booking.total_price)),
                    'currency': booking.currency,
                    'payment_method': 'STRIPE',
                    'transaction_id': payment_result.get('payment_intent_id'),
                    'payment_status': 'COMPLETED',
                    'payment_date': timezone.now(),
                    'additional_details': {
                        'flight_cost': float(payment_split.get('flight_cost', 0)),
                        'service_fee': float(payment_split.get('service_fee', 0)),
                        'payment_intent_id': payment_result.get('payment_intent_id')
                    }
                }
            )

            return True, payment_result

        except Exception as e:
            return False, str(e)


    def _create_amadeus_booking(self, booking):
        """
        Create the actual booking with Amadeus API with segment validation
        """
        flights = Flight.objects.filter(booking=booking)
        passenger_bookings = PassengerBooking.objects.filter(booking=booking).select_related('passenger')

        # 1. First validate flight segments are still available
        try:
            flight_offers = self._prepare_flight_offers(booking, flights)

            # Verify each segment in each flight offer
            for offer in flight_offers:
                for itinerary in offer.get('itineraries', []):
                    for segment in itinerary.get('segments', []):
                        if not segment.get('id'):
                            raise ValueError("Missing segment ID in flight offer")
                        if not all(segment.get(k) for k in ['departure', 'arrival', 'carrierCode', 'number']):
                            raise ValueError("Incomplete segment data")

            # 2. Prepare travelers data (same as before)
            travelers = []
            for i, pb in enumerate(passenger_bookings, 1):
                traveler = {
                    'id': str(i),
                    'dateOfBirth': pb.passenger.date_of_birth.strftime('%Y-%m-%d'),
                    'name': {
                        'firstName': pb.passenger.first_name,
                        'lastName': pb.passenger.last_name
                    },
                    'gender': 'MALE' if pb.passenger.gender == 'M' else 'FEMALE',
                    'contact': {
                        'emailAddress': pb.passenger.email,
                        'phones': [{
                            'deviceType': 'MOBILE',
                            'countryCallingCode': '1',
                            'number': ''.join(filter(str.isdigit, pb.passenger.phone))[:15] if pb.passenger.phone else '1234567890'
                        }]
                    }
                }
                if pb.passenger.passport_number:
                    traveler['documents'] = [{
                        'documentType': 'PASSPORT',
                        'number': pb.passenger.passport_number,
                        'expiryDate': pb.passenger.passport_expiry.strftime('%Y-%m-%d'),
                        'issuanceCountry': pb.passenger.nationality or 'US',
                        'nationality': pb.passenger.nationality or 'US',
                        'holder': True,
                        'birthPlace': 'UNKNOWN',
                        'issuanceLocation': 'UNKNOWN'
                    }]
                travelers.append(traveler)

            # 3. Prepare the complete payload
            amadeus_payload = {
                'data': {
                    'type': 'flight-order',
                    'flightOffers': flight_offers,
                    'travelers': travelers,
                    'remarks': {
                        'general': [{
                            'subType': 'GENERAL_MISCELLANEOUS',
                            'text': f'Booking {booking.booking_reference}'
                        }]
                    },
                    'ticketingAgreement': {
                        'option': 'DELAY_TO_CANCEL',
                        'delay': '6D'
                    },
                    'contacts': [{
                        'addresseeName': {
                            'firstName': booking.user.first_name or 'Customer',
                            'lastName': booking.user.last_name or 'Name'
                        },
                        'companyName': 'NA',
                        'purpose': 'STANDARD',
                        'phones': [{
                            'deviceType': 'MOBILE',
                            'countryCallingCode': '1',
                            'number': ''.join(filter(str.isdigit, passenger_bookings.first().passenger.phone))[:15] if passenger_bookings.exists() else '1234567890'
                        }],
                        'emailAddress': booking.user.email,
                        'address': {
                            'lines': ['123 Main Street'],
                            'postalCode': '10001',
                            'cityName': 'New York',
                            'countryCode': 'US'
                        }
                    }]
                }
            }

            # 4. Make the API call
            amadeus_client = AmadeusAPI()
            response = requests.post(
                f"{amadeus_client.base_url}/v1/booking/flight-orders",
                headers=amadeus_client._get_headers(),
                json=amadeus_payload
            )

            if response.status_code == 201:
                amadeus_data = response.json()
                booking.booking_reference = amadeus_data.get('data', {}).get('id')
                booking.save()
                self._update_ticket_numbers(booking, amadeus_data)
                return True

            # Enhanced error handling for segment errors
            error_details = response.json().get('errors', [])
            for error in error_details:
                print(f"Amadeus Error {error.get('code')}: {error.get('detail')}")
                if error.get('code') == 34651:  # Segment selling error
                    print("This flight segment may no longer be available. Please perform a new search.")

            return False

        except ValueError as e:
            print(f"Flight data validation error: {str(e)}")
            return False
        except Exception as e:
            print(f"Error creating Amadeus booking: {str(e)}")
            return False


    def _prepare_flight_offers(self, booking, flights):
        """
        Prepare flight offers data for Amadeus API
        """
        # This is a simplified version. In real implementation, you would need to
        # use the flight offers from Amadeus search API
        flight_offers = []

        # For demonstration, we'll create a simple flight offer structure
        segments = []
        for flight in flights:
            segment = {
                'departure': {
                    'iataCode': flight.departure_airport,
                    'terminal': '',
                    'at': flight.departure_datetime.strftime('%Y-%m-%dT%H:%M:%S')
                },
                'arrival': {
                    'iataCode': flight.arrival_airport,
                    'terminal': '',
                    'at': flight.arrival_datetime.strftime('%Y-%m-%dT%H:%M:%S')
                },
                'carrierCode': flight.airline_code,
                'number': flight.flight_number,
                'aircraft': {
                    'code': 'A320'  # Placeholder
                },
                'operating': {
                    'carrierCode': flight.airline_code
                },
                'duration': 'PT2H',  # Placeholder
                'id': flight.segment_id,
                'numberOfStops': 0,
                'blacklistedInEU': False
            }
            segments.append(segment)

        # Create a flight offer with segments
        offer = {
            'type': 'flight-offer',
            'id': '1',
            'source': 'GDS',
            'instantTicketingRequired': False,
            'nonHomogeneous': False,
            'oneWay': booking.booking_type == 'ONE_WAY',
            'lastTicketingDate': (timezone.now() + timezone.timedelta(days=3)).strftime('%Y-%m-%d'),
            'numberOfBookableSeats': PassengerBooking.objects.filter(booking=booking).count(),
            'itineraries': [
                {
                    'duration': 'PT2H',  # Placeholder
                    'segments': segments
                }
            ],
            'price': {
                'currency': booking.currency,
                'total': str(booking.total_price),
                'base': str(booking.total_price * Decimal('0.8')),  # Placeholder
                'fees': [
                    {
                        'amount': str(booking.total_price * Decimal('0.1')),
                        'type': 'SUPPLIER'
                    },
                    {
                        'amount': str(booking.total_price * Decimal('0.1')),
                        'type': 'TICKETING'
                    }
                ],
                'grandTotal': str(booking.total_price)
            },
            'pricingOptions': {
                'fareType': ['PUBLISHED'],
                'includedCheckedBagsOnly': True
            },
            'validatingAirlineCodes': [flights[0].airline_code],
            'travelerPricings': self._prepare_traveler_pricings(booking)
        }

        flight_offers.append(offer)
        return flight_offers

    def _prepare_traveler_pricings(self, booking):
        """
        Prepare traveler pricing data for Amadeus API
        """
        traveler_pricings = []
        passenger_bookings = PassengerBooking.objects.filter(booking=booking)

        for i, pb in enumerate(passenger_bookings, 1):
            pricing = {
                'travelerId': str(i),
                'fareOption': 'STANDARD',
                'travelerType': 'ADULT',  # Simplified - would need age calculation
                'price': {
                    'currency': booking.currency,
                    'total': str(booking.total_price / passenger_bookings.count()),
                    'base': str(booking.total_price * Decimal('0.8') / passenger_bookings.count())
                },
                'fareDetailsBySegment': [
                    {
                        'segmentId': flight.segment_id,
                        'cabin': flight.cabin_class,
                        'fareBasis': 'ABCDEF',  # Placeholder
                        'class': 'Y',  # Placeholder
                        'includedCheckedBags': {
                            'quantity': 1
                        }
                    } for flight in Flight.objects.filter(booking=booking)
                ]
            }
            traveler_pricings.append(pricing)

        return traveler_pricings

    def _prepare_travelers(self, passenger_bookings):
        """
        Prepare travelers data for Amadeus API
        """
        travelers = []

        for i, pb in enumerate(passenger_bookings, 1):
            passenger = pb.passenger

            traveler = {
                'id': str(i),
                'dateOfBirth': passenger.date_of_birth.strftime('%Y-%m-%d'),
                'name': {
                    'firstName': passenger.first_name,
                    'lastName': passenger.last_name
                },
                'gender': 'MALE' if passenger.gender == 'M' else 'FEMALE',
                'contact': {
                    'emailAddress': passenger.email,
                    'phones': [
                        {
                            'deviceType': 'MOBILE',
                            'countryCallingCode': '1',  # Assuming US code
                            'number': 'N/A'
                        }
                    ]
                }
            }

            # Add passport information if available
            if passenger.passport_number:
                traveler['documents'] = [
                    {
                        'documentType': 'PASSPORT',
                        'birthPlace': 'UNKNOWN',
                        'issuanceLocation': 'UNKNOWN',
                        'issuanceDate': '2015-04-14',  # Placeholder
                        'number': passenger.passport_number,
                        'expiryDate': passenger.passport_expiry.strftime('%Y-%m-%d'),
                        'issuanceCountry': 'US',  # Placeholder
                        'validityCountry': 'US',  # Placeholder
                        'nationality': passenger.nationality,
                        'holder': True
                    }
                ]

            travelers.append(traveler)

        return travelers

    def _update_ticket_numbers(self, booking, amadeus_data):
        """
        Update ticket numbers from Amadeus response
        """
        # Extract ticket numbers from Amadeus response
        # This is a simplified version. In real implementation, you would need to
        # parse the Amadeus response to extract ticket numbers

        # For demonstration, we'll generate random ticket numbers
        passenger_bookings = PassengerBooking.objects.filter(booking=booking)

        for pb in passenger_bookings:
            pb.ticket_number = f"TICKET-{uuid.uuid4().hex[:10].upper()}"
            pb.save()

    def _cancel_amadeus_booking(self, booking):
        """
        Cancel a booking with Amadeus API
        """
        try:
            # Initialize Amadeus client
            amadeus_client = self._get_amadeus_client()

            # Make API call to cancel booking
            response = amadeus_client.delete(
                f'/v1/booking/flight-orders/{booking.booking_reference}'
            )

            return response.status_code == 200

        except Exception as e:
            print(f"Error cancelling Amadeus booking: {str(e)}")
            return False

    def _get_amadeus_client(self):
        """
        Get Amadeus API client
        """
        from amadeus import Client

        # Initialize Amadeus client with your API key and secret
        amadeus = Client(
            client_id=settings.AMADEUS_API_TEST_KEY if settings.AMADEUS_API_TESTING else settings.AMADEUS_API_LIVE_KEY,
            client_secret=settings.AMADEUS_API_TEST_SECRET if settings.AMADEUS_API_TESTING else settings.AMADEUS_API_LIVE_SECRET,
        )

        return amadeus




class FlightSearchViewSet(viewsets.ViewSet):
    """
    ViewSet for flight search operations
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.amadeus_api = AmadeusAPI()

    @action(detail=False, methods=['post'])
    def one_way(self, request):
        """
        Search for one-way flights
        """
        serializer = FlightSearchSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Extract data from request
            origin = serializer.validated_data['origin']
            destination = serializer.validated_data['destination']
            departure_date = serializer.validated_data['departure_date']
            adults = serializer.validated_data.get('adults', 1)
            travel_class = serializer.validated_data.get('travel_class', 'ECONOMY')
            non_stop = serializer.validated_data.get('non_stop', False)
            currency = serializer.validated_data.get('currency', 'USD')

            # Filter flights in the response post-processing
            flight_offers = self.amadeus_api.search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date.strftime('%Y-%m-%d'),
                adults=adults,
                travel_class=travel_class,
                non_stop=non_stop,
                currency=currency
            )

            # Post-process flight offers to filter non-stop flights if required
            if non_stop and 'data' in flight_offers:
                flight_offers['data'] = [
                    offer for offer in flight_offers['data']
                    if len(offer.get('itineraries', [{}])[0].get('segments', [])) == 1
                ]

            # After getting flight_offers but before returning Response
            if 'data' in flight_offers:
                for offer in flight_offers['data']:
                    if 'id' in offer:
                        cache_key = f"flight_offer_{offer['id']}"
                        # Cache for a reasonable time (e.g., 1 hour)
                        cache.set(cache_key, offer, timeout=3600)

            return Response(flight_offers, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def round_trip(self, request):
        """
        Search for round-trip flights
        """
        serializer = FlightSearchSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Extract data from request
            origin = serializer.validated_data['origin']
            destination = serializer.validated_data['destination']
            departure_date = serializer.validated_data['departure_date']
            return_date = serializer.validated_data.get('return_date')

            if not return_date:
                return Response(
                    {"error": "Return date is required for round-trip flights"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            adults = serializer.validated_data.get('adults', 1)
            travel_class = serializer.validated_data.get('travel_class', 'ECONOMY')
            non_stop = serializer.validated_data.get('non_stop', False)
            currency = serializer.validated_data.get('currency', 'USD')

            # Search for flights
            flight_offers = self.amadeus_api.search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date.strftime('%Y-%m-%d'),
                return_date=return_date.strftime('%Y-%m-%d'),
                adults=adults,
                travel_class=travel_class,
                non_stop=non_stop,
                currency=currency
            )

            # After getting flight_offers but before returning Response
            if 'data' in flight_offers:
                for offer in flight_offers['data']:
                    if 'id' in offer:
                        cache_key = f"flight_offer_{offer['id']}"
                        # Cache for a reasonable time (e.g., 1 hour)
                        cache.set(cache_key, offer, timeout=3600)

            return Response(flight_offers, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def multi_city(self, request):
        """
        Search for multi-city flights
        """
        serializer = MultiCityFlightSearchSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Extract data from request
            segments = serializer.validated_data['segments']
            adults = serializer.validated_data.get('adults', 1)
            travel_class = serializer.validated_data.get('travel_class', 'ECONOMY')
            currency = serializer.validated_data.get('currency', 'USD')

            # Format segments for Amadeus API
            origin_destinations = []
            for segment in segments:
                origin_destinations.append({
                    'origin': segment['origin'],
                    'destination': segment['destination'],
                    'date': segment['departure_date'].strftime('%Y-%m-%d')
                })

            # Search for flights
            flight_offers = self.amadeus_api.search_multi_city_flights(
                origin_destinations=origin_destinations,
                adults=adults,
                travel_class=travel_class,
                currency=currency
            )

            # After getting flight_offers but before returning Response
            if 'data' in flight_offers:
                for offer in flight_offers['data']:
                    if 'id' in offer:
                        cache_key = f"flight_offer_{offer['id']}"
                        # Cache for a reasonable time (e.g., 1 hour)
                        cache.set(cache_key, offer, timeout=3600)

            return Response(flight_offers, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def price_flight_offers(self, request):
        """
        Price flight offers
        """
        try:
            # Extract flight offers from request
            flight_offers = request.data.get('flight_offers', [])

            if not flight_offers:
                return Response(
                    {"error": "No flight offers provided"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Price flight offers
            priced_offers = self.amadeus_api.price_flight_offers(flight_offers)

            return Response(priced_offers, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def search_airports(self, request):
        """
        Search for airports
        """
        keyword = request.query_params.get('keyword')

        if not keyword:
            return Response(
                {"error": "Keyword is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Search for airports
            airports = self.amadeus_api.search_airports(
                keyword=keyword,
                subType=request.query_params.get('subType', 'AIRPORT'),
                countryCode=request.query_params.get('countryCode'),
                limit=int(request.query_params.get('limit', 10))
            )

            return Response(airports, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=False, methods=['get'])
    def flight_details(self, request):
        """
        Get details of a specific flight offer
        """
        flight_id = request.query_params.get('flight_id')

        if not flight_id:
            return Response(
                {"error": "Flight ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Retrieve flight details from Amadeus API
            flight_details = self.amadeus_api.get_flight_details(flight_id)

            if not flight_details:
                return Response(
                    {"error": "Flight not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(flight_details, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle specific event types
    if event.type == 'payment_intent.succeeded':
        payment_intent = event.data.object

        # Retrieve booking reference from metadata
        booking_id = payment_intent.metadata.get('booking_id')

        if booking_id:
            try:
                with transaction.atomic():
                    # Find the booking
                    booking = FlightBooking.objects.get(id=booking_id)

                    # Update payment details
                    PaymentDetail.objects.create(
                        booking=booking,
                        amount=payment_intent.amount / 100,  # Convert cents to dollars
                        currency=payment_intent.currency.upper(),
                        payment_method='STRIPE',
                        transaction_id=payment_intent.id,
                        payment_status='COMPLETED',
                        additional_details={
                            'flight_cost': payment_intent.metadata.get('flight_cost', 0),
                            'service_fee': payment_intent.metadata.get('service_fee', 0),
                            'service_fee_percentage': payment_intent.metadata.get('service_fee_percentage', 0)
                        }
                    )

                    # Update booking status
                    booking.booking_status = 'CONFIRMED'
                    booking.save()

            except FlightBooking.DoesNotExist:
                # Log the error or handle accordingly
                pass

    elif event.type == 'payment_intent.payment_failed':
        payment_intent = event.data.object
        booking_id = payment_intent.metadata.get('booking_id')

        if booking_id:
            try:
                booking = FlightBooking.objects.get(id=booking_id)
                booking.booking_status = 'PAYMENT_FAILED'
                booking.save()
            except FlightBooking.DoesNotExist:
                pass

    return HttpResponse(status=200)

import json
from django.conf import settings
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import permission_classes
from rest_framework.decorators import action
from django.core.cache import cache
from django.db import transaction
from django.utils.dateparse import parse_duration
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from .flight_schema import flight_booking_schema, flight_search_schema
from drf_spectacular.utils import extend_schema_view, extend_schema
import uuid
import requests
from .models import FlightBooking, Flight, Passenger, PassengerBooking, PaymentDetail, ServiceFeeSetting
from core.applications.stay.models import Booking  # Import the base Booking model
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
        # Convert percentage to decimal (e.g., 5% -> 0.05)
        self.service_rate_percentage = Decimal(str(ServiceFeeSetting.get_current_fee())) / Decimal('100')

        stripe.api_key = (
            settings.STRIPE_SECRET_TEST_KEY
            if settings.AMADEUS_API_TESTING
            else settings.STRIPE_LIVE_SECRET_KEY
        )

    def calculate_total_price(self, amadeus_price):
        """Calculate total price including service fee"""
        service_fee = amadeus_price * self.service_rate_percentage
        return amadeus_price + service_fee

    def split_payment(self, total_amount):
        """
        Split payment between service fee and flight cost
        This ensures the service fee is always calculated from the base flight cost
        """
        # Calculate what the base flight cost would be without service fee
        base_flight_cost = total_amount / (1 + self.service_rate_percentage)
        service_fee = total_amount - base_flight_cost

        return {
            'total_price': float(total_amount),
            'flight_cost': float(base_flight_cost),
            'service_fee': float(service_fee),
            'service_fee_percentage': float(self.service_rate_percentage * 100)
        }

    def create_payment_intent(self, flight_booking, payment_method):
        try:
            total_price = self.calculate_total_price(flight_booking.base_flight_cost)
            payment_split = self.split_payment(total_price)

            payment_intent = stripe.PaymentIntent.create(
                amount=int(total_price * 100),  # Convert to cents
                currency=flight_booking.currency.lower(),
                payment_method=payment_method,
                confirm=True,
                automatic_payment_methods={
                    "enabled": True,
                    "allow_redirects": "never"  # Disable redirect-based payment methods
                },
                metadata={
                    'flight_booking_id': flight_booking.id,
                    'booking_id': flight_booking.booking.id,
                    'base_flight_cost': float(flight_booking.base_flight_cost),
                    'service_fee': payment_split['service_fee'],
                    'service_fee_percentage': payment_split['service_fee_percentage']
                }
            )

            return {
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'payment_split': payment_split
            }
        except stripe.error.StripeError as e:
            return {'error': str(e)}


@flight_booking_schema
class FlightBookingViewSet(viewsets.ModelViewSet):
    queryset = FlightBooking.objects.all()
    serializer_class = FlightBookingSerializer

    def get_queryset(self):
        """
        Filter bookings to return only those belonging to the current user
        """
        return FlightBooking.objects.filter(booking__user=self.request.user)

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

        # First create the base Booking
        base_booking = Booking.objects.create(
            user=request.user,
            status='PENDING',
            total_price=total_price_with_service,
        )

        # Create the FlightBooking that refers to the base Booking
        flight_booking = FlightBooking.objects.create(
            booking=base_booking,
            booking_reference=uuid.uuid4().hex[:10].upper(),
            booking_type=booking_type,
            base_flight_cost=base_price,
            service_fee=service_fee,
            currency='USD',  # Default currency, should ideally come from flight offer
        )

        # Create flight records from the cached flight offers
        for flight_offer in flight_offers:
            for itinerary_idx, itinerary in enumerate(flight_offer.get('itineraries', [])):
                for segment in itinerary.get('segments', []):
                    # Get fare details from traveler pricing
                    fare_details = {}
                    if flight_offer.get('travelerPricings'):
                        traveler_pricing = flight_offer['travelerPricings'][0]
                        for fare_segment in traveler_pricing.get('fareDetailsBySegment', []):
                            if fare_segment.get('segmentId') == segment.get('id'):
                                fare_details = fare_segment
                                break

                    # Create flight instance with all details
                    Flight.objects.create(
                        flight_booking=flight_booking,
                        itinerary_index=itinerary_idx,
                        flight_number=segment.get('number'),
                        airline_code=segment.get('carrierCode'),
                        operating_airline=segment.get('operating', {}).get('carrierCode'),
                        departure_airport=segment.get('departure', {}).get('iataCode'),
                        departure_terminal=segment.get('departure', {}).get('terminal', ''),
                        departure_city=segment.get('departure', {}).get('city', ''),
                        departure_datetime=datetime.strptime(
                            segment.get('departure', {}).get('at'),
                            '%Y-%m-%dT%H:%M:%S'
                        ),
                        arrival_airport=segment.get('arrival', {}).get('iataCode'),
                        arrival_terminal=segment.get('arrival', {}).get('terminal', ''),
                        arrival_city=segment.get('arrival', {}).get('city', ''),
                        arrival_datetime=datetime.strptime(
                            segment.get('arrival', {}).get('at'),
                            '%Y-%m-%dT%H:%M:%S'
                        ),
                        aircraft_code=segment.get('aircraft', {}).get('code'),
                        segment_id=segment.get('id'),
                        number_of_stops=segment.get('numberOfStops', 0),
                        duration=parse_duration(segment.get('duration', 'PT0H0M')),
                        cabin_class=fare_details.get('cabin', 'ECONOMY'),
                        fare_basis=fare_details.get('fareBasis', ''),
                        fare_class=fare_details.get('class', ''),
                        fare_brand=fare_details.get('brandedFare', ''),
                        fare_brand_label=fare_details.get('brandedFareLabel', ''),
                        included_checked_bags=fare_details.get('includedCheckedBags', {}).get('quantity', 0),
                        blacklisted_in_eu=segment.get('blacklistedInEU', False)
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
                flight_booking=flight_booking,  # Updated field name
                passenger=passenger
            )

        # Return the booking data
        return Response(
            FlightBookingSerializer(flight_booking).data,
            status=status.HTTP_201_CREATED
        )


    @action(detail=True, methods=['post'])
    @transaction.atomic
    def process_payment(self, request, pk=None):
        """
        Process payment for a booking
        """
        flight_booking = self.get_object()

        if flight_booking.booking.status != 'PENDING':
            return Response(
                {"error": "This booking is not in a pending state and cannot be paid for."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PaymentInputSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Process payment with Stripe
        payment_successful, payment_result = self._process_payment_with_gateway(
            flight_booking,
            serializer.validated_data
        )

        if payment_successful:
            # Create Amadeus booking
            amadeus_booking_successful = self._create_amadeus_booking(flight_booking)

            if amadeus_booking_successful:
                flight_booking.booking.status = 'COMPLETED'
                flight_booking.booking.save()
                return Response(
                    {
                        'booking': FlightBookingSerializer(flight_booking).data,
                        'payment_details': payment_result
                    },
                    status=status.HTTP_200_OK
                )
            else:
                # Refund the payment if Amadeus booking fails
                stripe.Refund.create(
                    payment_intent=payment_result['payment_intent_id']
                )

                flight_booking.booking.status = 'PENDING'
                flight_booking.booking.save()

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
        flight_booking = self.get_object()

        if flight_booking.booking.status == 'CANCELLED':
            return Response(
                {"error": "This booking is already cancelled"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Here you would call Amadeus API to cancel the booking
        amadeus_cancellation_successful = self._cancel_amadeus_booking(flight_booking)

        if amadeus_cancellation_successful:
            flight_booking.booking.status = 'CANCELLED'
            flight_booking.booking.save()

            return Response(
                FlightBookingSerializer(flight_booking).data,
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


    def _process_payment_with_gateway(self, flight_booking, payment_data):
        try:
            payment_method = payment_data.get('payment_method_id')
            if not payment_method:
                return False, "Payment method ID is required"

            stripe_processor = StripePaymentProcessor()
            payment_result = stripe_processor.create_payment_intent(
                flight_booking,
                payment_method
            )

            if 'error' in payment_result:
                return False, payment_result['error']

            payment_split = payment_result.get('payment_split', {})

            # Check if payment exists first
            payment, created = PaymentDetail.objects.update_or_create(
                booking=flight_booking.booking,  # Reference the base booking model
                defaults={
                    'amount': float(payment_split.get('total_price', flight_booking.booking.total_price)),
                    'currency': flight_booking.currency,
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


    def _create_amadeus_booking(self, flight_booking):
        """
        Create the actual booking with Amadeus API with segment validation
        """
        flights = Flight.objects.filter(flight_booking=flight_booking)
        passenger_bookings = PassengerBooking.objects.filter(flight_booking=flight_booking).select_related('passenger')

        try:
            # Try to get the original flight offers from cache
            flight_offers = []
            for flight in flights:
                # Try to find the original offer using the segment ID
                cache_key = f"flight_offer_by_segment_{flight.segment_id}"
                cached_offer = cache.get(cache_key)

                if cached_offer:
                    flight_offers.append(cached_offer)
                    continue

                # Fallback to searching by flight details if segment-based cache fails
                for offer_id in self._find_offer_ids_for_flight(flight):
                    cache_key = f"flight_offer_{offer_id}"
                    cached_offer = cache.get(cache_key)
                    if cached_offer:
                        flight_offers.append(cached_offer)
                        # Cache the offer by segment ID for future reference
                        cache.set(f"flight_offer_by_segment_{flight.segment_id}", cached_offer, timeout=3600)
                        break

            # If no offers found in cache, use reconstructed offers but with proper pricing
            if not flight_offers:
                print("No cached flight offers found, using reconstructed data")
                flight_offers = self._prepare_flight_offers(flight_booking, flights)
            else:
                # Ensure we're using the base price without service fee
                for offer in flight_offers:
                    if 'price' in offer:
                        offer['price']['total'] = str(flight_booking.base_flight_cost)
                        offer['price']['grandTotal'] = str(flight_booking.base_flight_cost)

            # Rest of the method remains the same...
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

            # Prepare the complete payload
            amadeus_payload = {
                'data': {
                    'type': 'flight-order',
                    'flightOffers': flight_offers,
                    'travelers': travelers,
                    'remarks': {
                        'general': [{
                            'subType': 'GENERAL_MISCELLANEOUS',
                            'text': f'Booking {flight_booking.booking_reference}'
                        }]
                    },
                    'ticketingAgreement': {
                        'option': 'DELAY_TO_CANCEL',
                        'delay': '6D'
                    },
                    'contacts': [{
                        'addresseeName': {
                            'firstName': flight_booking.booking.user.first_name or 'Customer',
                            'lastName': flight_booking.booking.user.last_name or 'Name'
                        },
                        'companyName': 'NA',
                        'purpose': 'STANDARD',
                        'phones': [{
                            'deviceType': 'MOBILE',
                            'countryCallingCode': '1',
                            'number': ''.join(filter(str.isdigit, passenger_bookings.first().passenger.phone))[:15] if passenger_bookings.exists() else '1234567890'
                        }],
                        'emailAddress': flight_booking.booking.user.email,
                        'address': {
                            'lines': [passenger_bookings.first().passenger.address_line1] if hasattr(passenger_bookings.first().passenger, 'address_line1') else ['123 Main Street'],
                            'postalCode': passenger_bookings.first().passenger.postal_code if hasattr(passenger_bookings.first().passenger, 'postal_code') else '10001',
                            'cityName': passenger_bookings.first().passenger.city if hasattr(passenger_bookings.first().passenger, 'city') else 'New York',
                            'countryCode': passenger_bookings.first().passenger.country_code if hasattr(passenger_bookings.first().passenger, 'country_code') else 'US'
                        }
                    }]
                }
            }

            # Log the payload for debugging
            print(f"Amadeus booking payload: {json.dumps(amadeus_payload, indent=2)}")

            # Make the API call
            amadeus_client = AmadeusAPI()
            response = requests.post(
                f"{amadeus_client.base_url}/v1/booking/flight-orders",
                headers=amadeus_client._get_headers(),
                json=amadeus_payload
            )

            # Log the full response for debugging
            print(f"Amadeus API response status: {response.status_code}")
            print(f"Amadeus API response body: {response.text}")

            if response.status_code == 201:
                amadeus_data = response.json()
                flight_booking.booking_reference = amadeus_data.get('data', {}).get('id')
                flight_booking.save()
                self._update_ticket_numbers(flight_booking, amadeus_data)
                return True

            # Handle errors
            error_details = response.json().get('errors', [])
            for error in error_details:
                error_code = error.get('code')
                error_detail = error.get('detail')
                print(f"Amadeus Error {error_code}: {error_detail}")

            return False

        except Exception as e:
            print(f"Error creating Amadeus booking: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _prepare_flight_offers(self, flight_booking, flights):
        """
        Prepare flight offers data for Amadeus API when cached data isn't available
        Handles multi-city flights and preserves all necessary flight details
        """
        flight_offers = []

        # Group segments by itinerary (for multi-city support)
        segments_by_itinerary = {}
        for flight in flights:
            # Use the itinerary_index stored in Flight model for multi-city
            itinerary_key = getattr(flight, 'itinerary_index', 0)
            if itinerary_key not in segments_by_itinerary:
                segments_by_itinerary[itinerary_key] = []

            segment = {
                'departure': {
                    'iataCode': flight.departure_airport,
                    'terminal': flight.departure_terminal or '',
                    'at': flight.departure_datetime.strftime('%Y-%m-%dT%H:%M:%S')
                },
                'arrival': {
                    'iataCode': flight.arrival_airport,
                    'terminal': flight.arrival_terminal or '',
                    'at': flight.arrival_datetime.strftime('%Y-%m-%dT%H:%M:%S')
                },
                'carrierCode': flight.airline_code,
                'number': flight.flight_number,
                'aircraft': {
                    'code': flight.aircraft_code or 'UNKNOWN'
                },
                'operating': {
                    'carrierCode': flight.operating_airline or flight.airline_code
                },
                'duration': self._calculate_segment_duration(flight.departure_datetime, flight.arrival_datetime),
                'id': flight.segment_id,
                'numberOfStops': flight.number_of_stops or 0,
                'blacklistedInEU': False,
                # Include fare details if available
                'fareBasis': flight.fare_basis or '',
                'class': flight.fare_class or 'Y',
                'brandedFare': flight.fare_brand or '',
                'brandedFareLabel': flight.fare_brand_label or ''
            }
            segments_by_itinerary[itinerary_key].append(segment)

        # Create flight offers with proper pricing and structure
        for itinerary_idx, segments in sorted(segments_by_itinerary.items()):
            # Calculate pricing per passenger
            num_passengers = PassengerBooking.objects.filter(flight_booking=flight_booking).count()
            base_price_per_passenger = flight_booking.base_flight_cost / num_passengers if num_passengers > 0 else Decimal('0.00')

            offer = {
                'type': 'flight-offer',
                'id': str(flight_booking.id) + f'_{itinerary_idx}',
                'source': 'GDS',
                'instantTicketingRequired': False,
                'nonHomogeneous': False,
                'oneWay': flight_booking.booking_type == 'ONE_WAY',
                'lastTicketingDate': (timezone.now() + timezone.timedelta(days=3)).strftime('%Y-%m-%d'),
                'numberOfBookableSeats': num_passengers,
                'itineraries': [{
                    'duration': self._calculate_itinerary_duration(segments),
                    'segments': segments
                }],
                'price': {
                    'currency': flight_booking.currency,
                    'total': str(base_price_per_passenger),  # Per passenger price
                    'base': str(base_price_per_passenger * Decimal('0.8')),  # 80% of total as base
                    'fees': [
                        {
                            'amount': '0.00',
                            'type': 'SUPPLIER'
                        },
                        {
                            'amount': '0.00',
                            'type': 'TICKETING'
                        }
                    ],
                    'grandTotal': str(base_price_per_passenger),
                    'additionalServices': self._get_additional_services(flight_booking)
                },
                'pricingOptions': {
                    'fareType': ['PUBLISHED'],
                    'includedCheckedBagsOnly': False
                },
                'validatingAirlineCodes': [segments[0]['carrierCode']] if segments else [],
                'travelerPricings': self._prepare_traveler_pricings(flight_booking, segments)
            }
            flight_offers.append(offer)

        return flight_offers

    def _prepare_traveler_pricings(self, flight_booking, segments=None):
        """
        Prepare traveler pricing with proper fare details from segments
        """
        traveler_pricings = []
        passenger_bookings = PassengerBooking.objects.filter(flight_booking=flight_booking)

        for i, pb in enumerate(passenger_bookings, 1):
            fare_details = []
            if segments:
                for segment in segments:
                    fare_details.append({
                        'segmentId': segment.get('id'),
                        'cabin': segment.get('cabin', 'ECONOMY'),
                        'fareBasis': segment.get('fareBasis', ''),
                        'class': segment.get('class', 'Y'),
                        'brandedFare': segment.get('brandedFare', ''),
                        'brandedFareLabel': segment.get('brandedFareLabel', ''),
                        'includedCheckedBags': {
                            'quantity': segment.get('included_checked_bags', 0)
                        }
                    })

            pricing = {
                'travelerId': str(i),
                'fareOption': 'STANDARD',
                'travelerType': 'ADULT',
                'price': {
                    'currency': flight_booking.currency,
                    'total': str(flight_booking.base_flight_cost / passenger_bookings.count()),
                    'base': str(flight_booking.base_flight_cost * Decimal('0.8') / passenger_bookings.count())
                },
                'fareDetailsBySegment': fare_details if fare_details else [
                    {
                        'segmentId': segment.get('id'),
                        'cabin': 'ECONOMY',
                        'fareBasis': 'STANDARD',
                        'class': 'Y',
                        'includedCheckedBags': {
                            'quantity': 0
                        }
                    } for segment in (segments or [])
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

    def _calculate_segment_duration(self, departure, arrival):
        """Calculate ISO 8601 duration string for a flight segment"""
        delta = arrival - departure
        hours, remainder = divmod(delta.total_seconds(), 3600)
        minutes = remainder // 60
        return f"PT{int(hours)}H{int(minutes)}M"

    def _calculate_itinerary_duration(self, segments):
        """Calculate total duration for an itinerary"""
        if not segments:
            return "PT0H0M"

        first_segment = segments[0]
        last_segment = segments[-1]

        departure = datetime.strptime(first_segment['departure']['at'], '%Y-%m-%dT%H:%M:%S')
        arrival = datetime.strptime(last_segment['arrival']['at'], '%Y-%m-%dT%H:%M:%S')

        return self._calculate_segment_duration(departure, arrival)

    def _update_ticket_numbers(self, flight_booking, amadeus_data):
        """
        Update ticket numbers from Amadeus response
        """
        # Extract ticket numbers from Amadeus response
        # This is a simplified version. In real implementation, you would need to
        # parse the Amadeus response to extract ticket numbers

        # For demonstration, we'll generate random ticket numbers
        passenger_bookings = PassengerBooking.objects.filter(flight_booking=flight_booking)  # Updated field name

        for pb in passenger_bookings:
            pb.ticket_number = f"TICKET-{uuid.uuid4().hex[:10].upper()}"
            pb.save()

    def _cancel_amadeus_booking(self, flight_booking):
        """
        Cancel a booking with Amadeus API
        """
        try:
            # Initialize Amadeus client
            amadeus_client = self._get_amadeus_client()

            # Make API call to cancel booking
            response = amadeus_client.delete(
                f'/v1/booking/flight-orders/{flight_booking.booking_reference}'
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




@flight_search_schema
class FlightSearchViewSet(viewsets.ViewSet):
    """
    ViewSet for flight search operations
    """

    permission_classes = [permissions.AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.amadeus_api = AmadeusAPI()

    def _validate_date_not_in_past(self, date):
        """
        Helper method to validate that a date is not in the past
        """
        today = datetime.now().date()
        if date < today:
            return False
        return True

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

            # Validate departure date is not in the past
            if not self._validate_date_not_in_past(departure_date):
                return Response(
                    {"error": "Departure date cannot be in the past"},
                    status=status.HTTP_400_BAD_REQUEST
                )

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
                        # Cache by offer ID
                        cache_key = f"flight_offer_{offer['id']}"
                        cache.set(cache_key, offer, timeout=3600)

                        # Also cache by segment IDs for easier lookup later
                        for itinerary in offer.get('itineraries', []):
                            for segment in itinerary.get('segments', []):
                                if 'id' in segment:
                                    segment_cache_key = f"flight_offer_by_segment_{segment['id']}"
                                    cache.set(segment_cache_key, offer, timeout=3600)

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

            # Validate departure date is not in the past
            if not self._validate_date_not_in_past(departure_date):
                return Response(
                    {"error": "Departure date cannot be in the past"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate return date is not before departure date
            if return_date < departure_date:
                return Response(
                    {"error": "Return date cannot be before departure date"},
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
                        # Cache by offer ID
                        cache_key = f"flight_offer_{offer['id']}"
                        cache.set(cache_key, offer, timeout=3600)

                        # Also cache by segment IDs for easier lookup later
                        for itinerary in offer.get('itineraries', []):
                            for segment in itinerary.get('segments', []):
                                if 'id' in segment:
                                    segment_cache_key = f"flight_offer_by_segment_{segment['id']}"
                                    cache.set(segment_cache_key, offer, timeout=3600)

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

            # Validate all departure dates
            today = datetime.now().date()
            for i, segment in enumerate(segments):
                if segment['departure_date'] < today:
                    return Response(
                        {"error": f"Departure date for segment {i+1} cannot be in the past"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

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
                        # Cache by offer ID
                        cache_key = f"flight_offer_{offer['id']}"
                        cache.set(cache_key, offer, timeout=3600)

                        # Also cache by segment IDs for easier lookup later
                        for itinerary in offer.get('itineraries', []):
                            for segment in itinerary.get('segments', []):
                                if 'id' in segment:
                                    segment_cache_key = f"flight_offer_by_segment_{segment['id']}"
                                    cache.set(segment_cache_key, offer, timeout=3600)

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




# class FlightAdminViewSet(viewsets.ViewSet):
#     """
#     Admin-only operations for flight bookings
#     """
#     permission_classes = [IsAdminUser]

#     def retrieve(self, request, pk=None):
#         """
#         Get detailed booking information including user and flight details
#         """
#         try:
#             flight_booking = FlightBooking.objects.get(pk=pk)

#             # Get all related data
#             booking_data = FlightBookingSerializer(flight_booking).data

#             # Add user details
#             user = flight_booking.booking.user
#             user_data = {
#                 'user': {
#                     'first_name': user.first_name,
#                     'last_name': user.last_name,
#                     'email': user.email,
#                     'phone_number': user.phone_number if hasattr(user, 'phone_number') else None,
#                     'address': user.address if hasattr(user, 'address') else None,
#                 }
#             }

#             # Add flight details
#             flights = Flight.objects.filter(flight_booking=flight_booking)
#             flight_data = {
#                 'flights': [
#                     {
#                         'id': flight.id,
#                         'departure_airport': flight.departure_airport,
#                         'arrival_airport': flight.arrival_airport,
#                         'departure_datetime': flight.departure_datetime,
#                         'arrival_datetime': flight.arrival_datetime,
#                         'airline_code': flight.airline_code,
#                         'flight_number': flight.flight_number,
#                         'cabin_class': flight.cabin_class,
#                         'segment_id': flight.segment_id
#                     } for flight in flights
#                 ]
#             }

#             # Add passenger details
#             passenger_bookings = PassengerBooking.objects.filter(flight_booking=flight_booking)
#             passenger_data = {
#                 'passengers': [
#                     {
#                         'first_name': pb.passenger.first_name,
#                         'last_name': pb.passenger.last_name,
#                         'email': pb.passenger.email,
#                         'phone': pb.passenger.phone,
#                         'passport_number': pb.passenger.passport_number,
#                         'passport_expiry': pb.passenger.passport_expiry,
#                         'nationality': pb.passenger.nationality,
#                         'ticket_number': pb.ticket_number
#                     } for pb in passenger_bookings
#                 ]
#             }

#             # Combine all data
#             response_data = {
#                 **booking_data,
#                 **user_data,
#                 **flight_data,
#                 **passenger_data
#             }

#             return Response(response_data, status=status.HTTP_200_OK)

#         except FlightBooking.DoesNotExist:
#             return Response(
#                 {"error": "Booking not found"},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#     @action(detail=True, methods=['patch'])
#     def update_flight(self, request, pk=None):
#         """
#         Update flight information (admin only)
#         """
#         try:
#             flight_booking = FlightBooking.objects.get(pk=pk)
#             flight_id = request.data.get('flight_id')

#             if not flight_id:
#                 return Response(
#                     {"error": "flight_id is required in request data"},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )

#             try:
#                 flight = Flight.objects.get(id=flight_id, flight_booking=flight_booking)
#             except Flight.DoesNotExist:
#                 return Response(
#                     {"error": "Flight not found for this booking"},
#                     status=status.HTTP_404_NOT_FOUND
#                 )

#             # Only allow updating certain fields
#             allowed_fields = ['departure_datetime', 'arrival_datetime', 'flight_number']
#             update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

#             if not update_data:
#                 return Response(
#                     {"error": "No valid fields provided for update"},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )

#             # Update the flight
#             for field, value in update_data.items():
#                 setattr(flight, field, value)
#             flight.save()

#             return Response(
#                 {"message": "Flight updated successfully"},
#                 status=status.HTTP_200_OK
#             )

#         except FlightBooking.DoesNotExist:
#             return Response(
#                 {"error": "Booking not found"},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#     @action(detail=True, methods=['post'])
#     def admin_cancel(self, request, pk=None):
#         """
#         Admin cancellation of a booking with optional refund
#         """
#         try:
#             flight_booking = FlightBooking.objects.get(pk=pk)

#             if flight_booking.booking.status == 'CANCELLED':
#                 return Response(
#                     {"error": "Booking is already cancelled"},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )

#             # Check if refund should be processed
#             process_refund = request.data.get('process_refund', False)
#             refund_amount = request.data.get('refund_amount')  # Optional partial refund

#             # Call the existing cancellation logic
#             view = FlightBookingViewSet()
#             view.request = request
#             view.format_kwarg = {}

#             response = view.cancel_booking(request, pk=pk)

#             if response.status_code == 200:
#                 # Add admin-specific cancellation notes
#                 cancellation_reason = request.data.get('reason', 'Admin cancellation')
#                 flight_booking.admin_notes = cancellation_reason
#                 flight_booking.save()

#                 # Process refund if requested
#                 if process_refund:
#                     refund_result = self._process_refund(
#                         flight_booking,
#                         refund_amount=refund_amount,
#                         reason=cancellation_reason
#                     )

#                     if 'error' in refund_result:
#                         return Response(
#                             {"message": "Booking cancelled but refund failed", "refund_error": refund_result['error']},
#                             status=status.HTTP_207_MULTI_STATUS
#                         )

#                     return Response(
#                         {"message": "Booking cancelled and refund processed", "refund_details": refund_result},
#                         status=status.HTTP_200_OK
#                     )

#                 return Response(
#                     {"message": "Booking cancelled successfully (no refund processed)"},
#                     status=status.HTTP_200_OK
#                 )
#             else:
#                 return response

#         except FlightBooking.DoesNotExist:
#             return Response(
#                 {"error": "Booking not found"},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#     def _process_refund(self, flight_booking, refund_amount=None, reason=None):
#         """
#         Process refund through Stripe
#         """
#         try:
#             # Get the payment details
#             payment = PaymentDetail.objects.filter(
#                 booking=flight_booking.booking,
#                 payment_status='COMPLETED'
#             ).first()

#             if not payment:
#                 return {'error': 'No completed payment found for this booking'}

#             stripe.api_key = (
#                 settings.STRIPE_SECRET_TEST_KEY
#                 if settings.AMADEUS_API_TESTING
#                 else settings.STRIPE_LIVE_SECRET_KEY
#             )

#             # Calculate refund amount (full or partial)
#             amount_to_refund = refund_amount or payment.amount * 100  # Convert to cents

#             # Create refund
#             refund = stripe.Refund.create(
#                 payment_intent=payment.transaction_id,
#                 amount=int(amount_to_refund),
#                 reason='requested_by_customer' if not reason else 'other',
#                 metadata={
#                     'admin_refund': 'true',
#                     'booking_id': flight_booking.booking.id,
#                     'reason': reason or 'Admin-initiated refund'
#                 }
#             )

#             # Update payment record
#             payment.refund_amount = (refund_amount or payment.amount)
#             payment.refund_date = timezone.now()
#             payment.payment_status = 'REFUNDED' if refund_amount == payment.amount else 'PARTIALLY_REFUNDED'
#             payment.additional_details['refund_id'] = refund.id
#             payment.save()

#             return {
#                 'refund_id': refund.id,
#                 'amount_refunded': refund.amount / 100,
#                 'currency': refund.currency,
#                 'status': refund.status
#             }

#         except stripe.error.StripeError as e:
#             return {'error': str(e), 'type': type(e).__name__}
#         except Exception as e:
#             return {'error': str(e)}



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
        booking_id = payment_intent.metadata.get('booking_id')

        if booking_id:
            try:
                with transaction.atomic():
                    booking = Booking.objects.get(id=booking_id)
                    booking.status = 'COMPLETED'
                    booking.save()

                    # Create payment record
                    PaymentDetail.objects.create(
                        booking=booking,
                        amount=payment_intent.amount / 100,
                        currency=payment_intent.currency,
                        payment_method='STRIPE',
                        transaction_id=payment_intent.id,
                        payment_status='COMPLETED',
                        metadata=payment_intent.metadata
                    )
            except Booking.DoesNotExist:
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

import json
from core.amadeus import amadeus_client
from core.helpers.enums import GenderChoice
from rest_framework import  status
from rest_framework.viewsets import ViewSet

from core.amadeus.amadeus_services import  book_hotel_room, list_or_fetch_hotels_by_city, search_hotels
from rest_framework.response import Response
from core.applications.stay.api.schemas import (
    search_hotel_schema, detail_schema, check_availability_schema,
    room_per_hotel_schema, book_hotel_schema, city_search_schema,
    list_hotel_schema
)
from datetime import datetime, timedelta

from amadeus import ResponseError, Location
import logging
from core.helpers.authentication import CustomJWTAuthentication
from djoser.conf import settings as djoser_settings
from django.conf import settings as django_settings
from rest_framework.decorators import action
from django.http import JsonResponse


logger = logging.getLogger(__name__)


class HotelApiViewSet(ViewSet):
    """
    ViewSet for fetching hotel information
    and availability from Amadeus API.
    """
    authentication_class = [CustomJWTAuthentication]
    permission_classes = djoser_settings.PERMISSIONS.user

    @list_hotel_schema
    def list(self, request):
        """Fetch hotels based on city code."""
        city_code = request.query_params.get("city_code")
        if not city_code:
            return Response(
                {"error": "City code is required"},
                status=400
            )

        hotels = list_or_fetch_hotels_by_city(city_code)
        return Response(
            hotels,
            status=200 if isinstance(hotels, list) else 500
        )


    @search_hotel_schema
    @action(detail=False, methods=["get"], url_path="search")
    def search_hotels(self, request):
        """Search for hotels based on hotelIds and filters."""
        hotel_ids = request.query_params.getlist("hotelIds")
        if not hotel_ids:
            return Response({"error": "hotelIds is required"}, status=400)

        check_in = request.query_params.get(
            "checkInDate",
            datetime.today().strftime("%Y-%m-%d")
        )
        check_out = request.query_params.get(
            "checkOutDate",
            (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        )
        adults = request.query_params.get("adults", "1")
        room_quantity = request.query_params.get("roomQuantity", "1")
        country_of_residence = request.query_params.get("countryOfResidence", None)
        price_range = request.query_params.get("priceRange", None)

        response = search_hotels(
            hotel_ids, check_in, check_out, adults, room_quantity,
            country_of_residence, price_range
        )
        return Response(response, status=200 if isinstance(response, list) else 400)


    @detail_schema
    @action(detail=False, methods=["get"], url_path="details")
    def get_hotel_details(self, request):
        """
        Retrieve details of a specific hotel using its hotelId.
        """
        hotel_id = request.query_params.get("hotel_id")
        if not hotel_id:
            return Response({"error": "hotel_id is required"}, status=400)

        try:
            response = amadeus_client.reference_data.locations.hotels.by_hotels.get(hotelIds=hotel_id)
            return Response(response.data)
        except ResponseError as amadeus_error:
            logger.error(f"Amadeus API Error: {amadeus_error}")
            return Response({"error": str(amadeus_error)}, status=400)
        except Exception as e:
            logger.error(f"Error in get_hotel_details: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=500)



    # @check_availability_schema
    # @action(detail=True, methods=["get"])
    # def check_availability(self, request, pk=None):
    #     """Check availability for a specific hotel."""
    #     if not pk:
    #         return Response({"error": "Hotel ID is required"}, status=400)

    #     try:
    #         response = amadeus_client.shopping.hotel_offers_search.get(hotelIds=pk)
    #         offers = response.data
    #         return Response(offers)
    #     except Exception as e:
    #         return Response({"error": str(e)}, status=500)

    @room_per_hotel_schema
    @action(detail=False, methods=["get"], url_path="rooms")
    def rooms_per_hotel(self, request):
        """
        Retrieve available rooms for a specific hotel with pricing transparency.
        """
        hotel_id = request.query_params.get("hotel_id")
        check_in = request.query_params.get("check_in")
        check_out = request.query_params.get("check_out")

        if not all([hotel_id, check_in, check_out]):
            return Response(
                {"error": "Hotel ID, check-in, and check-out dates are required"},
                status=400
            )

        # Validate date format
        try:
            check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        # Ensure check-in is in the future
        today = datetime.today().date()
        if check_in_date < today:
            return Response({"error": "Check-in date cannot be in the past."}, status=400)

        # Ensure check-out is after check-in
        if check_out_date <= check_in_date:
            return Response({"error": "Check-out date must be after check-in date."}, status=400)

        try:
            response = amadeus_client.shopping.hotel_offers_search.get(
                hotelIds=hotel_id, checkInDate=str(check_in_date), checkOutDate=str(check_out_date)
            ).data

            return Response(response)
        except (TypeError, AttributeError, ResponseError, KeyError) as e:
            return Response({"error": str(e)}, status=500)


    @book_hotel_schema
    # @action(detail=False, methods=["post"], url_path="book")
    # def book_hotel_room(self, request):
    #     """Book a hotel room using Amadeus API."""
    #     offerId = request.data.get("offerId")
    #     user = request.user

    #     if not offerId:
    #         return Response({"error": "Offer ID is required"}, status=400)

    #     profile = getattr(user, "profile", None)
    #     if not profile or not profile.first_name or not profile.last_name or not profile.mobile_number:
    #         return Response({"error": "Incomplete profile. Update first name, last name, and mobile number."}, status=400)

    #     try:
    #         # Step 1: Confirm offer availability
    #         logger.info(f"Fetching offer availability for offerId: {offerId}")
    #         offer_availability = amadeus_client.shopping.hotel_offer_search(offerId).get()

    #         if offer_availability.status_code != 200:
    #             logger.error(f"Offer availability failed: {offer_availability.result}")
    #             return Response({"error": f"Room not available. Response: {offer_availability.result}"}, status=400)

    #         # Step 2: Proceed with booking
    #         guests = [{
    #             "id": 1,
    #             "title": "MR" if profile.gender == "MALE" else "MS",
    #             "firstName": profile.first_name,
    #             "lastName": profile.last_name,
    #             "contact": {
    #                 "phone": profile.mobile_number,
    #                 "email": user.email
    #             }
    #         }]

    #         travel_agent = {"contact": {"email": "support@yourcompany.com"}}
    #         room_associations = [{"guestReferences": [{"id": "1"}], "offerId": offerId}]

    #         payment = {
    #             "method": "creditCard",
    #             "paymentCard": {
    #                 "vendorCode": "VI",
    #                 "cardNumber": "4151289722471370",
    #                 "expiryDate": "2030-08",
    #                 "cardHolderName": f"{profile.first_name} {profile.last_name}"
    #             }
    #         }

    #         logger.info(f"Booking request payload: {guests}, {room_associations}, {payment}")

    #         booking_response = amadeus_client.booking.hotel_orders.post(
    #             guests=guests,
    #             travel_agent=travel_agent,
    #             room_associations=room_associations,
    #             payment=payment
    #         )

    #         logger.info(f"Booking API response: {booking_response.result}")

    #         return Response({
    #             "pnr": booking_response['associatedRecords'][0]['reference'],
    #             "status": booking_response['hotelBookings'][0]['bookingStatus'],
    #             "providerConfirmationId": booking_response['hotelBookings'][0]['hotelProviderInformation'][0]['confirmationNumber']
    #         })

    #     except ResponseError as e:
    #         logger.error(f"Booking error: {e.code} - {e.description} - {e.response.body}", exc_info=True)
    #         return Response({"error": f"Amadeus API Error: {e.code} - {e.description} - {e.response.body}"}, status=400)


    @action(detail=False, methods=["post"], url_path="book")
    def book_room(self, request):
        """
        Book a hotel room using Amadeus API
        """
        try:
            user = request.user

            # Extract data from request
            offer_id = request.data.get("offerId")
            guests = request.data.get("guests", [])
            payment = request.data.get("payment")

            # Validate required fields
            if not offer_id:
                return Response({"error": "offerId is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not guests:
                return Response({"error": "At least one guest is required"}, status=status.HTTP_400_BAD_REQUEST)

            # Process guests with correct Amadeus structure
            processed_guests = []
            for idx, guest in enumerate(guests, start=1):
                processed_guests.append({
                    "id": str(idx),  # Amadeus uses 'id' not 'id'
                    "title": guest.get("title", "MR"),  # Top level fields
                    "firstName": guest.get("firstName", "Guest"),
                    "lastName": guest.get("lastName", "User"),
                    "phone": guest.get("phone", "+00000000000"),  # Not nested
                    "email": guest.get("email", user.email)  # Not nested
                })

            # Build payment structure (sandbox vs production)
            if django_settings.AMADEUS_API_TESTING:
                payment = {
                    "method": "CREDIT_CARD",
                    "paymentCard": {  # Correct Amadeus structure
                        "paymentCardInfo": {
                            "vendorCode": "VI",
                            "cardNumber": "4111111111111111",
                            "expiryDate": "2025-12",
                            "holderName": "TEST USER"
                        }
                    }
                }
            elif not payment:
                return Response({"error": "Payment details are required"}, status=status.HTTP_400_BAD_REQUEST)

            # Build room associations with correct format
            room_associations = [{
                "guestReferences": [{"guestReference": g["id"]} for g in processed_guests],
                "offerId": offer_id  # Correct field name
            }]

            # Verify offer is still available
            offer_response = amadeus_client.shopping.hotel_offer_search(offer_id).get()
            if offer_response.status_code != 200:
                return Response({"error": "Offer no longer available"}, status=status.HTTP_400_BAD_REQUEST)

            # Prepare final booking payload
            booking_payload = {
                "data": {
                    "type": "hotel-order",
                    "offerId": offer_id,  # ✅ Correct field name
                    "guests": processed_guests,
                    "payment": payment,
                    "roomAssociations": [{
                        "guestReferences": [{"id": g["id"]} for g in processed_guests],  # ✅ Use `id`, not `tid`
                        "offerId": offer_id  # ✅ Use `offerId`, not `hotelOfferId`
                    }],
                    "travelAgent": {
                        "contact": {"email": user.email}
                    }
                }
            }

            # Debugging: Print the payload before sending to Amadeus
            print("Final Amadeus Booking Payload:")
            print(json.dumps(booking_payload, indent=4), "?????????????????????")
            # Make the booking request
            booking_response = amadeus_client.booking.hotel_orders.post(booking_payload)
            booking = booking_response.data

            # Return successful response
            return Response({
                "pnr": booking["associatedRecords"][0]["reference"],
                "status": booking["hotelBookings"][0]["bookingStatus"],
                "provider_confirmation": booking["hotelBookings"][0]["hotelProviderInformation"][0]["confirmationNumber"]
            }, status=status.HTTP_200_OK)

        except ResponseError as error:
            return Response({
                "error": "Booking failed",
                "details": error.response.body,
                "debug": str(error)
            }, status=status.HTTP_400_BAD_REQUEST)
        except KeyError as e:
            return Response({"error": f"Missing data in response: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": "Internal server error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=False, methods=["get"], url_path="cancellation-options")
    def cancellation_policies(self, request):
        """Retrieve hotel cancellation policies, including free and non-refundable options."""
        hotel_id = request.query_params.get("hotel_id")
        if not hotel_id:
            return Response({"error": "Hotel ID is required"}, status=400)

        try:
            response = amadeus_client.shopping.hotel_offer_search.get(hotelIds=hotel_id)
            policies = [
                {"offerId": o["id"],
                "cancellation_policy": o["policies"]["cancellation"]} for o in response.data
            ]
            return Response(policies)
        except ResponseError as e:
            return Response({"error": str(e)}, status=500)

    @action(detail=False, methods=["get"], url_path="last-minute-deals")
    def last_minute_deals(self, request):
        """Retrieve last-minute hotel deals and mobile-exclusive discounts."""
        try:
            response = amadeus_client.shopping.hotel_offers_search.get(lastMinuteDeals=True)
            return Response(response.data)
        except ResponseError as e:
            return Response({"error": str(e)}, status=500)

    @city_search_schema
    @action(detail=False, methods=["get"], url_path="search-city")
    def city_search(self, request):
        """Search for cities by keyword using Amadeus API."""
        term = request.query_params.get("term")
        if not term:
            return Response({"error": "A search term is required"}, status=400)

        try:
            response = amadeus_client.reference_data.locations.get(keyword=term, subType=Location.ANY)
            cities = self.get_city_list(response.data)
            return JsonResponse(cities, safe=False)
        except ResponseError as error:
            return Response({"error": str(error)}, status=500)

    def get_city_list(self, data):
        """
        Format city search results into a JSON-friendly list.

        Args:
            data (list): A list of city location dictionaries from the Amadeus API response.

        Returns:
            list: A list of formatted city strings in the format 'IATA_CODE, City Name'.

        Example:
            Input:
            [
                {"iataCode": "NYC", "name": "New York"},
                {"iataCode": "LON", "name": "London"},
                {"iataCode": "PAR", "name": "Paris"}
            ]

            Output:
            [
                "NYC, New York",
                "LON, London",
                "PAR, Paris"
            ]
        """
        return list({f"{item['iataCode']}, {item['name']}" for item in data})

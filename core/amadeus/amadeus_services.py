import logging
from datetime import datetime, timedelta
from amadeus import Client, ResponseError
from core.amadeus import amadeus_client

logger = logging.getLogger(__name__)

def list_or_fetch_hotels_by_city(city_code, **filters):
    """Fetch hotels based on city code with optional filters."""
    try:
        # Base parameters
        params = {"cityCode": city_code}

        # Add optional filters if provided
        optional_params = [
            "latitude", "longitude", "radius", "radiusUnit",
            "hotelName", "chains", "amenities", "ratings"
        ]
        for key in optional_params:
            if key in filters:
                params[key] = filters[key]

        # Make API request with parameters
        response = amadeus_client.reference_data.locations.hotels.by_city.get(**params)

        # Process and return hotel data
        return [
            {
                "hotel_id": h["hotelId"],
                "name": h["name"],
                "city": city_code,
                # Include additional details as needed
            }
            for h in response.data
        ]
    except Exception as e:
        logger.error(f"Error fetching hotels: {str(e)}", exc_info=True)
        return {"error": str(e)}



def search_hotels(
        hotel_ids, check_in, check_out, adults, room_quantity,
        country_of_residence=None, price_range=None
):
    """Search for hotels with optional filters."""
    query_params = {
        "hotelIds": ",".join(hotel_ids),
        "checkInDate": check_in,
        "checkOutDate": check_out,
        "adults": adults,
        "roomQuantity": room_quantity,
    }
    if country_of_residence:
        query_params["countryOfResidence"] = country_of_residence

    if price_range:
        try:
            min_price, max_price = map(int, price_range.split('-'))
            if min_price > max_price:
                return {
                    "error": "Minimum price must be less than maximum price."
                }
        except ValueError:
            return {
                "error": "Invalid price range format. Use min-max (e.g., 100-300)"
            }

    try:
        response = amadeus_client.shopping.hotel_offers_search.get(**query_params)
        return response.data
    except ResponseError as amadeus_error:
        logger.error(f"Amadeus API Error: {amadeus_error}")
        return {"error": str(amadeus_error)}


def fetch_hotel_details(hotel_id):
    """Retrieve hotel details by ID."""
    try:
        response = amadeus_client.reference_data.locations.hotels.by_hotels.get(hotelIds=hotel_id)
        return response.data
    except ResponseError as e:
        logger.error(f"Error fetching hotel details: {str(e)}", exc_info=True)
        return {"error": str(e)}

def book_hotel_room(user, offer_id):
    """Book a hotel room using Amadeus API."""
    if not offer_id:
        return {"error": "Offer ID is required"}

    profile = getattr(user, "profile", None)
    if not profile or not profile.first_name or not profile.last_name or not profile.mobile_number:
        return {"error": "Incomplete profile. Update first name, last name, and mobile number."}

    try:
        offer_availability = amadeus_client.shopping.hotel_offer_search(offer_id).get()
        if offer_availability.status_code != 200:
            return {"error": "Room not available"}

        guests = [{
            "tid": 1,
            "title": "MR" if profile.gender == "MALE" else "MS",
            "firstName": profile.first_name,
            "lastName": profile.last_name,
            "phone": profile.mobile_number,
            "email": user.email,
        }]

        travel_agent = {"contact": {"email": "support@yourcompany.com"}}
        room_associations = [{"guestReferences": [{"guestReference": "1"}], "hotelOfferId": offer_id}]

        payment = {
            "method": "CREDIT_CARD",
            "paymentCard": {
                "paymentCardInfo": {
                    "vendorCode": "VI",
                    "cardNumber": "4151289722471370",
                    "expiryDate": "2030-08",
                    "holderName": f"{profile.first_name} {profile.last_name}"
                }
            }
        }

        booking = amadeus_client.booking.hotel_orders.post(
            guests=guests,
            travel_agent=travel_agent,
            room_associations=room_associations,
            payment=payment
        ).data

        return {
            "pnr": booking['associatedRecords'][0]['reference'],
            "status": booking['hotelBookings'][0]['bookingStatus'],
            "providerConfirmationId": booking['hotelBookings'][0]['hotelProviderInformation'][0]['confirmationNumber']
        }

    except ResponseError as e:
        logger.error(f"Booking error: {str(e)}", exc_info=True)
        return {"error": str(e)}

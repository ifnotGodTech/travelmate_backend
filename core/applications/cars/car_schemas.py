from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, inline_serializer
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers

# Schema for LocationViewSet
location_schema = extend_schema_view(
    list=extend_schema(
        summary="List all locations",
        description="Returns a list of all available locations.",
        tags=['Car Locations']
    ),
    retrieve=extend_schema(
        summary="Retrieve a location",
        description="Returns details of a specific location.",
        tags=['Car Locations']
    ),
    create=extend_schema(
        summary="Create a location",
        description="Create a new location (admin only).",
        tags=['Car Locations']
    ),
    update=extend_schema(
        summary="Update a location",
        description="Update an existing location (admin only).",
        tags=['Car Locations']
    ),
    partial_update=extend_schema(
        summary="Partial update a location",
        description="Partially update an existing location (admin only).",
        tags=['Car Locations']
    ),
    destroy=extend_schema(
        summary="Delete a location",
        description="Delete an existing location (admin only).",
        tags=['Car Locations']
    ),
    search=extend_schema(
        summary="Search locations",
        description="Search locations by name, city or country.",
        tags=['Car Locations'],
        parameters=[
            OpenApiParameter(
                name='q',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search query (min 3 characters)',
                required=True
            )
        ],
        examples=[
            OpenApiExample(
                'Example 1',
                summary='Search for London',
                value={'q': 'London'},
                description='Search for locations containing "London"'
            )
        ]
    )
)

# Schema for CarCategoryViewSet
car_category_schema = extend_schema_view(
    list=extend_schema(
        summary="List all car categories",
        description="Returns a list of all available car categories.",
        tags=['Car Categories']
    ),
    retrieve=extend_schema(
        summary="Retrieve a car category",
        description="Returns details of a specific car category.",
        tags=['Car Categories']
    ),
    create=extend_schema(
        summary="Create a car category",
        description="Create a new car category (admin only).",
        tags=['Car Categories']
    ),
    update=extend_schema(
        summary="Update a car category",
        description="Update an existing car category (admin only).",
        tags=['Car Categories']
    ),
    partial_update=extend_schema(
        summary="Partial update a car category",
        description="Partially update an existing car category (admin only).",
        tags=['Car Categories']
    ),
    destroy=extend_schema(
        summary="Delete a car category",
        description="Delete an existing car category (admin only).",
        tags=['Car Categories']
    )
)

# Schema for CarCompanyViewSet
car_company_schema = extend_schema_view(
    list=extend_schema(
        summary="List all car companies",
        description="Returns a list of all available car companies.",
        tags=['Car Companies']
    ),
    retrieve=extend_schema(
        summary="Retrieve a car company",
        description="Returns details of a specific car company.",
        tags=['Car Companies']
    ),
    create=extend_schema(
        summary="Create a car company",
        description="Create a new car company (admin only).",
        tags=['Car Companies']
    ),
    update=extend_schema(
        summary="Update a car company",
        description="Update an existing car company (admin only).",
        tags=['Car Companies']
    ),
    partial_update=extend_schema(
        summary="Partial update a car company",
        description="Partially update an existing car company (admin only).",
        tags=['Car Companies']
    ),
    destroy=extend_schema(
        summary="Delete a car company",
        description="Delete an existing car company (admin only).",
        tags=['Car Companies']
    )
)

# Schema for TransferSearchViewSet
transfer_search_schema = extend_schema_view(
    search=extend_schema(
        summary="Search for transfers",
        description="Search for available car transfers based on criteria.",
        tags=['Transfers'],
        request=inline_serializer(
            name='TransferSearchRequest',
            fields={
                'pickup_location': serializers.CharField(),
                'dropoff_location': serializers.CharField(required=False),
                'pickup_date': serializers.DateField(),
                'pickup_time': serializers.TimeField(),
                'passengers': serializers.IntegerField(default=1),
                'transfer_type': serializers.ChoiceField(
                    choices=['PRIVATE', 'SHARED'],
                    default='PRIVATE'
                ),
                'vehicle_type': serializers.CharField(required=False),
                'price_min': serializers.FloatField(required=False),
                'price_max': serializers.FloatField(required=False),
                'end_address': serializers.CharField(required=False),
                'end_city': serializers.CharField(required=False),
                'end_zipcode': serializers.CharField(required=False),
                'end_country': serializers.CharField(required=False),
                'end_name': serializers.CharField(required=False),
                'end_geo_lat': serializers.FloatField(required=False),
                'end_geo_long': serializers.FloatField(required=False),
                'connected_flight': serializers.BooleanField(required=False),
                'flight_number': serializers.CharField(required=False),
                'flight_departure_time': serializers.DateTimeField(required=False),
                'flight_departure_location': serializers.CharField(required=False),
                'flight_arrival_time': serializers.DateTimeField(required=False),
                'flight_arrival_location': serializers.CharField(required=False)
            }
        ),
        examples=[
            OpenApiExample(
                'Example',
                summary='Paris transfer with geo coordinates',
                value={
                    'pickup_location': 'CDG',
                    'dropoff_location': 'FR',
                    'pickup_date': '2025-04-10',
                    'pickup_time': '10:30',
                    'end_address': 'Avenue Anatole France, 5',
                    'end_city': 'Paris',
                    'end_country': 'FR',
                    'end_geo_lat': 48.859466,
                    'end_geo_long': 2.2976965,
                    'price_min': 50,
                    'price_max': 150,
                    'passengers': 2
                },
                description='Transfer search from Charles de Gaulle to Eiffel Tower with price range'
            )
        ]
    ),
    details=extend_schema(
        summary="Get transfer details",
        description="Get details of a specific transfer by ID.",
        tags=['Transfers'],
        parameters=[
            OpenApiParameter(
                name='transfer_id',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Transfer ID from search results',
                required=True
            )
        ]
    )
)

# Schema for CarBookingViewSet
car_booking_schema = extend_schema_view(
    list=extend_schema(
        summary="List all car bookings",
        description="Returns a list of all car bookings for the current user.",
        tags=['Car Bookings']
    ),
    retrieve=extend_schema(
        summary="Retrieve a car booking",
        description="Returns details of a specific car booking.",
        tags=['Car Bookings']
    ),

    create=extend_schema(
        summary="Create a car booking",
        description="Create a new car booking based on a previously searched transfer.",
        tags=['Car Bookings'],
        request=inline_serializer(
            name='CarBookingCreateRequest',
            fields={
                'transfer_id': serializers.CharField(help_text='ID of the previously searched transfer'),
                'passengers': serializers.IntegerField(default=1, help_text='Number of passengers'),
                'child_seats': serializers.IntegerField(default=0, help_text='Number of child seats required'),
                'notes': serializers.CharField(required=False, help_text='Additional booking notes'),
                'customer': serializers.DictField(
                    help_text='Customer details for the booking',
                    child=serializers.CharField(),
                    default={
                        'firstName': 'John',
                        'lastName': 'Doe',
                        'title': 'Mr',
                        'contacts': {
                            'email': 'john.doe@example.com',
                            'phoneNumber': '+1234567890'
                        }
                    }
                )
            }
        ),
        examples=[
            OpenApiExample(
                'Example',
                summary='Create booking with full customer details',
                value={
                    'transfer_id': 'TRANS12345',
                    'passengers': 2,
                    'child_seats': 1,
                    'notes': 'Arriving on Flight BA123',
                    'customer': {
                        'firstName': 'Jane',
                        'lastName': 'Smith',
                        'title': 'Ms',
                        'contacts': {
                            'email': 'jane.smith@example.com',
                            'phoneNumber': '+1987654321'
                        }
                    }
                },
                description='Create a car booking with complete customer information'
            )
        ]
    ),
    update=extend_schema(
        summary="Update a car booking",
        description="Update an existing car booking (admin only).",
        tags=['Car Bookings']
    ),
    partial_update=extend_schema(
        summary="Partial update a car booking",
        description="Partially update an existing car booking (admin only).",
        tags=['Car Bookings']
    ),
    destroy=extend_schema(
        summary="Delete a car booking",
        description="Delete an existing car booking (admin only).",
        tags=['Car Bookings']
    ),
    process_payment=extend_schema(
        summary="Process payment for booking",
        description="Process payment for a pending car booking.",
        tags=['Car Bookings'],
        request=inline_serializer(
            name='ProcessPaymentRequest',
            fields={
                'payment_method_id': serializers.CharField(),  # Changed back to payment_method_id
                'save_payment_method': serializers.BooleanField(default=False)
            }
        ),
        examples=[
            OpenApiExample(
                'Example 1',
                summary='Process payment with Visa card',
                value={
                    'payment_method_id': 'pm_card_visa'  # Changed back to payment_method_id
                },
                description='Process a payment for a booking using a Visa card'
            )
        ],
        responses={
            200: inline_serializer(
                name='ProcessPaymentResponse',
                fields={
                    'booking': OpenApiTypes.OBJECT,
                    'payment_details': OpenApiTypes.OBJECT
                }
            )
        }
    ),
    cancel_booking=extend_schema(
        summary="Cancel a booking",
        description="Cancel an existing car booking.",
        tags=['Car Bookings'],
        request=inline_serializer(
            name='CancelBookingRequest',
            fields={
                'request_refund': serializers.BooleanField(default=False),
                'reason': serializers.CharField(required=False)
            }
        )
    )
)

# Schema for PaymentViewSet
payment_schema = extend_schema_view(
    list=extend_schema(
        summary="List all payments",
        description="Returns a list of all payments for the current user's bookings.",
        tags=['Car Payments']
    ),
    retrieve=extend_schema(
        summary="Retrieve a payment",
        description="Returns details of a specific payment.",
        tags=['Car Payments']
    ),
    create=extend_schema(
        summary="Create a payment",
        description="Create a new payment record (for manual payments).",
        tags=['Car Payments'],
        request=inline_serializer(
            name='PaymentCreateRequest',
            fields={
                'booking_id': serializers.IntegerField(),
                'payment_method': serializers.CharField(),  # Keep as payment_method for this endpoint
                'transaction_id': serializers.CharField(required=False),
                'notes': serializers.CharField(required=False)
            }
        ),
        examples=[
            OpenApiExample(
                'Example 1',
                summary='Create payment with Visa card',
                value={
                    'booking_id': 1,
                    'payment_method': 'pm_card_visa'  # Keep as payment_method for this endpoint
                },
                description='Create a payment record using a Visa card'
            )
        ]
    ),
    update=extend_schema(
        summary="Update a payment",
        description="Update an existing payment (admin only).",
        tags=['Car Payments']
    ),
    partial_update=extend_schema(
        summary="Partial update a payment",
        description="Partially update an existing payment (admin only).",
        tags=['Car Payments']
    ),
    destroy=extend_schema(
        summary="Delete a payment",
        description="Delete an existing payment (admin only).",
        tags=['Car Payments']
    ),
    refund=extend_schema(
        summary="Process refund",
        description="Initiate a refund for a completed payment.",
        tags=['Car Payments'],
        responses={
            200: inline_serializer(
                name='RefundResponse',
                fields={
                    'status': serializers.CharField(),
                    'refund_id': serializers.CharField(required=False)
                }
            )
        }
    )
)

# Schema for RecentSearchesView
recent_searches_schema = extend_schema(
    summary="Get recent searches",
    description="Returns the 10 most recent car searches for the authenticated user.",
    tags=['Car Searches'],
    responses={
        200: inline_serializer(
            name='RecentSearchesResponse',
            fields={
                'id': serializers.IntegerField(),
                'pickup_location': inline_serializer(
                    name='LocationResponse',
                    fields={
                        'id': serializers.IntegerField(),
                        'code': serializers.CharField(),
                        'name': serializers.CharField(),
                        'city': serializers.CharField(),
                        'country': serializers.CharField(),
                        'address': serializers.CharField(),
                        'latitude': serializers.DecimalField(max_digits=9, decimal_places=6),
                        'longitude': serializers.DecimalField(max_digits=9, decimal_places=6),
                        'airport_code': serializers.CharField()
                    }
                ),
                'dropoff_location': inline_serializer(
                    name='LocationResponse',
                    fields={
                        'id': serializers.IntegerField(),
                        'code': serializers.CharField(),
                        'name': serializers.CharField(),
                        'city': serializers.CharField(),
                        'country': serializers.CharField(),
                        'address': serializers.CharField(),
                        'latitude': serializers.DecimalField(max_digits=9, decimal_places=6),
                        'longitude': serializers.DecimalField(max_digits=9, decimal_places=6),
                        'airport_code': serializers.CharField()
                    }
                ),
                'pickup_date': serializers.DateField(),
                'dropoff_date': serializers.DateField(),
                'created_at': serializers.DateTimeField(),
                'passengers': serializers.IntegerField()
            }
        )
    }
)

# Schema for PopularDestinationsView
popular_destinations_schema = extend_schema(
    summary="Get popular destinations",
    description="Returns the most popular pickup and dropoff locations based on search frequency in the last 30 days.",
    tags=['Car Searches'],
    responses={
        200: inline_serializer(
            name='PopularDestinationsResponse',
            fields={
                'popular_pickup_locations': serializers.ListField(
                    child=inline_serializer(
                        name='PopularLocationResponse',
                        fields={
                            'location': inline_serializer(
                                name='LocationResponse',
                                fields={
                                    'id': serializers.IntegerField(),
                                    'code': serializers.CharField(),
                                    'name': serializers.CharField(),
                                    'city': serializers.CharField(),
                                    'country': serializers.CharField(),
                                    'address': serializers.CharField(),
                                    'latitude': serializers.DecimalField(max_digits=9, decimal_places=6),
                                    'longitude': serializers.DecimalField(max_digits=9, decimal_places=6),
                                    'airport_code': serializers.CharField()
                                }
                            ),
                            'search_count': serializers.IntegerField()
                        }
                    )
                ),
                'popular_dropoff_locations': serializers.ListField(
                    child=inline_serializer(
                        name='PopularLocationResponse',
                        fields={
                            'location': inline_serializer(
                                name='LocationResponse',
                                fields={
                                    'id': serializers.IntegerField(),
                                    'code': serializers.CharField(),
                                    'name': serializers.CharField(),
                                    'city': serializers.CharField(),
                                    'country': serializers.CharField(),
                                    'address': serializers.CharField(),
                                    'latitude': serializers.DecimalField(max_digits=9, decimal_places=6),
                                    'longitude': serializers.DecimalField(max_digits=9, decimal_places=6),
                                    'airport_code': serializers.CharField()
                                }
                            ),
                            'search_count': serializers.IntegerField()
                        }
                    )
                )
            }
        )
    }
)

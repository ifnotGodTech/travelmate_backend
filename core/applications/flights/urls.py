from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FlightBookingViewSet, FlightSearchViewSet, stripe_webhook

app_name = "flights"


router = DefaultRouter()
router.register(r'bookings', FlightBookingViewSet, basename='booking')
router.register(r'search', FlightSearchViewSet, basename='search')
# router.register(r'admin/flight-bookings', FlightAdminViewSet, basename='admin-flight-bookings')

urlpatterns = [
    path('', include(router.urls)),
    path('stripe-webhook/', stripe_webhook, name='stripe_webhook'),

]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from .webhooks import stripe_webhook


app_name = "cars"

router = DefaultRouter()
router.register(r'locations', LocationViewSet)
router.register(r'categories', CarCategoryViewSet)
router.register(r'companies', CarCompanyViewSet)
router.register(r'transfers', TransferSearchViewSet, basename='transfers')
router.register(r'car-bookings', CarBookingViewSet)
router.register(r'payments', PaymentViewSet)
# router.register(r'admin/car-bookings', CarAdminViewSet, basename='admin-car-bookings')

urlpatterns = [
    path('api/cars/', include(router.urls)),
    path('webhooks/stripe/', stripe_webhook, name='stripe-webhook'),
    path('api/cars/recent-searches/', RecentSearchesView.as_view(), name='recent-searches'),
    path('api/cars/popular-destinations/', PopularDestinationsView.as_view(), name='popular-destinations'),
]

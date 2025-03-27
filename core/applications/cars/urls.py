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
router.register(r'bookings', TransferBookingViewSet)
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('webhooks/stripe/', stripe_webhook, name='stripe-webhook'),
]

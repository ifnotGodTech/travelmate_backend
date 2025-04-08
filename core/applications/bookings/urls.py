from django.urls import path
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UnifiedBookingAdminViewSet

app_name = "bookings"


router = DefaultRouter()
router.register(r'admin/bookings', UnifiedBookingAdminViewSet, basename='admin-bookings')


urlpatterns = [
    path('', include(router.urls)),

]

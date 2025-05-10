from django.urls import path
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UnifiedBookingAdminViewSet, UserBookingViewSet

app_name = "bookings"


router = DefaultRouter()
router.register(r'admin/bookings', UnifiedBookingAdminViewSet, basename='admin-bookings')
router.register(r'user/bookings', UserBookingViewSet, basename='user-bookings')


urlpatterns = [
    path('', include(router.urls)),

]

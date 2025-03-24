from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from core.applications.stay.api.views import HotelApiViewSet

PREFIX = "stay"
API_VERSION = settings.API_VERSION

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("hotels", HotelApiViewSet, basename="hotel")


app_name = f"{PREFIX}"
urlpatterns = router.urls

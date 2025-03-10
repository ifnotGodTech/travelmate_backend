from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from core.applications.users.api.views import UserViewSet, ProfileViewSet

PREFIX = "users"

API_VERSION = settings.API_VERSION

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("users", UserViewSet, basename="users")
router.register("profile", ProfileViewSet, basename="profile")

app_name = f"{PREFIX}"
urlpatterns = router.urls

from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from core.applications.users.api.views import (
    AdminUserViewSet, UserViewSet,  ProfileViewSet,
    UserRegistrationViewSet, AdminRegistrationViewSet

)
PREFIX = "users"

API_VERSION = settings.API_VERSION

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("users", UserViewSet, basename="users")
router.register(
    "registration_with_otp", UserRegistrationViewSet,
    basename="otpregisterviews"
)
router.register(
    "registration_with_otp_admin", AdminRegistrationViewSet,
    basename="adminregisterviews"
)


router.register("profile", ProfileViewSet, basename="profile")
router.register("admin", AdminUserViewSet, basename="admin-users")

app_name = f"{PREFIX}"
urlpatterns = router.urls

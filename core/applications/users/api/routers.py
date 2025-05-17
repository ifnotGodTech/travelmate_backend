from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter
from django.urls import path

from core.applications.users.api.views import (
    SuperUserViewSet, UserViewSet,  ProfileViewSet,
    UserRegistrationViewSet, AdminRegistrationViewSet,
    SuperAdminViewSet, RoleViewSet, GroupedPermissionsView,
    AcceptInvitationView, ValidateInvitationTokenView
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
router.register("superuser", SuperUserViewSet, basename="admin-users")

router.register("roles", RoleViewSet, basename="roles")
router.register("superadmin", SuperAdminViewSet, basename="superadmin")

app_name = f"{PREFIX}"
urlpatterns = router.urls
urlpatterns += [
    path("permissions/", GroupedPermissionsView.as_view(), name="grouped-permissions"),
    path("invitation/accept/", AcceptInvitationView.as_view(), name="invitation-accept"),
    path("invitation/validate/", ValidateInvitationTokenView.as_view(), name="invitation-validate"),

]

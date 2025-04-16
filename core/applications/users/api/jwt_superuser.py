from django.urls import path

from core.applications.users.api.views import (
    SuperUserTokenObtainPairView, TokenRefreshView, TokenVerifyView
)

urlpatterns = [
    path("admin/jwt/login-superuser/", SuperUserTokenObtainPairView.as_view(), name="admin-jwt-create"),
    path("admin/jwt/refresh-superuser/", TokenRefreshView.as_view(), name="admin-jwt-refresh"),
    path("admin/jwt/verify-superuser/", TokenVerifyView.as_view(), name="admin-jwt-verify"),
]

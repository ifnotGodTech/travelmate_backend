from django.urls import re_path

from core.applications.users.api import views

urlpatterns = [
    re_path(r"^jwt/login/?$", views.TokenObtainPairView.as_view(), name="jwt-create"),
    re_path(r"^jwt/token/refresh/?$", views.TokenRefreshView.as_view(), name="jwt-refresh"),
    re_path(r"^jwt/token/verify/?$", views.TokenVerifyView.as_view(), name="jwt-verify"),
]

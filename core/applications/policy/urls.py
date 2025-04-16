from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'policy'

# Router for admin endpoints (POST, PUT, DELETE)
admin_router = DefaultRouter()
admin_router.register(r'about-us', views.AdminAboutUsViewSet, basename='admin-about-us')
admin_router.register(r'privacy-policy', views.AdminPrivacyPolicyViewSet, basename='admin-privacy-policy')
admin_router.register(r'terms-of-use', views.AdminTermsOfUseViewSet, basename='admin-terms-of-use')
admin_router.register(r'partner-categories', views.AdminPartnerCategoryViewSet, basename='admin-partner-categories')
admin_router.register(r'partners', views.AdminPartnerViewSet, basename='admin-partners')

# Router for regular user endpoints (GET only)
user_router = DefaultRouter()
user_router.register(r'about-us', views.UserAboutUsViewSet, basename='about-us')
user_router.register(r'privacy-policy', views.UserPrivacyPolicyViewSet, basename='privacy-policy')
user_router.register(r'terms-of-use', views.UserTermsOfUseViewSet, basename='terms-of-use')
user_router.register(r'partners', views.UserPartnerViewSet, basename='partners')

app_name = 'policy'

urlpatterns = [
    path('api/admin/', include(admin_router.urls)),
    path('api/', include(user_router.urls)),
]

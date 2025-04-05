from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


app_name = "FAQ"


# Router for user-facing endpoints (read-only)
user_router = DefaultRouter()
user_router.register(r'categories', views.FAQCategoryReadOnlyViewSet)
user_router.register(r'faqs', views.FAQReadOnlyViewSet)

# Router for admin endpoints (full CRUD)
admin_router = DefaultRouter()
admin_router.register(r'categories', views.FAQCategoryViewSet)
admin_router.register(r'', views.FAQViewSet)

urlpatterns = [
    # Public facing API for users
    path('api/', include(user_router.urls)),

    # Admin API with full CRUD operations
    path('api/admin/faqs/', include(admin_router.urls)),
]

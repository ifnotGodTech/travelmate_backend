# ruff: noqa
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include
from django.urls import path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from core.applications.users.api.views import AppleLoginView, FacebookLoginView, GoogleLoginView
from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path(
        "about/",
        TemplateView.as_view(template_name="pages/about.html"),
        name="about",
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("core.applications.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    path("flights/", include("core.applications.flights.urls", namespace="flights")),
    path("cars/", include("core.applications.cars.urls", namespace="cars")),
    path("", include("core.applications.tickets.urls", namespace="tickets")),
    path("", include("core.applications.faq.urls", namespace="faq")),
    path("", include("core.applications.chat.urls", namespace="chat")),
    path("", include("core.applications.policy.urls", namespace="policy")),

    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]
if settings.DEBUG:
    # Static file serving when using Gunicorn + Uvicorn for local web socket development
    urlpatterns += staticfiles_urlpatterns()

# API URLS
urlpatterns += [
    # API base url
    path("api/", include("config.api_router")),
    # DRF auth token
    path("api/auth/", include("core.applications.users.api.jwt")),
    path("api/auth/", include("core.applications.users.api.jwt_superuser")),
    path("api/", include("core.applications.users.api.routers", namespace="users")),
    path("api/", include("core.applications.stay.api.stay_routers", namespace="stay")),
    path("api/", include("core.applications.bookings.urls", namespace="bookings")),
    path("api/auth-token/", obtain_auth_token),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    # dj-rest-auth
    # path("dj-rest-auth/", include("dj_rest_auth.urls")),
    # path("api/auth/registration/", include("dj_rest_auth.registration.urls")),  # User Registration
    path("api/auth/social/", include("allauth.socialaccount.urls")),  # Social Auth Setup
    path("api/auth/social/google/", GoogleLoginView.as_view(), name="google_login"),
    path("api/auth/social/facebook/", FacebookLoginView.as_view(), name="facebook_login"),
    path("api/auth/social/apple/", AppleLoginView.as_view(), name="apple_login"),
]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

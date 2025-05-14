from django.urls import path
from .views import (
    DashboardStatsView, UserActivitiesView, MessagesView,
    DashboardOverviewView
)
from . import views

app_name = "dashboard"

urlpatterns = [
    path("api/admin/dashboard/overview/", DashboardOverviewView.as_view(), name="dashboard-overview"),
    path("api/admin/dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("api/admin/dashboard/activities/", UserActivitiesView.as_view(), name="user-activities"),
    path('booking-types/', views.BookingTypeView.as_view(), name='booking-types'),
    path('api/admin/dashboard/revenue/', views.RevenueView.as_view(), name='revenue'),
    path('api/admin/dashboard/messages/', MessagesView.as_view(), name='messages'),
]

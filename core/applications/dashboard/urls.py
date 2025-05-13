from django.urls import path
from .views import DashboardStatsView, UserActivitiesView

app_name = "dashboard"

urlpatterns = [
    path("api/admin/dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("api/admin/dashboard/activities/", UserActivitiesView.as_view(), name="user-activities"),
]

from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .serializers import DashboardStatsSerializer, UserActivitySerializer

dashboard_stats_schema = extend_schema(
    summary="Dashboard Overview",
    description="Returns total number of bookings in the system",
    responses={
        200: DashboardStatsSerializer,
        401: OpenApiTypes.OBJECT
    },
    tags=["Dashboard Overview"]
)

user_activities_schema = extend_schema(
    summary="Recent User Activities",
    description="Returns a list of recent user booking activities",
    responses={
        200: UserActivitySerializer(many=True),
        401: OpenApiTypes.OBJECT
    },
    tags=["Dashboard Overview"]
)

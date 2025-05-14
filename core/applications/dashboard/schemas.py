from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .serializers import (
    DashboardStatsSerializer, UserActivitySerializer,
    RevenueSerializer, MessageSerializer, DashboardOverviewSerializer
)

dashboard_stats_schema = extend_schema(
    summary="Dashboard Statistics",
    description="Get dashboard statistics including total bookings",
    responses={
        200: DashboardStatsSerializer,
        401: OpenApiTypes.OBJECT
    },
    tags=["Dashboard"]
)

user_activities_schema = extend_schema(
    summary="Recent User Activities",
    description="Get recent user activities including bookings",
    responses={
        200: UserActivitySerializer(many=True),
        401: OpenApiTypes.OBJECT
    },
    tags=["Dashboard"]
)

dashboard_overview_schema = extend_schema(
    summary="Dashboard Overview",
    description="Get complete dashboard overview including stats, revenue, activities, and messages",
    responses={
        200: DashboardOverviewSerializer,
        401: OpenApiTypes.OBJECT
    },
    tags=["Dashboard"]
)

messages_schema = extend_schema(
    summary="All Messages",
    description="Get all messages from tickets and chats",
    responses={
        200: MessageSerializer(many=True),
        401: OpenApiTypes.OBJECT
    },
    tags=["Dashboard"]
)

revenue_schema = extend_schema(
    summary="Revenue Statistics",
    description="Get revenue statistics from car and flight bookings",
    responses={
        200: RevenueSerializer,
        401: OpenApiTypes.OBJECT
    },
    tags=["Dashboard"]
)

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.applications.bookings.models import Booking
from .schemas import dashboard_stats_schema, user_activities_schema
from .serializers import DashboardStatsSerializer, UserActivitySerializer

# Create your views here.

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    @dashboard_stats_schema
    def get(self, request):
        total_bookings = Booking.objects.count()

        serializer = DashboardStatsSerializer({
            "total_bookings": total_bookings
        })
        return Response(serializer.data)

class UserActivitiesView(APIView):
    permission_classes = [IsAuthenticated]

    @user_activities_schema
    def get(self, request):
        # Get the 10 most recent bookings
        recent_bookings = Booking.objects.select_related('user').order_by('-created_at')[:10]

        serializer = UserActivitySerializer(recent_bookings, many=True)
        return Response(serializer.data)

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.applications.bookings.models import Booking
from core.applications.cars.models import CarBooking
from core.applications.flights.models import FlightBooking
from core.applications.tickets.models import Ticket, Message as TicketMessage
from core.applications.chat.models import ChatMessage, ChatSession
from .schemas import (
    dashboard_stats_schema, user_activities_schema,
    dashboard_overview_schema, messages_schema, revenue_schema
)
from .serializers import (
    DashboardStatsSerializer, UserActivitySerializer,
    BookingTypeSerializer, RevenueSerializer, MessageSerializer,
    DashboardOverviewSerializer
)
from django.db.models import Sum, Count
from decimal import Decimal
from itertools import chain
from operator import attrgetter

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

class BookingTypeView(APIView):
    def get(self, request):
        bookings = Booking.objects.all()
        serializer = BookingTypeSerializer(bookings, many=True)
        return Response(serializer.data)

class MessagesView(APIView):
    permission_classes = [IsAuthenticated]

    @messages_schema
    def get(self, request):
        # Get latest ticket messages
        ticket_messages = TicketMessage.objects.select_related(
            'ticket', 'sender'
        ).order_by('-timestamp')[:50]

        # Get latest chat messages
        chat_messages = ChatMessage.objects.select_related(
            'session', 'sender'
        ).order_by('-created_at')[:50]

        # Get latest tickets
        tickets = Ticket.objects.select_related(
            'user'
        ).order_by('-created_at')[:50]

        # Combine all messages
        messages = []

        # Add ticket messages
        for msg in ticket_messages:
            messages.append({
                'id': f'ticket_msg_{msg.id}',
                'type': 'ticket_message',
                'title': f'New message in ticket {msg.ticket.ticket_id}',
                'content': msg.content,
                'sender': msg.sender,
                'created_at': msg.timestamp,
                'ticket': msg.ticket
            })

        # Add chat messages
        for msg in chat_messages:
            messages.append({
                'id': f'chat_msg_{msg.id}',
                'type': 'chat_message',
                'title': f'New message in chat {msg.session.title}',
                'content': msg.content,
                'sender': msg.sender,
                'created_at': msg.created_at,
                'session': msg.session
            })

        # Add new tickets
        for ticket in tickets:
            messages.append({
                'id': f'ticket_{ticket.id}',
                'type': 'new_ticket',
                'title': f'New ticket: {ticket.title}',
                'content': ticket.description,
                'sender': ticket.user,
                'created_at': ticket.created_at,
                'ticket': ticket
            })

        # Sort all messages by created_at
        messages.sort(key=lambda x: x['created_at'], reverse=True)
        messages = messages[:50]

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

class RevenueView(APIView):
    permission_classes = [IsAuthenticated]

    @revenue_schema
    def get(self, request):
        # Get total car booking revenue
        car_revenue = CarBooking.objects.aggregate(
            total=Sum('service_fee')
        )['total'] or Decimal('0.00')

        # Get total flight booking revenue
        flight_revenue = FlightBooking.objects.aggregate(
            total=Sum('service_fee')
        )['total'] or Decimal('0.00')

        # Calculate total revenue
        total_revenue = car_revenue + flight_revenue

        data = {
            'total_revenue': total_revenue,
            'car_revenue': car_revenue,
            'flight_revenue': flight_revenue,
            'currency': 'USD'
        }

        serializer = RevenueSerializer(data)
        return Response(serializer.data)

class DashboardOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    @dashboard_overview_schema
    def get(self, request):
        # Get stats data
        total_bookings = Booking.objects.count()
        stats_data = {
            "total_bookings": total_bookings
        }

        # Get revenue data
        car_revenue = CarBooking.objects.aggregate(
            total=Sum('service_fee')
        )['total'] or Decimal('0.00')

        flight_revenue = FlightBooking.objects.aggregate(
            total=Sum('service_fee')
        )['total'] or Decimal('0.00')

        total_revenue = car_revenue + flight_revenue
        revenue_data = {
            'total_revenue': total_revenue,
            'car_revenue': car_revenue,
            'flight_revenue': flight_revenue,
            'currency': 'USD'
        }

        # Get recent activities
        recent_bookings = Booking.objects.select_related('user').order_by('-created_at')[:10]

        # Get messages
        ticket_messages = TicketMessage.objects.select_related(
            'ticket', 'sender'
        ).order_by('-timestamp')[:50]

        chat_messages = ChatMessage.objects.select_related(
            'session', 'sender'
        ).order_by('-created_at')[:50]

        tickets = Ticket.objects.select_related(
            'user'
        ).order_by('-created_at')[:50]

        messages = []

        # Add ticket messages
        for msg in ticket_messages:
            messages.append({
                'id': f'ticket_msg_{msg.id}',
                'type': 'ticket_message',
                'title': f'New message in ticket {msg.ticket.ticket_id}',
                'content': msg.content,
                'sender': msg.sender,
                'created_at': msg.timestamp,
                'ticket': msg.ticket
            })

        # Add chat messages
        for msg in chat_messages:
            messages.append({
                'id': f'chat_msg_{msg.id}',
                'type': 'chat_message',
                'title': f'New message in chat {msg.session.title}',
                'content': msg.content,
                'sender': msg.sender,
                'created_at': msg.created_at,
                'session': msg.session
            })

        # Add new tickets
        for ticket in tickets:
            messages.append({
                'id': f'ticket_{ticket.id}',
                'type': 'new_ticket',
                'title': f'New ticket: {ticket.title}',
                'content': ticket.description,
                'sender': ticket.user,
                'created_at': ticket.created_at,
                'ticket': ticket
            })

        # Sort all messages by created_at
        messages.sort(key=lambda x: x['created_at'], reverse=True)
        messages = messages[:50]

        # Combine all data
        overview_data = {
            'stats': stats_data,
            'revenue': revenue_data,
            'recent_activities': recent_bookings,
            'messages': messages
        }

        serializer = DashboardOverviewSerializer(overview_data)
        return Response(serializer.data)

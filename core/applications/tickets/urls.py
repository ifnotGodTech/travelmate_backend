# core/applications/tickets/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminNotificationViewSet,
    NotificationViewSet,
    TicketViewSet,
    AdminTicketViewSet,
    TicketMessageListCreateView,
    MessageViewSet,
    EscalationLevelViewSet
)

app_name = 'tickets'

# Router for regular user endpoints
user_router = DefaultRouter()
user_router.register(r'tickets', TicketViewSet, basename='ticket')
user_router.register(r'messages', MessageViewSet, basename='message')
user_router.register(r'notifications', NotificationViewSet, basename='notification')  # Add this line


# Router for admin-only endpoints
admin_router = DefaultRouter()
admin_router.register(r'tickets', AdminTicketViewSet, basename='admin-ticket')
admin_router.register(r'messages', MessageViewSet, basename='admin-message')
admin_router.register(r'escalation-levels', EscalationLevelViewSet, basename='escalation-level')
admin_router.register(r'notifications', AdminNotificationViewSet, basename='admin-notification')  # Add this line


urlpatterns = [
    # Regular user routes
    path('api/', include(user_router.urls)),

    # Regular user nested routes
    path('api/tickets/<int:ticket_pk>/messages/',
         TicketMessageListCreateView.as_view(),
         name='ticket-message-list'),

    # Admin-only routes
    path('api/admin/', include(admin_router.urls)),

    # Admin nested routes
    path('api/admin/tickets/<int:ticket_pk>/messages/',
         TicketMessageListCreateView.as_view(),
         name='admin-ticket-message-list'),
]

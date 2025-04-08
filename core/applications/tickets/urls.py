# core/applications/tickets/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TicketViewSet,
    AdminTicketViewSet,
    TicketMessageListCreateView,
    MessageViewSet,
    EscalationLevelViewSet,
    EscalationReasonViewSet
)
import sys

app_name = 'tickets'

# Router for regular user endpoints
user_router = DefaultRouter()
user_router.register(r'tickets', TicketViewSet, basename='ticket')
user_router.register(r'messages', MessageViewSet, basename='message')

# Router for admin-only endpoints
admin_router = DefaultRouter()
admin_router.register(r'tickets', AdminTicketViewSet, basename='admin-ticket')
admin_router.register(r'messages', MessageViewSet, basename='admin-message')
admin_router.register(r'escalation-levels', EscalationLevelViewSet, basename='escalation-level')
admin_router.register(r'escalation-reasons', EscalationReasonViewSet, basename='escalation-reason')

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

# Print all registered routes
print("\n=== REGISTERED API ROUTES ===")
print("\nREGULAR USER ROUTES (with api/ added at root):")
for route in user_router.urls:
    print(f"  /api/{route.pattern}")
print("  /api/tickets/<int:ticket_pk>/messages/")

print("\nADMIN ROUTES (with api/ added at root):")
for route in admin_router.urls:
    print(f"  /api/admin/{route.pattern}")
print("  /api/admin/tickets/<int:ticket_pk>/messages/")
print("\n=============================\n")

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "chat"

router = DefaultRouter()
# User routes
router.register(r'user/chats', views.UserChatSessionViewSet, basename='user-chat')
# Admin routes
router.register(r'api/admin/chats', views.AdminChatSessionViewSet, basename='admin-chat')
# Common routes
router.register(r'api/chat/messages', views.ChatMessageViewSet, basename='chat-message')

urlpatterns = [
    path('', include(router.urls)),
]

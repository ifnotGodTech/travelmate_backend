# Make sure this pattern in routing.txt matches your connection URL
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/chat/(?P<session_id>\w+)/$', consumers.ChatConsumer.as_asgi()),  # Note the ^ at the beginning
]

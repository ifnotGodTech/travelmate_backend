# ruff: noqa
"""
ASGI config for travelmate-backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/asgi/

"""

import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from core.applications.chat.jwt_middleware import JWTMiddleware

# This allows easy placement of apps within the interior
# travelmate_backend directory.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
sys.path.append(str(BASE_DIR / "travelmate_backend"))

# If DJANGO_SETTINGS_MODULE is unset, default to the local settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import logging
logger = logging.getLogger(__name__)
logger.info(f"Using settings module: {os.environ['DJANGO_SETTINGS_MODULE']}")

# This application object is used by any ASGI server configured to use this file.
django_application = get_asgi_application()

# Import websocket application here, so apps from django_application are loaded first
# Import your chat routing
from core.applications.chat.routing import websocket_urlpatterns as chat_websocket_urlpatterns
# Import any other existing routing from your websocket.py if needed
from config.websocket import websocket_application as original_websocket_application

# Create a ProtocolTypeRouter with proper middleware stacking
application = ProtocolTypeRouter({
    "http": django_application,
    "websocket": JWTMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                chat_websocket_urlpatterns
            )
        )
    ),
})

# If you need to maintain backward compatibility with other WebSocket connections
# Define a custom ASGI application that can route based on path
async def backward_compatible_websocket(scope, receive, send):
    path = scope["path"]
    if path.startswith("/ws/chat/"):
        # Let channels handle chat websockets
        await application(scope, receive, send)
    else:
        # Use your original websocket handler for other websockets
        await original_websocket_application(scope, receive, send)

# To use the backward_compatible_websocket function, replace the application definition with:
# application = backward_compatible_websocket

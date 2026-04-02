import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "wardrive.settings"

django_asgi_app = get_asgi_application()

# Tras cargar apps, ya podemos importar consumers/routing WebSocket.
from api.websockets.middleware import JWTAuthMiddlewareStack
from api.websockets.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)

"""
Punto de entrada ASGI de SistemKios.

Enruta HTTP por Django y WebSocket por Channels. Por ahora no hay consumers
(se agregan en la Fase 3, Tiempo real), pero el ruteo ya queda cableado.
"""
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Se inicializa la app HTTP de Django antes de importar rutas que tocan modelos.
django_asgi_app = get_asgi_application()

from config.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)

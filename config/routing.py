"""
Rutas WebSocket. Grupos por punto (`punto_{id}`) para stock, ventas y jornadas
en vivo.
"""
from django.urls import path

from apps.core.consumers import PuntoConsumer

websocket_urlpatterns = [
    path("ws/punto/<int:punto_id>/", PuntoConsumer.as_asgi()),
]

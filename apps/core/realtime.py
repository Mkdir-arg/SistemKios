"""
Ayudas para el tiempo real. `notificar_punto` publica un evento en el grupo
de WebSocket de un punto (`punto_{id}`); el consumer lo reenvía a las pantallas
conectadas de ese punto.
"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def notificar_punto(punto_id, tipo, **data):
    """Envía un evento {tipo, ...data} al grupo del punto."""
    if punto_id is None:
        return
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        f"punto_{punto_id}",
        {"type": "evento", "data": {"tipo": tipo, **data}},
    )


def grupo_punto(punto_id):
    return f"punto_{punto_id}"

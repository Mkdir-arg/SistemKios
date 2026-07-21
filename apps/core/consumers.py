"""Consumer WebSocket: cada cliente se suscribe al grupo de un punto."""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class PuntoConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        self.punto_id = int(self.scope["url_route"]["kwargs"]["punto_id"])

        if user is None or not user.is_authenticated:
            await self.close()
            return
        if not await self._puede_ver(user, self.punto_id):
            await self.close()
            return

        self.group = f"punto_{self.punto_id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send_json({"tipo": "conectado", "punto_id": self.punto_id})

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def evento(self, event):
        """Reenvía al cliente los eventos publicados con `notificar_punto`."""
        await self.send_json(event["data"])

    @database_sync_to_async
    def _puede_ver(self, user, punto_id):
        if user.es_super_admin:
            return True
        return user.punto_id == punto_id

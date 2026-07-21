from django.db import models


class Punto(models.Model):
    """Un local a la calle. Cada punto tiene su propio stock, precios y caja."""

    nombre = models.CharField("nombre", max_length=120)
    direccion = models.CharField("dirección", max_length=255, blank=True)
    activo = models.BooleanField("activo", default=True)
    creado = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "punto"
        verbose_name_plural = "puntos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def grupo_ws(self):
        """Nombre del grupo de WebSocket para el tiempo real de este punto."""
        return f"punto_{self.pk}"

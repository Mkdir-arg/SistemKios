from django.db import models


class Punto(models.Model):
    """
    Un local a la calle. Cada punto tiene su propio stock, precios y caja.

    El **Depósito** (almacén central) se modela como un punto especial con
    `es_deposito=True`: el stock que no está asignado a un local a la calle vive
    ahí. Hay un único depósito.
    """

    nombre = models.CharField("nombre", max_length=120)
    direccion = models.CharField("dirección", max_length=255, blank=True)
    activo = models.BooleanField("activo", default=True)
    es_deposito = models.BooleanField("es depósito", default=False)
    creado = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "punto"
        verbose_name_plural = "puntos"
        ordering = ["-es_deposito", "nombre"]  # el Depósito primero
        constraints = [
            models.UniqueConstraint(
                fields=["es_deposito"],
                condition=models.Q(es_deposito=True),
                name="un_solo_deposito",
            )
        ]

    def __str__(self):
        return self.nombre

    @property
    def grupo_ws(self):
        """Nombre del grupo de WebSocket para el tiempo real de este punto."""
        return f"punto_{self.pk}"

    @classmethod
    def get_deposito(cls):
        """Devuelve (creándolo si hace falta) el depósito central."""
        deposito, _ = cls.objects.get_or_create(
            es_deposito=True, defaults={"nombre": "Depósito"}
        )
        return deposito

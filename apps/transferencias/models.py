from django.conf import settings
from django.db import models


class Transferencia(models.Model):
    class Estado(models.TextChoices):
        COMPLETADA = "completada", "Completada"

    punto_origen = models.ForeignKey(
        "puntos.Punto", verbose_name="origen", on_delete=models.PROTECT, related_name="transferencias_salida"
    )
    punto_destino = models.ForeignKey(
        "puntos.Punto", verbose_name="destino", on_delete=models.PROTECT, related_name="transferencias_entrada"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="usuario", null=True, on_delete=models.SET_NULL, related_name="transferencias"
    )
    estado = models.CharField("estado", max_length=12, choices=Estado.choices, default=Estado.COMPLETADA)
    fecha = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "transferencia"
        verbose_name_plural = "transferencias"
        ordering = ["-fecha"]

    def __str__(self):
        return f"Transferencia #{self.pk}: {self.punto_origen} → {self.punto_destino}"


class TransferenciaItem(models.Model):
    transferencia = models.ForeignKey(
        Transferencia, verbose_name="transferencia", on_delete=models.CASCADE, related_name="items"
    )
    producto = models.ForeignKey(
        "catalogo.Producto", verbose_name="producto", on_delete=models.PROTECT, related_name="transferencia_items"
    )
    cantidad = models.PositiveIntegerField("cantidad")

    class Meta:
        verbose_name = "ítem de transferencia"
        verbose_name_plural = "ítems de transferencia"

    def __str__(self):
        return f"{self.cantidad}× {self.producto}"

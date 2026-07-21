from django.conf import settings
from django.db import models


class StockPunto(models.Model):
    """Cantidad disponible de un producto en un punto. Uno por (producto, punto)."""

    producto = models.ForeignKey(
        "catalogo.Producto", verbose_name="producto", on_delete=models.CASCADE, related_name="stocks"
    )
    punto = models.ForeignKey(
        "puntos.Punto", verbose_name="punto", on_delete=models.CASCADE, related_name="stocks"
    )
    cantidad = models.PositiveIntegerField("cantidad", default=0)
    stock_minimo = models.PositiveIntegerField("stock mínimo", default=0)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "stock por punto"
        verbose_name_plural = "stock por punto"
        constraints = [
            models.UniqueConstraint(
                fields=["producto", "punto"], name="stock_unico_por_producto_punto"
            )
        ]

    def __str__(self):
        return f"{self.producto} @ {self.punto}: {self.cantidad}"

    @property
    def bajo_minimo(self):
        return self.stock_minimo > 0 and self.cantidad <= self.stock_minimo


class MovimientoStock(models.Model):
    """
    Kardex: cada variación de stock queda registrada. `cantidad` es el delta
    con signo (positivo suma, negativo resta) y `resultante` es el saldo
    después de aplicar el movimiento.
    """

    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Ingreso de mercadería"
        SALIDA = "salida", "Salida"
        AJUSTE = "ajuste", "Ajuste"
        VENTA = "venta", "Venta"
        TRANSFERENCIA_ENTRADA = "transf_in", "Transferencia (entrada)"
        TRANSFERENCIA_SALIDA = "transf_out", "Transferencia (salida)"

    producto = models.ForeignKey(
        "catalogo.Producto", verbose_name="producto", on_delete=models.PROTECT, related_name="movimientos"
    )
    punto = models.ForeignKey(
        "puntos.Punto", verbose_name="punto", on_delete=models.PROTECT, related_name="movimientos"
    )
    tipo = models.CharField("tipo", max_length=12, choices=Tipo.choices)
    cantidad = models.IntegerField("cantidad (delta)")
    resultante = models.PositiveIntegerField("saldo resultante")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="movimientos_stock",
    )
    nota = models.CharField("nota", max_length=255, blank=True)
    fecha = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "movimiento de stock"
        verbose_name_plural = "movimientos de stock"
        ordering = ["-fecha"]

    def __str__(self):
        signo = "+" if self.cantidad >= 0 else ""
        return f"{self.get_tipo_display()} {signo}{self.cantidad} · {self.producto}"

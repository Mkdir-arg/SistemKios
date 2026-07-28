from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.ofertas.models import redondear


class Venta(models.Model):
    class Estado(models.TextChoices):
        CONFIRMADA = "confirmada", "Confirmada"
        ANULADA = "anulada", "Anulada"

    punto = models.ForeignKey(
        "puntos.Punto", verbose_name="punto", on_delete=models.PROTECT, related_name="ventas"
    )
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="vendedor", on_delete=models.PROTECT, related_name="ventas"
    )
    jornada = models.ForeignKey(
        "caja.Jornada", verbose_name="jornada", on_delete=models.PROTECT, related_name="ventas"
    )
    fecha = models.DateTimeField("fecha", auto_now_add=True)
    total = models.DecimalField("total", max_digits=12, decimal_places=2)
    descuento_total = models.DecimalField(
        "descuento por ofertas", max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    estado = models.CharField("estado", max_length=10, choices=Estado.choices, default=Estado.CONFIRMADA)

    class Meta:
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        ordering = ["-fecha"]

    def __str__(self):
        return f"Venta #{self.pk} · ${self.total}"

    @property
    def total_lista(self):
        """Lo que habría salido sin ofertas."""
        return self.total + self.descuento_total


class DetalleVenta(models.Model):
    """
    Una línea de la venta. `precio_unitario` es el **precio de lista** del punto
    y `descuento` lo que quitó la oferta sobre la línea entera, así que
    `subtotal = precio_unitario × cantidad − descuento`.

    Se guarda así porque un «2 x $1500» no da un precio unitario parejo: con 5
    unidades, 4 entran en la promo y 1 va a precio de lista.
    """

    venta = models.ForeignKey(Venta, verbose_name="venta", on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(
        "catalogo.Producto", verbose_name="producto", on_delete=models.PROTECT, related_name="ventas_detalle"
    )
    cantidad = models.PositiveIntegerField("cantidad")
    precio_unitario = models.DecimalField("precio de lista", max_digits=12, decimal_places=2)
    descuento = models.DecimalField(
        "descuento", max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    oferta = models.ForeignKey(
        "ofertas.Oferta",
        verbose_name="oferta",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="detalles_venta",
        help_text="La oferta que más descontó en esta línea.",
    )
    subtotal = models.DecimalField("subtotal", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "detalle de venta"
        verbose_name_plural = "detalles de venta"

    def __str__(self):
        return f"{self.cantidad}× {self.producto}"

    @property
    def precio_promedio(self):
        """Lo que se pagó por unidad, promediando el descuento de la línea."""
        if not self.cantidad:
            return self.subtotal
        return redondear(self.subtotal / self.cantidad)


class Pago(models.Model):
    class Medio(models.TextChoices):
        EFECTIVO = "efectivo", "Efectivo"
        TARJETA = "tarjeta", "Tarjeta"
        TRANSFERENCIA = "transferencia", "Transferencia / QR"

    venta = models.ForeignKey(Venta, verbose_name="venta", on_delete=models.CASCADE, related_name="pagos")
    medio = models.CharField("medio", max_length=14, choices=Medio.choices)
    monto = models.DecimalField("monto", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "pago"
        verbose_name_plural = "pagos"

    def __str__(self):
        return f"{self.get_medio_display()}: ${self.monto}"

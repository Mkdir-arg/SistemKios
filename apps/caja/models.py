from decimal import Decimal

from django.conf import settings
from django.db import models


class Jornada(models.Model):
    """
    Turno de trabajo de un vendedor. Al iniciar sesión se abre (con el monto
    inicial de la caja) y al terminar se cierra con arqueo. Ventas y movimientos
    de caja cuelgan de la jornada.
    """

    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        CERRADA = "cerrada", "Cerrada"

    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="vendedor", on_delete=models.PROTECT, related_name="jornadas"
    )
    punto = models.ForeignKey(
        "puntos.Punto", verbose_name="punto", on_delete=models.PROTECT, related_name="jornadas"
    )
    hora_inicio = models.DateTimeField("inicio", auto_now_add=True)
    hora_fin = models.DateTimeField("fin", null=True, blank=True)
    monto_inicial = models.DecimalField("monto inicial", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    monto_final = models.DecimalField("monto final (arqueo)", max_digits=12, decimal_places=2, null=True, blank=True)
    estado = models.CharField("estado", max_length=8, choices=Estado.choices, default=Estado.ABIERTA)

    class Meta:
        verbose_name = "jornada"
        verbose_name_plural = "jornadas"
        ordering = ["-hora_inicio"]
        constraints = [
            # Un vendedor no puede tener dos jornadas abiertas a la vez.
            models.UniqueConstraint(
                fields=["vendedor"],
                condition=models.Q(estado="abierta"),
                name="una_jornada_abierta_por_vendedor",
            )
        ]

    def __str__(self):
        return f"Jornada #{self.pk} · {self.vendedor} @ {self.punto}"

    @property
    def abierta(self):
        return self.estado == self.Estado.ABIERTA


class MovimientoCaja(models.Model):
    """Ingreso o egreso de dinero de la caja durante la jornada (retiros, gastos)."""

    class Tipo(models.TextChoices):
        INGRESO = "ingreso", "Ingreso"
        EGRESO = "egreso", "Egreso"

    jornada = models.ForeignKey(
        Jornada, verbose_name="jornada", on_delete=models.CASCADE, related_name="movimientos_caja"
    )
    tipo = models.CharField("tipo", max_length=8, choices=Tipo.choices)
    monto = models.DecimalField("monto", max_digits=12, decimal_places=2)
    motivo = models.CharField("motivo", max_length=200, blank=True)
    fecha = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "movimiento de caja"
        verbose_name_plural = "movimientos de caja"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.get_tipo_display()} ${self.monto}"

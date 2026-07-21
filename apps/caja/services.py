"""Lógica de jornada y caja: abrir, registrar movimientos y cerrar con arqueo."""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.realtime import notificar_punto

from .models import Jornada, MovimientoCaja


class JornadaError(Exception):
    """Error de negocio de jornada (ya abierta, cerrada, etc.)."""


def jornada_abierta(vendedor):
    """Devuelve la jornada abierta del vendedor, o None."""
    return Jornada.objects.filter(vendedor=vendedor, estado=Jornada.Estado.ABIERTA).first()


@transaction.atomic
def abrir_jornada(*, vendedor, punto, monto_inicial=Decimal("0.00")):
    if jornada_abierta(vendedor):
        raise JornadaError("Ya tenés una jornada abierta.")
    if punto is None:
        raise JornadaError("No tenés un punto asignado para abrir la jornada.")
    jornada = Jornada.objects.create(
        vendedor=vendedor, punto=punto, monto_inicial=monto_inicial
    )
    transaction.on_commit(
        lambda: notificar_punto(
            punto.id, "jornada", estado="abierta",
            vendedor=vendedor.get_short_name() or vendedor.username,
        )
    )
    return jornada


def registrar_movimiento_caja(*, jornada, tipo, monto, motivo=""):
    if not jornada.abierta:
        raise JornadaError("La jornada está cerrada.")
    if monto <= 0:
        raise JornadaError("El monto debe ser mayor a 0.")
    return MovimientoCaja.objects.create(
        jornada=jornada, tipo=tipo, monto=monto, motivo=motivo
    )


def efectivo_esperado(jornada):
    """
    Efectivo que debería haber en la caja al cierre:
    monto inicial + ventas en efectivo + ingresos - egresos.
    """
    # Import diferido para evitar dependencia circular caja <-> ventas.
    from apps.ventas.models import Pago, Venta

    ventas_efectivo = (
        Pago.objects.filter(
            venta__jornada=jornada,
            venta__estado=Venta.Estado.CONFIRMADA,
            medio=Pago.Medio.EFECTIVO,
        ).aggregate(t=Sum("monto"))["t"]
        or Decimal("0.00")
    )
    ingresos = (
        jornada.movimientos_caja.filter(tipo=MovimientoCaja.Tipo.INGRESO).aggregate(t=Sum("monto"))["t"]
        or Decimal("0.00")
    )
    egresos = (
        jornada.movimientos_caja.filter(tipo=MovimientoCaja.Tipo.EGRESO).aggregate(t=Sum("monto"))["t"]
        or Decimal("0.00")
    )
    return jornada.monto_inicial + ventas_efectivo + ingresos - egresos


@transaction.atomic
def cerrar_jornada(*, jornada, monto_final):
    if not jornada.abierta:
        raise JornadaError("La jornada ya está cerrada.")
    esperado = efectivo_esperado(jornada)
    jornada.monto_final = monto_final
    jornada.hora_fin = timezone.now()
    jornada.estado = Jornada.Estado.CERRADA
    jornada.save(update_fields=["monto_final", "hora_fin", "estado"])
    transaction.on_commit(
        lambda: notificar_punto(
            jornada.punto_id, "jornada", estado="cerrada",
            vendedor=jornada.vendedor.get_short_name() or jornada.vendedor.username,
        )
    )
    return {
        "esperado": esperado,
        "contado": monto_final,
        "diferencia": monto_final - esperado,
    }

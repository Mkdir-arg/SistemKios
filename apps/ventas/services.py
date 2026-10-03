"""
Registro de ventas: cotiza en el servidor, descuenta stock (al confirmar) y
guarda los pagos.

El precio no llega del navegador: se resuelve con `ofertas.cotizar` a partir del
precio del punto y las ofertas vigentes. Lo único que manda el POS es qué
producto y cuántas unidades.
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.core.realtime import notificar_punto
from apps.ofertas.services import cotizar
from apps.stock.models import MovimientoStock
from apps.stock.services import aplicar_movimiento

from .models import DetalleVenta, Pago, Venta


class VentaError(Exception):
    """Error de negocio de una venta."""


def _pagos_netos(pagos, total):
    """
    Valida los pagos y devuelve `({medio: monto}, vuelto)` con lo que queda en la caja.

    Lo pagado tiene que alcanzar el total. Lo que sobra es el vuelto, y el vuelto sale del
    efectivo: se descuenta del pago en efectivo, porque esa plata vuelve al cliente y no
    es del negocio. Si el sobrante supera al efectivo (pagaron de más con tarjeta o
    transferencia), la venta se rechaza: no hay de dónde dar ese vuelto.
    Los pagos en 0 o negativos se ignoran; dos renglones del mismo medio se suman.
    """
    por_medio = {}
    for p in pagos:
        try:
            monto = Decimal(str(p.get("monto", "0")))
        except InvalidOperation:
            raise VentaError("Monto de pago inválido.")
        if not monto.is_finite() or monto <= 0:
            continue
        medio = p.get("medio")
        if medio not in Pago.Medio.values:
            raise VentaError("Medio de pago inválido.")
        por_medio[medio] = por_medio.get(medio, Decimal("0.00")) + monto

    pagado = sum(por_medio.values(), Decimal("0.00"))
    if pagado < total:
        raise VentaError("Lo pagado es menor al total de la venta.")

    vuelto = pagado - total
    efectivo = por_medio.get(Pago.Medio.EFECTIVO, Decimal("0.00"))
    if vuelto > efectivo:
        raise VentaError(
            "El vuelto sale del efectivo: lo pagado con tarjeta o transferencia "
            "no puede superar el total."
        )
    if vuelto:
        por_medio[Pago.Medio.EFECTIVO] = efectivo - vuelto
    return por_medio, vuelto


@transaction.atomic
def registrar_venta(*, jornada, usuario, items, pagos):
    """
    Crea una venta confirmada.

    items: [{producto_id, cantidad}, ...]
    pagos: [{medio, monto}, ...]  (puede haber varios -> pago mixto)

    El stock se descuenta acá, al confirmar (no en cada escaneo). Todo es
    atómico: si falta stock de un ítem, no se registra nada.

    Puede levantar `CotizacionError` (carrito vacío, producto sin precio en el
    punto, producto dado de baja) además de `VentaError`.
    """
    if not jornada or not jornada.abierta:
        raise VentaError("Necesitás una jornada abierta para vender.")

    cotizacion = cotizar(punto=jornada.punto, items=items)
    por_medio, vuelto = _pagos_netos(pagos, cotizacion.total)

    venta = Venta.objects.create(
        punto=jornada.punto,
        vendedor=usuario,
        jornada=jornada,
        total=cotizacion.total,
        descuento_total=cotizacion.descuento_total,
    )

    for linea in cotizacion.lineas:
        DetalleVenta.objects.create(
            venta=venta,
            producto=linea.producto,
            cantidad=linea.cantidad,
            precio_unitario=linea.precio_lista,
            descuento=linea.descuento,
            oferta=linea.oferta_principal,
            subtotal=linea.subtotal,
        )
        # Los servicios (recargas, SUBE) no llevan stock: no se descuenta nada.
        if not linea.producto.es_servicio:
            aplicar_movimiento(
                producto=linea.producto,
                punto=jornada.punto,
                tipo=MovimientoStock.Tipo.VENTA,
                delta=-linea.cantidad,
                usuario=usuario,
                nota=f"Venta #{venta.pk}",
            )

    for medio, monto in por_medio.items():
        if monto > 0:
            Pago.objects.create(venta=venta, medio=medio, monto=monto)
    venta.vuelto = vuelto  # no se guarda: el POS lo muestra mientras el cajero da el cambio

    transaction.on_commit(
        lambda: notificar_punto(
            venta.punto_id,
            "venta",
            venta_id=venta.id,
            total=str(venta.total),
            items=len(cotizacion.lineas),
            vendedor=usuario.get_short_name() or usuario.username,
        )
    )
    return venta

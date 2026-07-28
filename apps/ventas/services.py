"""
Registro de ventas: cotiza en el servidor, descuenta stock (al confirmar) y
guarda los pagos.

El precio no llega del navegador: se resuelve con `ofertas.cotizar` a partir del
precio del punto y las ofertas vigentes. Lo único que manda el POS es qué
producto y cuántas unidades.
"""
from decimal import Decimal

from django.db import transaction

from apps.core.realtime import notificar_punto
from apps.ofertas.services import cotizar
from apps.stock.models import MovimientoStock
from apps.stock.services import aplicar_movimiento

from .models import DetalleVenta, Pago, Venta


class VentaError(Exception):
    """Error de negocio de una venta."""


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

    # Validación de pagos: lo pagado no puede ser menor al total.
    pagado = sum((Decimal(str(p.get("monto", "0"))) for p in pagos), Decimal("0.00"))
    if pagado < cotizacion.total:
        raise VentaError("Lo pagado es menor al total de la venta.")

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

    for p in pagos:
        monto = Decimal(str(p.get("monto", "0")))
        if monto <= 0:
            continue
        Pago.objects.create(venta=venta, medio=p.get("medio"), monto=monto)

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

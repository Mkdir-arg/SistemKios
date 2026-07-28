"""Registro de ventas: valida, descuenta stock (al confirmar) y guarda pagos."""
from decimal import Decimal

from django.db import transaction

from apps.core.realtime import notificar_punto
from apps.catalogo.models import Producto
from apps.stock.models import MovimientoStock
from apps.stock.services import aplicar_movimiento

from .models import DetalleVenta, Pago, Venta


class VentaError(Exception):
    """Error de negocio de una venta."""


@transaction.atomic
def registrar_venta(*, jornada, usuario, items, pagos):
    """
    Crea una venta confirmada.

    items: [{producto_id, cantidad, precio_unitario}, ...]
    pagos: [{medio, monto}, ...]  (puede haber varios -> pago mixto)

    El stock se descuenta acá, al confirmar (no en cada escaneo). Todo es
    atómico: si falta stock de un ítem, no se registra nada.
    """
    if not jornada or not jornada.abierta:
        raise VentaError("Necesitás una jornada abierta para vender.")
    if not items:
        raise VentaError("El carrito está vacío.")

    # Total a partir de los ítems.
    total = Decimal("0.00")
    normalizados = []
    for item in items:
        producto = Producto.objects.filter(pk=item.get("producto_id"), activo=True).first()
        if producto is None:
            raise VentaError("Hay un producto inexistente en el carrito.")
        cantidad = int(item.get("cantidad", 0))
        precio = Decimal(str(item.get("precio_unitario", "0")))
        if cantidad <= 0:
            raise VentaError(f"Cantidad inválida para «{producto}».")
        if precio < 0:
            raise VentaError(f"Precio inválido para «{producto}».")
        subtotal = precio * cantidad
        total += subtotal
        normalizados.append((producto, cantidad, precio, subtotal))

    # Validación de pagos: lo pagado no puede ser menor al total.
    pagado = sum((Decimal(str(p.get("monto", "0"))) for p in pagos), Decimal("0.00"))
    if pagado < total:
        raise VentaError("Lo pagado es menor al total de la venta.")

    venta = Venta.objects.create(
        punto=jornada.punto, vendedor=usuario, jornada=jornada, total=total
    )

    for producto, cantidad, precio, subtotal in normalizados:
        DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=precio,
            subtotal=subtotal,
        )
        # Los servicios (recargas, SUBE) no llevan stock: no se descuenta nada.
        if not producto.es_servicio:
            aplicar_movimiento(
                producto=producto,
                punto=jornada.punto,
                tipo=MovimientoStock.Tipo.VENTA,
                delta=-cantidad,
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
            items=len(normalizados),
            vendedor=usuario.get_short_name() or usuario.username,
        )
    )
    return venta

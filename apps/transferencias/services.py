"""Transferencia de stock entre puntos: salida en origen, entrada en destino."""
from django.db import transaction

from apps.catalogo.models import Producto
from apps.stock.models import MovimientoStock
from apps.stock.services import aplicar_movimiento

from .models import Transferencia, TransferenciaItem


class TransferenciaError(Exception):
    """Error de negocio de una transferencia."""


@transaction.atomic
def crear_transferencia(*, origen, destino, usuario, items):
    """
    items: [{producto_id, cantidad}, ...]

    Cada ítem descuenta stock en `origen` y lo suma en `destino`, todo atómico:
    si falta stock de algún ítem en el origen, no se transfiere nada.
    """
    if origen is None or destino is None:
        raise TransferenciaError("Elegí el punto de origen y el de destino.")
    if origen.pk == destino.pk:
        raise TransferenciaError("El origen y el destino deben ser distintos.")
    if not items:
        raise TransferenciaError("Agregá al menos un producto.")

    transferencia = Transferencia.objects.create(
        punto_origen=origen, punto_destino=destino, usuario=usuario
    )

    for item in items:
        producto = Producto.objects.filter(pk=item.get("producto_id")).first()
        if producto is None:
            raise TransferenciaError("Hay un producto inexistente en la transferencia.")
        cantidad = int(item.get("cantidad", 0))
        if cantidad <= 0:
            raise TransferenciaError(f"Cantidad inválida para «{producto}».")

        nota = f"Transferencia #{transferencia.pk}"
        # Salida del origen (puede lanzar StockInsuficiente -> rollback total).
        aplicar_movimiento(
            producto=producto, punto=origen, tipo=MovimientoStock.Tipo.TRANSFERENCIA_SALIDA,
            delta=-cantidad, usuario=usuario, nota=f"{nota} → {destino}",
        )
        # Entrada al destino.
        aplicar_movimiento(
            producto=producto, punto=destino, tipo=MovimientoStock.Tipo.TRANSFERENCIA_ENTRADA,
            delta=cantidad, usuario=usuario, nota=f"{nota} ← {origen}",
        )
        TransferenciaItem.objects.create(
            transferencia=transferencia, producto=producto, cantidad=cantidad
        )

    return transferencia

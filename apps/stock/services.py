"""
Lógica de negocio del stock. Toda variación pasa por `aplicar_movimiento`,
que actualiza el saldo de forma atómica y deja el registro en el kardex.
"""
from django.db import transaction

from .models import MovimientoStock, StockPunto


class StockInsuficiente(Exception):
    """Se intentó restar más stock del disponible."""


@transaction.atomic
def aplicar_movimiento(*, producto, punto, tipo, delta, usuario=None, nota=""):
    """
    Aplica un movimiento de stock y devuelve (stock_punto, movimiento).

    `delta` es la variación con signo (por ejemplo +10 para un ingreso).
    Bloquea la fila de StockPunto para evitar condiciones de carrera entre cajas.
    """
    if delta == 0:
        raise ValueError("El movimiento no puede ser de cantidad 0.")

    stock, _ = StockPunto.objects.select_for_update().get_or_create(
        producto=producto, punto=punto
    )

    nuevo = stock.cantidad + delta
    if nuevo < 0:
        raise StockInsuficiente(
            f"Stock insuficiente de «{producto}» en {punto}: "
            f"hay {stock.cantidad} y se intentó restar {abs(delta)}."
        )

    stock.cantidad = nuevo
    stock.save(update_fields=["cantidad", "actualizado"])

    movimiento = MovimientoStock.objects.create(
        producto=producto,
        punto=punto,
        tipo=tipo,
        cantidad=delta,
        resultante=nuevo,
        usuario=usuario,
        nota=nota,
    )
    return stock, movimiento


def ingresar_stock(*, producto, punto, cantidad, usuario=None, nota=""):
    """Atajo para el ingreso de mercadería (entrada positiva)."""
    if cantidad <= 0:
        raise ValueError("La cantidad a ingresar debe ser mayor a 0.")
    return aplicar_movimiento(
        producto=producto,
        punto=punto,
        tipo=MovimientoStock.Tipo.ENTRADA,
        delta=cantidad,
        usuario=usuario,
        nota=nota,
    )

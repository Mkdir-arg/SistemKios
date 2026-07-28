"""
Motor de ofertas: dado un punto y un carrito, resuelve los precios finales.

Es la única fuente de verdad del precio de una venta. El POS lo usa para
mostrar y `ventas.registrar_venta` para grabar; el navegador nunca decide un
precio.

Resolución cuando varias ofertas alcanzan al mismo producto: se aplica la que
más le conviene al cliente. En cada vuelta se elige la oferta que más ahorra
con las unidades que quedan libres, se consumen esas unidades y se repite hasta
que ninguna pueda armar un grupo completo. A igual ahorro gana la oferta más
antigua, así el resultado es siempre el mismo para el mismo carrito.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from apps.catalogo.models import PrecioPunto, Producto

from .models import CERO, Oferta, redondear


class CotizacionError(Exception):
    """El carrito no se puede cotizar (producto de baja, sin precio, etc.)."""


@dataclass
class OfertaAplicada:
    """Una oferta que entró en una línea, con lo que aportó de descuento."""

    oferta: Oferta
    veces: int
    descuento: Decimal

    @property
    def etiqueta(self):
        if self.veces == 1:
            return self.oferta.etiqueta
        return f"{self.veces}× {self.oferta.etiqueta}"


@dataclass
class Linea:
    """Una línea del carrito ya cotizada."""

    producto: Producto
    cantidad: int
    precio_lista: Decimal
    descuento: Decimal = CERO
    ofertas: list = field(default_factory=list)

    @property
    def total_lista(self):
        return redondear(self.precio_lista * self.cantidad)

    @property
    def subtotal(self):
        return redondear(self.total_lista - self.descuento)

    @property
    def precio_promedio(self):
        """Lo que termina pagando por unidad (un 2x$1500 no da precio parejo)."""
        return redondear(self.subtotal / self.cantidad)

    @property
    def tiene_oferta(self):
        return bool(self.ofertas)

    @property
    def oferta_principal(self):
        """La oferta que más descontó en esta línea; es la que se guarda en la venta."""
        if not self.ofertas:
            return None
        return self.ofertas[0].oferta

    def a_dict(self):
        return {
            "producto_id": self.producto.pk,
            "nombre": self.producto.nombre,
            "cantidad": self.cantidad,
            "precio_lista": str(self.precio_lista),
            "precio_promedio": str(self.precio_promedio),
            "descuento": str(self.descuento),
            "subtotal": str(self.subtotal),
            "ofertas": [
                {
                    "id": a.oferta.pk,
                    "nombre": a.oferta.nombre,
                    "etiqueta": a.etiqueta,
                    "veces": a.veces,
                    "descuento": str(a.descuento),
                }
                for a in self.ofertas
            ],
        }


@dataclass
class Cotizacion:
    """El carrito completo con sus precios resueltos."""

    punto: object
    lineas: list

    @property
    def total_lista(self):
        return redondear(sum((l.total_lista for l in self.lineas), CERO))

    @property
    def descuento_total(self):
        return redondear(sum((l.descuento for l in self.lineas), CERO))

    @property
    def total(self):
        return redondear(self.total_lista - self.descuento_total)

    @property
    def cantidad_total(self):
        return sum(l.cantidad for l in self.lineas)

    @property
    def tiene_ofertas(self):
        return any(l.ofertas for l in self.lineas)

    def a_dict(self):
        return {
            "lineas": [l.a_dict() for l in self.lineas],
            "total_lista": str(self.total_lista),
            "descuento_total": str(self.descuento_total),
            "total": str(self.total),
            "cantidad_total": self.cantidad_total,
        }


def cotizar(*, punto, items, fecha=None):
    """
    Cotiza un carrito en un punto y devuelve una `Cotizacion`.

    items: [{"producto_id": 1, "cantidad": 2}, ...] (también acepta
    {"producto": <Producto>, ...}). Los precios que venga trayendo el ítem se
    ignoran: el precio sale de `PrecioPunto` y los descuentos de las ofertas
    vigentes.
    """
    pedido, montos = _normalizar(items)
    productos = _traer_productos(pedido)
    precios = _traer_precios(punto, productos, montos)
    ofertas = _ofertas_candidatas(punto, pedido, fecha)
    veces, aportes = _resolver(ofertas, pedido, precios)
    return _armar(punto, pedido, productos, precios, ofertas, veces, aportes)


def ofertas_vigentes(punto, fecha=None):
    """Ofertas que corren hoy en un punto (para mostrárselas al vendedor)."""
    return (
        Oferta.objects.vigentes(punto=punto, fecha=fecha)
        .prefetch_related("items__producto")
        .order_by("nombre")
    )


# --- pasos internos ---------------------------------------------------------


def _normalizar(items):
    """
    {producto_id: cantidad} sumando repetidos y respetando el orden del carrito.
    Devuelve además {producto_id: monto} para los servicios (precio variable que
    ingresa el vendedor).
    """
    pedido = {}
    montos = {}
    for item in items or []:
        producto = item.get("producto")
        producto_id = producto.pk if producto is not None else item.get("producto_id")
        if producto_id is None:
            raise CotizacionError("Hay un ítem sin producto en el carrito.")
        try:
            producto_id = int(producto_id)
            cantidad = int(item.get("cantidad", 0))
        except (TypeError, ValueError):
            raise CotizacionError("Hay un ítem con datos inválidos en el carrito.")
        if cantidad <= 0:
            raise CotizacionError("Las cantidades tienen que ser mayores a 0.")
        pedido[producto_id] = pedido.get(producto_id, 0) + cantidad
        monto = item.get("monto")
        if monto not in (None, ""):
            try:
                montos[producto_id] = Decimal(str(monto))
            except (InvalidOperation, TypeError, ValueError):
                raise CotizacionError("Hay un servicio con un monto inválido.")
    if not pedido:
        raise CotizacionError("El carrito está vacío.")
    return pedido, montos


def _traer_productos(pedido):
    productos = {p.pk: p for p in Producto.objects.filter(pk__in=pedido)}
    if len(productos) != len(pedido):
        raise CotizacionError("Hay un producto inexistente en el carrito.")
    inactivos = [p.nombre for p in productos.values() if not p.activo]
    if inactivos:
        raise CotizacionError(f"«{inactivos[0]}» ya no está disponible.")
    return productos


def _traer_precios(punto, productos, montos=None):
    """
    Precio de lista por producto en el punto.

    Los servicios (recargas, SUBE) no usan `PrecioPunto`: su precio es el monto
    que ingresó el vendedor + el costo del producto (la comisión / ganancia).
    """
    montos = montos or {}
    precios = {}
    normales = {}
    for pk, p in productos.items():
        if p.es_servicio:
            precios[pk] = redondear(montos.get(pk, CERO) + (p.costo or CERO))
        else:
            normales[pk] = p

    de_punto = dict(
        PrecioPunto.objects.filter(
            punto=punto, producto_id__in=normales
        ).values_list("producto_id", "precio_venta")
    )
    sin_precio = [p.nombre for pk, p in normales.items() if pk not in de_punto]
    if sin_precio:
        raise CotizacionError(f"«{sin_precio[0]}» no tiene precio en {punto}.")
    precios.update(de_punto)
    return precios


def _ofertas_candidatas(punto, pedido, fecha):
    """
    Ofertas vigentes en el punto que podrían aplicar: si al grupo le falta algún
    producto que no está en el carrito, ya se descarta acá.
    """
    qs = (
        Oferta.objects.vigentes(punto=punto, fecha=fecha)
        .filter(items__producto_id__in=pedido)
        .prefetch_related("items")
        .distinct()
    )
    candidatas = []
    for oferta in qs:
        items = list(oferta.items.all())
        if items and all(i.producto_id in pedido for i in items):
            candidatas.append(oferta)
    return candidatas


def _resolver(ofertas, pedido, precios):
    """
    Aplica ofertas de a un grupo, siempre la que más ahorra, hasta que no queden
    unidades libres para armar ninguna.

    Devuelve (veces, aportes): cuántos grupos entraron por oferta y cuánto
    descuento aportó cada oferta a cada producto — {(oferta_pk, producto_id): $}.
    """
    libres = dict(pedido)
    veces = defaultdict(int)
    aportes = defaultdict(lambda: CERO)
    if not ofertas:
        return veces, aportes

    grupos = {o.pk: [(i.producto_id, i.cantidad) for i in o.items.all()] for o in ofertas}
    # El ahorro de un grupo no cambia entre vueltas: se calcula una sola vez.
    descuentos = {o.pk: o.descuento_del_grupo(precios) for o in ofertas}

    # Cada grupo consume al menos una unidad, así que el carrito acota las vueltas.
    for _ in range(sum(pedido.values())):
        mejor = None
        for oferta in ofertas:
            descuento = descuentos[oferta.pk]
            if descuento <= 0:
                continue
            tope = oferta.veces_max_por_venta
            if tope and veces[oferta.pk] >= tope:
                continue
            if any(libres.get(pk, 0) < cant for pk, cant in grupos[oferta.pk]):
                continue
            # Más ahorro primero; a igual ahorro, la oferta más antigua.
            clave = (-descuento, oferta.pk)
            if mejor is None or clave < mejor[0]:
                mejor = (clave, oferta, descuento)
        if mejor is None:
            break

        _, oferta, descuento = mejor
        grupo = grupos[oferta.pk]
        for producto_id, cantidad in grupo:
            libres[producto_id] -= cantidad
        veces[oferta.pk] += 1
        for producto_id, parte in _repartir(descuento, grupo, precios).items():
            aportes[(oferta.pk, producto_id)] += parte
    return veces, aportes


def _repartir(descuento, grupo, precios):
    """
    Reparte el descuento de un grupo entre sus productos, en proporción a lo que
    cada uno aporta al precio de lista (un combo descuenta sobre dos líneas).

    El resto del redondeo va al producto que más pesa, para que la suma de las
    líneas dé exactamente el total.
    """
    contribuciones = sorted(
        ((producto_id, precios[producto_id] * cantidad) for producto_id, cantidad in grupo),
        key=lambda c: (-c[1], c[0]),
    )
    lista = sum((monto for _, monto in contribuciones), CERO)
    principal = contribuciones[0][0]
    if lista <= 0:
        # Precio de lista 0: no hay proporción posible, va todo al primero.
        return {principal: descuento} | {pk: CERO for pk, _ in contribuciones[1:]}

    reparto = {}
    asignado = CERO
    for producto_id, monto in contribuciones[1:]:
        parte = redondear(descuento * monto / lista)
        reparto[producto_id] = parte
        asignado += parte
    reparto[principal] = redondear(descuento - asignado)
    return reparto


def _armar(punto, pedido, productos, precios, ofertas, veces, aportes):
    por_pk = {o.pk: o for o in ofertas}
    lineas = []
    for producto_id, cantidad in pedido.items():
        linea = Linea(
            producto=productos[producto_id],
            cantidad=cantidad,
            precio_lista=precios[producto_id],
        )
        for oferta_pk, aplicaciones in veces.items():
            aporte = aportes.get((oferta_pk, producto_id), CERO)
            if aplicaciones and aporte > 0:
                linea.ofertas.append(
                    OfertaAplicada(
                        oferta=por_pk[oferta_pk],
                        veces=aplicaciones,
                        descuento=redondear(aporte),
                    )
                )
        linea.ofertas.sort(key=lambda a: (-a.descuento, a.oferta.pk))
        linea.descuento = redondear(sum((a.descuento for a in linea.ofertas), CERO))
        lineas.append(linea)
    return Cotizacion(punto=punto, lineas=lineas)

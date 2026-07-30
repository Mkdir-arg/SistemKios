import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.catalogo.models import (
    Categoria,
    CodigoBarras,
    PrecioPunto,
    Producto,
    margen_desde_precio,
)
from apps.puntos.models import Punto
from apps.transferencias.services import TransferenciaError, crear_transferencia

from .models import StockPunto
from .services import StockInsuficiente, ingresar_stock


# --- Helpers ----------------------------------------------------------------

def _resolver_punto(request, punto_id=None):
    """
    Devuelve la ubicación de trabajo. El vendedor siempre opera en su punto;
    el Super Admin elige una (parámetro `punto`) y, si no elige, va al Depósito.
    """
    user = request.user
    if user.es_vendedor:
        return user.punto
    if punto_id:
        return Punto.objects.filter(pk=punto_id, activo=True).first()
    return Punto.get_deposito()


def _payload_producto(producto, punto):
    """
    Datos del producto + su stock en la ubicación seleccionada, el total general
    y el desglose por ubicación (Depósito y cada punto).
    """
    stock_map = {
        s.punto_id: s.cantidad
        for s in StockPunto.objects.filter(producto=producto)
    }
    total = sum(stock_map.values())
    desglose = [
        {"nombre": u.nombre, "es_deposito": u.es_deposito, "cantidad": stock_map.get(u.id, 0)}
        for u in Punto.objects.filter(activo=True)  # Depósito primero (ordering del modelo)
    ]
    precio = producto.precio_en(punto)
    return {
        "id": producto.id,
        "nombre": producto.nombre,
        "categoria": producto.categoria.nombre if producto.categoria else "",
        "codigo": producto.codigo_principal,
        "imagen": producto.imagen_url,
        "ubicacion": punto.nombre,
        "es_deposito": punto.es_deposito,
        "stock_actual": stock_map.get(punto.id, 0),
        "total": total,
        "desglose": desglose,
        "precio": str(precio) if precio is not None else None,
    }


def _parse_decimal(valor, campo):
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"El campo «{campo}» no es un número válido.")


def _matriz_stock():
    """
    Devuelve (ubicaciones, filas) para la tabla de stock:
    una fila por producto activo con su cantidad en cada ubicación y el total.
    """
    ubicaciones = list(Punto.objects.filter(activo=True))  # Depósito primero
    por_prod = {}
    for r in StockPunto.objects.filter(producto__activo=True).values(
        "producto_id", "punto_id", "cantidad"
    ):
        por_prod.setdefault(r["producto_id"], {})[r["punto_id"]] = r["cantidad"]

    filas = []
    productos = (
        Producto.objects.filter(activo=True, es_servicio=False)  # los servicios no llevan stock
        .select_related("categoria")
        .prefetch_related("codigos")
        .order_by("nombre")
    )
    for p in productos:
        codigos = list(p.codigos.all())
        codigo = next((c.codigo for c in codigos if c.principal), codigos[0].codigo if codigos else "")
        pm = por_prod.get(p.id, {})
        cantidades = [pm.get(u.id, 0) for u in ubicaciones]
        filas.append(
            {
                "id": p.id,
                "nombre": p.nombre,
                "codigo": codigo,
                "categoria": p.categoria.nombre if p.categoria else "",
                "imagen": p.imagen_url,
                "cantidades": cantidades,
                "total": sum(cantidades),
            }
        )
    return ubicaciones, filas


# --- Vistas -----------------------------------------------------------------

@ensure_csrf_cookie
@login_required
def ingreso(request):
    """
    Pantalla única del stock: ver la tabla, sumar mercadería con el lector y
    transferir entre ubicaciones (esto último, solo el Super Admin).
    """
    user = request.user
    deposito = Punto.get_deposito()
    context = {
        "categorias": Categoria.objects.all(),
        "ubicaciones": Punto.objects.filter(activo=True),  # Depósito primero
        "punto_fijo": user.punto if user.es_vendedor else None,
        "es_super_admin": user.es_super_admin,
        "deposito_id": deposito.id,
        # Transferir es del Super Admin, y necesita al menos dos ubicaciones.
        "puede_transferir": user.es_super_admin and Punto.objects.filter(activo=True).count() > 1,
    }
    return render(request, "stock/ingreso.html", context)


@login_required
def buscar(request):
    """Busca un producto por código de barras en el punto indicado."""
    codigo = request.GET.get("codigo", "").strip()
    punto = _resolver_punto(request, request.GET.get("punto"))

    if punto is None:
        return JsonResponse({"error": "Elegí un punto antes de escanear."}, status=400)
    if not codigo:
        return JsonResponse({"error": "Código vacío."}, status=400)

    cb = CodigoBarras.objects.select_related("producto", "producto__categoria").filter(codigo=codigo).first()
    if cb is None:
        return JsonResponse({"found": False, "codigo": codigo})
    if cb.producto.es_servicio:
        return JsonResponse({"found": True, "servicio": True, "nombre": cb.producto.nombre})
    return JsonResponse({"found": True, "producto": _payload_producto(cb.producto, punto)})


@login_required
@require_POST
def agregar(request):
    """Suma stock a un producto existente (ingreso de mercadería)."""
    data = json.loads(request.body or "{}")
    punto = _resolver_punto(request, data.get("punto"))
    if punto is None:
        return JsonResponse({"error": "Elegí un punto antes de agregar."}, status=400)

    producto = get_object_or_404(Producto, pk=data.get("producto_id"))
    try:
        cantidad = int(data.get("cantidad", 1))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Cantidad inválida."}, status=400)
    if cantidad <= 0:
        return JsonResponse({"error": "La cantidad debe ser mayor a 0."}, status=400)

    stock, _ = ingresar_stock(
        producto=producto, punto=punto, cantidad=cantidad, usuario=request.user
    )
    return JsonResponse(
        {
            "ok": True,
            "producto": _payload_producto(producto, punto),
            "agregado": cantidad,
        }
    )


@login_required
@require_POST
def alta(request):
    """Alta rápida de un producto que no existía, con su stock inicial."""
    data = json.loads(request.body or "{}")
    punto = _resolver_punto(request, data.get("punto"))
    if punto is None:
        return JsonResponse({"error": "Elegí un punto antes de dar de alta."}, status=400)

    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not codigo:
        return JsonResponse({"error": "Falta el código de barras."}, status=400)
    if not nombre:
        return JsonResponse({"error": "Poné un nombre al producto."}, status=400)
    if CodigoBarras.objects.filter(codigo=codigo).exists():
        return JsonResponse({"error": "Ese código ya está usado por otro producto."}, status=409)

    try:
        costo = _parse_decimal(data.get("costo") or 0, "costo")
        precio_venta = data.get("precio_venta")
        precio_venta = _parse_decimal(precio_venta, "precio de venta") if precio_venta not in (None, "") else None
        cantidad = int(data.get("cantidad") or 0)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    if cantidad < 0:
        return JsonResponse({"error": "La cantidad no puede ser negativa."}, status=400)

    with transaction.atomic():
        producto = Producto.objects.create(
            nombre=nombre,
            categoria_id=data.get("categoria") or None,
            costo=costo,
        )
        CodigoBarras.objects.create(producto=producto, codigo=codigo, principal=True)
        if precio_venta is not None:
            # El precio se aplica a los puntos de venta (no al Depósito).
            margen = margen_desde_precio(producto.precio_base, precio_venta)
            for pv in Punto.objects.filter(activo=True, es_deposito=False):
                PrecioPunto.objects.update_or_create(
                    producto=producto,
                    punto=pv,
                    defaults={"precio_venta": precio_venta, "margen": margen},
                )
        if cantidad > 0:
            ingresar_stock(
                producto=producto,
                punto=punto,
                cantidad=cantidad,
                usuario=request.user,
                nota="Alta rápida",
            )

    return JsonResponse({"ok": True, "creado": True, "producto": _payload_producto(producto, punto)})


@login_required
@require_POST
def transferir(request):
    """
    Mueve stock de la ubicación de trabajo a otra. Solo Super Admin: repartir
    mercadería es decisión del dueño, no del que atiende.
    """
    if not request.user.es_super_admin:
        return JsonResponse({"error": "Las transferencias las maneja el Super Admin."}, status=403)

    data = json.loads(request.body or "{}")
    origen = _resolver_punto(request, data.get("origen"))
    destino = Punto.objects.filter(pk=data.get("destino"), activo=True).first()
    if origen is None:
        return JsonResponse({"error": "Elegí la ubicación de origen."}, status=400)
    if destino is None:
        return JsonResponse({"error": "Elegí la ubicación de destino."}, status=400)

    try:
        transferencia = crear_transferencia(
            origen=origen, destino=destino, usuario=request.user, items=data.get("items", [])
        )
    except (TransferenciaError, StockInsuficiente) as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    items = list(transferencia.items.all())
    return JsonResponse(
        {
            "ok": True,
            "transferencia_id": transferencia.id,
            "origen": origen.nombre,
            "destino": destino.nombre,
            "productos": len(items),
            "unidades": sum(i.cantidad for i in items),
        }
    )


@login_required
def tabla(request):
    """Datos de la tabla de stock (para la consulta y el ingreso en vivo)."""
    ubicaciones, filas = _matriz_stock()
    return JsonResponse(
        {
            "ubicaciones": [
                {"nombre": u.nombre, "es_deposito": u.es_deposito} for u in ubicaciones
            ],
            "filas": filas,
        }
    )

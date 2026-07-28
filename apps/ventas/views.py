import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from apps.caja.services import jornada_abierta
from apps.catalogo.models import CodigoBarras
from apps.ofertas.services import CotizacionError
from apps.ofertas.services import cotizar as cotizar_carrito
from apps.stock.models import StockPunto
from apps.stock.services import StockInsuficiente

from .services import VentaError, registrar_venta

CARRITO_VACIO = {
    "lineas": [],
    "total_lista": "0.00",
    "descuento_total": "0.00",
    "total": "0.00",
    "cantidad_total": 0,
}


@ensure_csrf_cookie
@login_required
def pos(request):
    user = request.user
    if not user.es_vendedor:
        messages.info(request, "Solo los vendedores pueden vender.")
        return redirect("core:home")
    jornada = jornada_abierta(user)
    if not jornada:
        messages.info(request, "Abrí tu jornada para empezar a vender.")
        return redirect("caja:abrir")
    return render(request, "ventas/pos.html", {"jornada": jornada})


@login_required
def buscar(request):
    """Busca un producto por código para la venta (precio de lista y stock del punto)."""
    jornada = jornada_abierta(request.user)
    if not jornada:
        return JsonResponse({"error": "Sin jornada abierta."}, status=400)
    codigo = request.GET.get("codigo", "").strip()
    if not codigo:
        return JsonResponse({"error": "Código vacío."}, status=400)

    cb = CodigoBarras.objects.select_related("producto").filter(codigo=codigo).first()
    if cb is None or not cb.producto.activo:
        return JsonResponse({"found": False, "codigo": codigo})

    producto = cb.producto
    precio = producto.precio_en(jornada.punto)
    if precio is None and not producto.es_servicio:
        # Sin precio en el punto no se puede vender: antes se iba al carrito en $0.
        # (Los servicios no tienen precio fijo: el vendedor ingresa el monto.)
        return JsonResponse(
            {"error": f"«{producto.nombre}» no tiene precio en {jornada.punto}."},
            status=400,
        )

    stock = StockPunto.objects.filter(producto=producto, punto=jornada.punto).first()
    return JsonResponse(
        {
            "found": True,
            "producto": {
                "id": producto.id,
                "nombre": producto.nombre,
                "precio": str(precio) if precio is not None else "0",
                "stock": stock.cantidad if stock else 0,
                "es_servicio": producto.es_servicio,
                "comision": str(producto.costo),  # en servicios, el costo es la comisión
                "imagen": producto.imagen_url,
            },
        }
    )


@login_required
@require_POST
def cotizar(request):
    """
    Precio del carrito según el punto y las ofertas vigentes.

    El POS lo llama en cada cambio del carrito: es la única fuente del total que
    ve el cliente, y el mismo cálculo con el que después se graba la venta.
    """
    jornada = jornada_abierta(request.user)
    if not jornada:
        return JsonResponse({"error": "Sin jornada abierta."}, status=400)

    data = json.loads(request.body or "{}")
    items = data.get("items", [])
    if not items:
        return JsonResponse(CARRITO_VACIO)

    try:
        cotizacion = cotizar_carrito(punto=jornada.punto, items=items)
    except CotizacionError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(cotizacion.a_dict())


@login_required
@require_POST
def confirmar(request):
    jornada = jornada_abierta(request.user)
    if not jornada:
        return JsonResponse({"error": "Sin jornada abierta."}, status=400)
    data = json.loads(request.body or "{}")
    try:
        venta = registrar_venta(
            jornada=jornada,
            usuario=request.user,
            items=data.get("items", []),
            pagos=data.get("pagos", []),
        )
    except (VentaError, CotizacionError, StockInsuficiente) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(
        {
            "ok": True,
            "venta_id": venta.id,
            "total": str(venta.total),
            "descuento": str(venta.descuento_total),
        }
    )

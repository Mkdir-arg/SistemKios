import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from apps.caja.services import jornada_abierta
from apps.catalogo.models import CodigoBarras
from apps.stock.models import StockPunto
from apps.stock.services import StockInsuficiente

from .services import VentaError, registrar_venta


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
    """Busca un producto por código para la venta (precio y stock del punto)."""
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
    stock = StockPunto.objects.filter(producto=producto, punto=jornada.punto).first()
    precio = producto.precio_en(jornada.punto)
    return JsonResponse(
        {
            "found": True,
            "producto": {
                "id": producto.id,
                "nombre": producto.nombre,
                "precio": str(precio) if precio is not None else "0",
                "stock": stock.cantidad if stock else 0,
            },
        }
    )


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
    except (VentaError, StockInsuficiente) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"ok": True, "venta_id": venta.id, "total": str(venta.total)})

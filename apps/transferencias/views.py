import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from apps.catalogo.models import CodigoBarras
from apps.puntos.models import Punto
from apps.stock.models import StockPunto
from apps.stock.services import StockInsuficiente

from .services import TransferenciaError, crear_transferencia


def _solo_admin(request):
    if not request.user.es_super_admin:
        messages.info(request, "Las transferencias las maneja el Super Admin.")
        return False
    return True


@ensure_csrf_cookie
@login_required
def nueva(request):
    if not _solo_admin(request):
        return redirect("core:home")
    return render(request, "transferencias/nueva.html", {"puntos": Punto.objects.filter(activo=True)})


@login_required
def buscar(request):
    if not request.user.es_super_admin:
        return JsonResponse({"error": "No autorizado."}, status=403)
    codigo = request.GET.get("codigo", "").strip()
    origen = Punto.objects.filter(pk=request.GET.get("origen")).first()
    if origen is None:
        return JsonResponse({"error": "Elegí el punto de origen."}, status=400)
    if not codigo:
        return JsonResponse({"error": "Código vacío."}, status=400)

    cb = CodigoBarras.objects.select_related("producto").filter(codigo=codigo).first()
    if cb is None:
        return JsonResponse({"found": False, "codigo": codigo})
    producto = cb.producto
    stock = StockPunto.objects.filter(producto=producto, punto=origen).first()
    return JsonResponse(
        {
            "found": True,
            "producto": {
                "id": producto.id,
                "nombre": producto.nombre,
                "codigo": producto.codigo_principal,
                "stock_origen": stock.cantidad if stock else 0,
            },
        }
    )


@login_required
@require_POST
def confirmar(request):
    if not request.user.es_super_admin:
        return JsonResponse({"error": "No autorizado."}, status=403)
    data = json.loads(request.body or "{}")
    origen = Punto.objects.filter(pk=data.get("origen")).first()
    destino = Punto.objects.filter(pk=data.get("destino")).first()
    try:
        transferencia = crear_transferencia(
            origen=origen, destino=destino, usuario=request.user, items=data.get("items", [])
        )
    except (TransferenciaError, StockInsuficiente) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"ok": True, "transferencia_id": transferencia.id})

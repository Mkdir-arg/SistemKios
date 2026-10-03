import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.core.formato import plata

from .models import MovimientoCaja
from .services import (
    JornadaError,
    abrir_jornada,
    cerrar_jornada,
    efectivo_esperado,
    jornada_abierta,
    registrar_movimiento_caja,
)


def _monto(valor):
    try:
        return Decimal(str(valor or "0"))
    except InvalidOperation:
        return None


@login_required
def abrir(request):
    user = request.user
    if not user.es_vendedor:
        messages.info(request, "Solo los vendedores abren jornada.")
        return redirect("core:home")
    if jornada_abierta(user):
        return redirect("caja:mi_jornada")
    if not user.punto:
        return render(request, "caja/abrir.html", {"sin_punto": True})

    if request.method == "POST":
        monto = _monto(request.POST.get("monto_inicial"))
        if monto is None or monto < 0:
            messages.error(request, "Monto inicial inválido.")
            return redirect("caja:abrir")
        try:
            abrir_jornada(vendedor=user, punto=user.punto, monto_inicial=monto)
        except JornadaError as exc:
            messages.error(request, str(exc))
            return redirect("caja:abrir")
        messages.success(request, "Jornada iniciada. ¡A vender!")
        return redirect("ventas:pos")

    return render(request, "caja/abrir.html", {})


@login_required
def mi_jornada(request):
    user = request.user
    if not user.es_vendedor:
        messages.info(request, "La jornada es de los vendedores.")
        return redirect("core:home")
    jornada = jornada_abierta(user)
    if not jornada:
        return redirect("caja:abrir")
    return render(
        request,
        "caja/mi_jornada.html",
        {
            "jornada": jornada,
            "esperado": efectivo_esperado(jornada),
            "movimientos": jornada.movimientos_caja.all(),
            "ventas_count": jornada.ventas.count(),
        },
    )


@login_required
@require_POST
def movimiento(request):
    user = request.user
    jornada = jornada_abierta(user)
    if not jornada:
        return JsonResponse({"error": "No tenés una jornada abierta."}, status=400)
    data = json.loads(request.body or "{}")
    monto = _monto(data.get("monto"))
    if monto is None:
        return JsonResponse({"error": "Monto inválido."}, status=400)
    try:
        registrar_movimiento_caja(
            jornada=jornada, tipo=data.get("tipo"), monto=monto, motivo=data.get("motivo", "")
        )
    except JornadaError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"ok": True, "esperado": str(efectivo_esperado(jornada))})


@login_required
@require_POST
def cerrar(request):
    user = request.user
    jornada = jornada_abierta(user)
    if not jornada:
        return redirect("caja:abrir")
    monto_final = _monto(request.POST.get("monto_final"))
    if monto_final is None or monto_final < 0:
        messages.error(request, "Monto contado inválido.")
        return redirect("caja:mi_jornada")
    resultado = cerrar_jornada(jornada=jornada, monto_final=monto_final)
    messages.success(
        request,
        f"Jornada cerrada. Esperado {plata(resultado['esperado'])}, contado {plata(resultado['contado'])}, "
        f"diferencia {plata(resultado['diferencia'])}.",
    )
    return redirect("core:home")

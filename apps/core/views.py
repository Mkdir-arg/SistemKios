from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.caja.models import Jornada
from apps.puntos.models import Punto
from apps.stock.models import StockPunto
from apps.ventas.models import Pago, Venta


def healthz(request):
    """Endpoint liviano para el healthcheck de la plataforma."""
    return HttpResponse("ok", content_type="text/plain")


@login_required
def home(request):
    """Pantalla principal tras el login; se adapta al rol."""
    context = {}
    if request.user.es_super_admin:
        context["puntos"] = Punto.objects.filter(activo=True)
    else:
        context["punto_fijo"] = request.user.punto
    return render(request, "core/dashboard.html", context)


@login_required
def reportes(request):
    """Reportes del negocio (solo Super Admin): ventas, stock y horas."""
    if not request.user.es_super_admin:
        messages.info(request, "Los reportes son del Super Admin.")
        return redirect("core:home")

    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    ventas = Venta.objects.filter(estado=Venta.Estado.CONFIRMADA)

    hoy_agg = ventas.filter(fecha__date=hoy).aggregate(total=Sum("total"), cant=Count("id"))
    mes_agg = ventas.filter(fecha__date__gte=inicio_mes).aggregate(total=Sum("total"), cant=Count("id"))

    por_punto = list(
        ventas.filter(fecha__date__gte=inicio_mes)
        .values("punto__nombre")
        .annotate(total=Sum("total"), cantidad=Count("id"))
        .order_by("-total")
    )
    tope_punto = max((p["total"] for p in por_punto), default=0) or 1

    medios_labels = dict(Pago.Medio.choices)
    medios = [
        {"label": medios_labels.get(m["medio"], m["medio"]), "total": m["total"]}
        for m in Pago.objects.filter(
            venta__estado=Venta.Estado.CONFIRMADA, venta__fecha__date__gte=inicio_mes
        ).values("medio").annotate(total=Sum("monto")).order_by("-total")
    ]

    bajo_minimo = (
        StockPunto.objects.filter(stock_minimo__gt=0, cantidad__lte=F("stock_minimo"))
        .select_related("producto", "punto")
        .order_by("cantidad")
    )

    # Horas trabajadas por vendedor en el mes.
    ahora = timezone.now()
    horas = {}
    for j in Jornada.objects.filter(hora_inicio__date__gte=inicio_mes).select_related("vendedor"):
        fin = j.hora_fin or ahora
        segundos = (fin - j.hora_inicio).total_seconds()
        clave = j.vendedor.get_short_name() or j.vendedor.username
        horas[clave] = horas.get(clave, 0) + segundos
    horas_vendedor = sorted(
        ({"vendedor": k, "horas": round(v / 3600, 1)} for k, v in horas.items()),
        key=lambda x: -x["horas"],
    )

    return render(
        request,
        "core/reportes.html",
        {
            "hoy_total": hoy_agg["total"] or 0,
            "hoy_cant": hoy_agg["cant"] or 0,
            "mes_total": mes_agg["total"] or 0,
            "mes_cant": mes_agg["cant"] or 0,
            "por_punto": por_punto,
            "tope_punto": tope_punto,
            "medios": medios,
            "bajo_minimo": bajo_minimo,
            "horas_vendedor": horas_vendedor,
        },
    )

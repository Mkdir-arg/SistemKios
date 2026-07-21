from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.puntos.models import Punto


@login_required
def home(request):
    """
    Pantalla principal tras el login. El contenido se adapta al rol:
    el Super Admin ve el panel de gestión; el Vendedor, su punto de trabajo.
    """
    context = {}
    if request.user.es_super_admin:
        context["puntos"] = Punto.objects.filter(activo=True)
    else:
        context["punto_fijo"] = request.user.punto
    return render(request, "core/dashboard.html", context)

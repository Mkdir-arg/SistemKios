from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    """
    Pantalla principal tras el login. El contenido se adapta al rol:
    el Super Admin ve el panel de gestión; el Vendedor, su punto de trabajo.
    Los módulos concretos llegan en las próximas fases.
    """
    return render(request, "core/dashboard.html")

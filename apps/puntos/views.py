from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import super_admin_required

from .forms import PuntoForm
from .models import Punto


@super_admin_required
def lista(request):
    puntos = Punto.objects.annotate(vendedores_count=Count("vendedores")).order_by("nombre")
    return render(request, "puntos/lista.html", {"puntos": puntos})


@super_admin_required
def crear(request):
    form = PuntoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Punto creado.")
        return redirect("puntos:lista")
    return render(request, "puntos/form.html", {"form": form, "titulo": "Nuevo punto"})


@super_admin_required
def editar(request, pk):
    punto = get_object_or_404(Punto, pk=pk)
    form = PuntoForm(request.POST or None, instance=punto)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Punto actualizado.")
        return redirect("puntos:lista")
    return render(request, "puntos/form.html", {"form": form, "titulo": f"Editar {punto.nombre}"})

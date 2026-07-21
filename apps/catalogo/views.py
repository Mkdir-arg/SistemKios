from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import super_admin_required
from apps.puntos.models import Punto

from .forms import ProductoForm
from .models import Categoria, CodigoBarras, PrecioPunto, Producto


@super_admin_required
def lista(request):
    productos = Producto.objects.select_related("categoria").prefetch_related("codigos").order_by("nombre")
    return render(request, "catalogo/lista.html", {"productos": productos})


def _guardar(request, producto=None):
    form = ProductoForm(request.POST or None, instance=producto)
    puntos = list(Punto.objects.filter(activo=True))

    # Valores para prefill (existentes o los recién enviados si hubo error).
    codigos = list(producto.codigos.values_list("codigo", flat=True)) if producto else []
    precios_val = {pp.punto_id: str(pp.precio_venta) for pp in producto.precios.all()} if producto else {}
    error = None

    if request.method == "POST":
        codigos = list(dict.fromkeys(c.strip() for c in request.POST.getlist("codigos") if c.strip()))
        precios_val = {p.id: request.POST.get(f"precio_{p.id}", "").strip() for p in puntos}

        if form.is_valid():
            # Validación de códigos.
            if not codigos:
                error = "Agregá al menos un código de barras."
            else:
                for c in codigos:
                    qs = CodigoBarras.objects.filter(codigo=c)
                    if producto:
                        qs = qs.exclude(producto=producto)
                    if qs.exists():
                        error = f"El código {c} ya está usado por otro producto."
                        break
            # Validación de precios.
            precios_dec = {}
            if not error:
                for p in puntos:
                    val = precios_val.get(p.id, "")
                    if val:
                        try:
                            precios_dec[p.id] = Decimal(val)
                        except InvalidOperation:
                            error = f"Precio inválido para {p.nombre}."
                            break

            if not error:
                with transaction.atomic():
                    prod = form.save(commit=False)
                    nueva = form.cleaned_data.get("nueva_categoria", "").strip()
                    if nueva:
                        prod.categoria, _ = Categoria.objects.get_or_create(nombre=nueva)
                    prod.save()

                    # Sincroniza códigos (borra los que se quitaron, agrega los nuevos).
                    prod.codigos.exclude(codigo__in=codigos).delete()
                    for c in codigos:
                        CodigoBarras.objects.update_or_create(codigo=c, defaults={"producto": prod})
                    prod.codigos.update(principal=False)
                    prod.codigos.filter(codigo=codigos[0]).update(principal=True)

                    # Sincroniza precios por punto.
                    for p in puntos:
                        if p.id in precios_dec:
                            PrecioPunto.objects.update_or_create(
                                producto=prod, punto=p, defaults={"precio_venta": precios_dec[p.id]}
                            )
                        else:
                            PrecioPunto.objects.filter(producto=prod, punto=p).delete()

                messages.success(request, "Producto guardado.")
                return redirect("catalogo:lista")

    contexto = {
        "form": form,
        "titulo": f"Editar {producto.nombre}" if producto else "Nuevo producto",
        "codigos": codigos or [""],
        "precios": [{"punto": p, "valor": precios_val.get(p.id, "")} for p in puntos],
        "error": error,
    }
    return render(request, "catalogo/form.html", contexto)


@super_admin_required
def crear(request):
    return _guardar(request)


@super_admin_required
def editar(request, pk):
    return _guardar(request, get_object_or_404(Producto, pk=pk))

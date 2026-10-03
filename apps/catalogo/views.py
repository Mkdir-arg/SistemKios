from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.contrib import messages
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from PIL import Image

from apps.core.decorators import super_admin_required
from apps.puntos.models import Punto

from .forms import ProductoForm
from .models import (
    Categoria,
    CodigoBarras,
    PrecioPunto,
    Producto,
    margen_desde_precio,
    precio_con_margen,
)


@super_admin_required
def lista(request):
    productos = Producto.objects.select_related("categoria").prefetch_related("codigos").order_by("nombre")
    return render(request, "catalogo/lista.html", {"productos": productos})


def _achicar_imagen(archivo, max_lado=800):
    """
    Devuelve la imagen subida achicada si es muy grande (evita fotos enormes).

    Trabaja en memoria, antes de guardar: así sirve para cualquier almacenamiento (disco en
    local, Supabase Storage en producción). Si algo falla, devuelve el archivo tal cual.
    """
    try:
        img = Image.open(archivo)
        formato = img.format or "JPEG"
        if max(img.size) <= max_lado:
            archivo.seek(0)
            return archivo
        img.thumbnail((max_lado, max_lado))
        if formato == "JPEG" and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        salida = BytesIO()
        img.save(salida, format=formato)
        return ContentFile(salida.getvalue(), name=archivo.name)
    except Exception:
        archivo.seek(0)
        return archivo


def _guardar(request, producto=None):
    form = ProductoForm(request.POST or None, request.FILES or None, instance=producto)
    puntos = list(Punto.objects.filter(activo=True))

    # Valores para prefill (existentes o los recién enviados si hubo error).
    codigos = list(producto.codigos.values_list("codigo", flat=True)) if producto else []
    precios_val, margenes_val = {}, {}
    if producto:
        for pp in producto.precios.all():
            precios_val[pp.punto_id] = str(pp.precio_venta)
            margenes_val[pp.punto_id] = "" if pp.margen is None else str(pp.margen)
    error = None

    if request.method == "POST":
        codigos = list(dict.fromkeys(c.strip() for c in request.POST.getlist("codigos") if c.strip()))
        precios_val = {p.id: request.POST.get(f"precio_{p.id}", "").strip() for p in puntos}
        margenes_val = {p.id: request.POST.get(f"margen_{p.id}", "").strip() for p in puntos}

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
            # Precios por punto: el precio final lo define el margen % sobre el
            # precio base (costo + IVA). El precio que llega del form es solo el
            # calculado en pantalla; acá se recalcula para no confiar en el navegador.
            precios_dec, margenes_dec = {}, {}
            if not error:
                base = form.instance.precio_base
                for p in puntos:
                    val = precios_val.get(p.id, "")
                    mar = margenes_val.get(p.id, "")
                    try:
                        margen = Decimal(mar) if mar else None
                    except InvalidOperation:
                        error = f"Margen inválido para {p.nombre}."
                        break
                    if margen is not None and base:
                        precio = precio_con_margen(base, margen)
                    elif val:
                        # Producto sin costo: no hay margen posible, se respeta el precio ya cargado.
                        try:
                            precio = Decimal(val)
                        except InvalidOperation:
                            error = f"Precio inválido para {p.nombre}."
                            break
                    else:
                        continue  # Sin precio: no se vende en este punto.
                    if precio < 0:
                        error = f"El margen deja el precio en negativo en {p.nombre}."
                        break
                    precios_dec[p.id] = precio
                    margenes_dec[p.id] = margen if margen is not None else margen_desde_precio(base, precio)

            if not error:
                with transaction.atomic():
                    prod = form.save(commit=False)
                    nueva = form.cleaned_data.get("nueva_categoria", "").strip()
                    if nueva:
                        prod.categoria, _ = Categoria.objects.get_or_create(nombre=nueva)
                    if "imagen" in request.FILES:
                        prod.imagen = _achicar_imagen(request.FILES["imagen"])
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
                                producto=prod,
                                punto=p,
                                defaults={
                                    "precio_venta": precios_dec[p.id],
                                    "margen": margenes_dec[p.id],
                                },
                            )
                        else:
                            PrecioPunto.objects.filter(producto=prod, punto=p).delete()

                messages.success(request, "Producto guardado.")
                return redirect("catalogo:lista")

    contexto = {
        "form": form,
        "titulo": f"Editar {producto.nombre}" if producto else "Nuevo producto",
        "codigos": codigos or [""],
        "precios": [
            {"punto": p, "valor": precios_val.get(p.id, ""), "margen": margenes_val.get(p.id, "")}
            for p in puntos
        ],
        "error": error,
    }
    return render(request, "catalogo/form.html", contexto)


@super_admin_required
def crear(request):
    return _guardar(request)


@super_admin_required
def editar(request, pk):
    return _guardar(request, get_object_or_404(Producto, pk=pk))


@super_admin_required
@require_POST
def eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    nombre = producto.nombre
    try:
        producto.delete()
        messages.success(request, f"«{nombre}» eliminado.")
    except ProtectedError:
        # Tiene ventas o movimientos: no se puede borrar sin romper el historial.
        # Se desactiva (deja de aparecer en ventas, stock y catálogo activo).
        producto.activo = False
        producto.save(update_fields=["activo"])
        messages.warning(
            request,
            f"«{nombre}» tiene ventas o movimientos registrados, así que no se puede "
            "borrar. Lo marqué como inactivo: deja de aparecer al vender y en el stock.",
        )
    return redirect("catalogo:lista")

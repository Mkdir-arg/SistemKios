from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "stock"

urlpatterns = [
    # Pantalla única de Stock: ver la tabla + sumar mercadería con el lector.
    path("stock/", views.ingreso, name="ingreso"),
    path("stock/buscar/", views.buscar, name="buscar"),
    path("stock/agregar/", views.agregar, name="agregar"),
    path("stock/alta/", views.alta, name="alta"),
    path("stock/tabla/", views.tabla, name="tabla"),
    # Compatibilidad con la URL anterior.
    path("stock/ingreso/", RedirectView.as_view(pattern_name="stock:ingreso", permanent=False)),
]

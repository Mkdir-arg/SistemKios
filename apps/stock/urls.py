from django.urls import path

from . import views

app_name = "stock"

urlpatterns = [
    path("stock/", views.consulta, name="consulta"),
    path("stock/tabla/", views.tabla, name="tabla"),
    path("stock/ingreso/", views.ingreso, name="ingreso"),
    path("stock/ingreso/buscar/", views.buscar, name="buscar"),
    path("stock/ingreso/agregar/", views.agregar, name="agregar"),
    path("stock/ingreso/alta/", views.alta, name="alta"),
]

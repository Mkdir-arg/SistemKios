from django.urls import path

from . import views

app_name = "ventas"

urlpatterns = [
    path("vender/", views.pos, name="pos"),
    path("vender/buscar/", views.buscar, name="buscar"),
    path("vender/cotizar/", views.cotizar, name="cotizar"),
    path("vender/confirmar/", views.confirmar, name="confirmar"),
]

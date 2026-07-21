from django.urls import path

from . import views

app_name = "transferencias"

urlpatterns = [
    path("transferencias/nueva/", views.nueva, name="nueva"),
    path("transferencias/buscar/", views.buscar, name="buscar"),
    path("transferencias/confirmar/", views.confirmar, name="confirmar"),
]

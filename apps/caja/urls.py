from django.urls import path

from . import views

app_name = "caja"

urlpatterns = [
    path("jornada/abrir/", views.abrir, name="abrir"),
    path("jornada/", views.mi_jornada, name="mi_jornada"),
    path("jornada/movimiento/", views.movimiento, name="movimiento"),
    path("jornada/cerrar/", views.cerrar, name="cerrar"),
]

from django.urls import path

from . import views

app_name = "puntos"

urlpatterns = [
    path("puntos/", views.lista, name="lista"),
    path("puntos/nuevo/", views.crear, name="crear"),
    path("puntos/<int:pk>/editar/", views.editar, name="editar"),
]

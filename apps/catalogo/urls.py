from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("productos/", views.lista, name="lista"),
    path("productos/nuevo/", views.crear, name="crear"),
    path("productos/<int:pk>/editar/", views.editar, name="editar"),
]

from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("ingresar/", views.SistemLoginView.as_view(), name="login"),
    path("salir/", LogoutView.as_view(), name="logout"),
    path("usuarios/", views.usuarios_lista, name="usuarios_lista"),
    path("usuarios/nuevo/", views.usuario_crear, name="usuario_crear"),
    path("usuarios/<int:pk>/editar/", views.usuario_editar, name="usuario_editar"),
]

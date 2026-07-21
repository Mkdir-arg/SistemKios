from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("ingresar/", views.SistemLoginView.as_view(), name="login"),
    path("salir/", LogoutView.as_view(), name="logout"),
]

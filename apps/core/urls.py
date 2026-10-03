from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("healthz/", views.healthz, name="healthz"),
    path("reportes/", views.reportes, name="reportes"),
    path("tiempo-real/token/", views.tiempo_real_token, name="tiempo_real_token"),
]

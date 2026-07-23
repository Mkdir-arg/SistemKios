from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("panel-django/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.puntos.urls")),
    path("", include("apps.catalogo.urls")),
    path("", include("apps.stock.urls")),
    path("", include("apps.caja.urls")),
    path("", include("apps.ventas.urls")),
    path("", include("apps.transferencias.urls")),
    # Servimos los archivos subidos (imágenes de productos). En este proyecto
    # no hay nginx: los sirve la app (tráfico interno bajo).
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]

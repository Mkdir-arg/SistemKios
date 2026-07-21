from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("panel-django/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("", include("apps.accounts.urls")),
]

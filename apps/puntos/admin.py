from django.contrib import admin

from .models import Punto


@admin.register(Punto)
class PuntoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "direccion", "activo", "creado"]
    list_filter = ["activo"]
    search_fields = ["nombre", "direccion"]

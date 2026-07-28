from django.contrib import admin

from .models import Oferta, OfertaItem


class OfertaItemInline(admin.TabularInline):
    model = OfertaItem
    extra = 1
    autocomplete_fields = ["producto"]


@admin.register(Oferta)
class OfertaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "tipo", "valor", "alcance", "desde", "hasta", "estado"]
    list_filter = ["tipo", "alcance", "activa", "puntos"]
    search_fields = ["nombre"]
    filter_horizontal = ["puntos"]
    inlines = [OfertaItemInline]

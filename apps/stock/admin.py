from django.contrib import admin

from .models import MovimientoStock, StockPunto


@admin.register(StockPunto)
class StockPuntoAdmin(admin.ModelAdmin):
    list_display = ["producto", "punto", "cantidad", "stock_minimo", "bajo_minimo", "actualizado"]
    list_filter = ["punto"]
    search_fields = ["producto__nombre", "producto__codigos__codigo"]
    autocomplete_fields = ["producto", "punto"]


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ["fecha", "tipo", "producto", "punto", "cantidad", "resultante", "usuario"]
    list_filter = ["tipo", "punto"]
    search_fields = ["producto__nombre", "producto__codigos__codigo"]
    autocomplete_fields = ["producto", "punto"]
    readonly_fields = ["fecha"]
    date_hierarchy = "fecha"

from django.contrib import admin

from .models import DetalleVenta, Pago, Venta


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ["producto", "cantidad", "precio_unitario", "subtotal"]


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    readonly_fields = ["medio", "monto"]


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ["id", "fecha", "punto", "vendedor", "total", "estado"]
    list_filter = ["estado", "punto"]
    date_hierarchy = "fecha"
    inlines = [DetalleVentaInline, PagoInline]

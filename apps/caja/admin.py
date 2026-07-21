from django.contrib import admin

from .models import Jornada, MovimientoCaja


class MovimientoCajaInline(admin.TabularInline):
    model = MovimientoCaja
    extra = 0


@admin.register(Jornada)
class JornadaAdmin(admin.ModelAdmin):
    list_display = ["id", "vendedor", "punto", "estado", "hora_inicio", "hora_fin", "monto_inicial", "monto_final"]
    list_filter = ["estado", "punto"]
    search_fields = ["vendedor__username"]
    date_hierarchy = "hora_inicio"
    inlines = [MovimientoCajaInline]


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(admin.ModelAdmin):
    list_display = ["fecha", "jornada", "tipo", "monto", "motivo"]
    list_filter = ["tipo"]

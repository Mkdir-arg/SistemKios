from django.contrib import admin

from .models import Transferencia, TransferenciaItem


class TransferenciaItemInline(admin.TabularInline):
    model = TransferenciaItem
    extra = 0


@admin.register(Transferencia)
class TransferenciaAdmin(admin.ModelAdmin):
    list_display = ["id", "fecha", "punto_origen", "punto_destino", "usuario", "estado"]
    list_filter = ["punto_origen", "punto_destino"]
    date_hierarchy = "fecha"
    inlines = [TransferenciaItemInline]

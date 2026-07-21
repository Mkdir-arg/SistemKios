from django.contrib import admin

from .models import Categoria, CodigoBarras, PrecioPunto, Producto


class CodigoBarrasInline(admin.TabularInline):
    model = CodigoBarras
    extra = 1


class PrecioPuntoInline(admin.TabularInline):
    model = PrecioPunto
    extra = 1
    autocomplete_fields = ["punto"]


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "categoria", "codigo_principal", "costo", "activo"]
    list_filter = ["activo", "categoria"]
    search_fields = ["nombre", "codigos__codigo"]
    inlines = [CodigoBarrasInline, PrecioPuntoInline]


@admin.register(CodigoBarras)
class CodigoBarrasAdmin(admin.ModelAdmin):
    list_display = ["codigo", "producto", "principal"]
    search_fields = ["codigo", "producto__nombre"]

from decimal import ROUND_HALF_UP, Decimal

from django.db import models

CENTAVO = Decimal("0.01")
CIEN = Decimal("100")


def precio_con_margen(base, margen):
    """Precio final = precio base + `margen` %."""
    return (base * (Decimal("1") + Decimal(margen) / CIEN)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def margen_desde_precio(base, precio):
    """Margen % que hay que aplicarle al `base` para llegar a `precio`."""
    if not base:
        return None
    return ((Decimal(precio) / base - Decimal("1")) * CIEN).quantize(CENTAVO, rounding=ROUND_HALF_UP)


class Categoria(models.Model):
    nombre = models.CharField("nombre", max_length=80, unique=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """Producto del catálogo. Es unitario (se vende de a unidades enteras)."""

    nombre = models.CharField("nombre", max_length=160)
    categoria = models.ForeignKey(
        Categoria,
        verbose_name="categoría",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="productos",
    )
    costo = models.DecimalField(
        "costo (referencia)", max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    alicuota_iva = models.DecimalField(
        "alícuota IVA (%)", max_digits=5, decimal_places=2, default=Decimal("21.00")
    )
    imagen = models.ImageField(
        "imagen", upload_to="productos/", blank=True, null=True
    )
    es_servicio = models.BooleanField(
        "es un servicio (sin stock)",
        default=False,
        help_text="Recargas, SUBE y similares: se cobran pero no llevan stock.",
    )
    activo = models.BooleanField("activo", default=True)
    creado = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def imagen_url(self):
        return self.imagen.url if self.imagen else ""

    @property
    def precio_base(self):
        """Costo + IVA. Es la base sobre la que cada punto aplica su margen %."""
        iva = self.alicuota_iva or Decimal("0")
        costo = self.costo or Decimal("0")
        return (costo * (Decimal("1") + iva / CIEN)).quantize(CENTAVO, rounding=ROUND_HALF_UP)

    @property
    def codigo_principal(self):
        codigo = self.codigos.filter(principal=True).first() or self.codigos.first()
        return codigo.codigo if codigo else ""

    def precio_en(self, punto):
        """Precio de venta en un punto, o None si todavía no tiene precio ahí."""
        precio = self.precios.filter(punto=punto).first()
        return precio.precio_venta if precio else None


class CodigoBarras(models.Model):
    """Un producto puede tener varios códigos de barras (pack, unidad, etc.)."""

    producto = models.ForeignKey(
        Producto, verbose_name="producto", on_delete=models.CASCADE, related_name="codigos"
    )
    codigo = models.CharField("código", max_length=64, unique=True, db_index=True)
    principal = models.BooleanField("principal", default=False)

    class Meta:
        verbose_name = "código de barras"
        verbose_name_plural = "códigos de barras"
        ordering = ["-principal", "codigo"]

    def __str__(self):
        return self.codigo


class PrecioPunto(models.Model):
    """Precio de venta de un producto en un punto concreto."""

    producto = models.ForeignKey(
        Producto, verbose_name="producto", on_delete=models.CASCADE, related_name="precios"
    )
    punto = models.ForeignKey(
        "puntos.Punto", verbose_name="punto", on_delete=models.CASCADE, related_name="precios"
    )
    margen = models.DecimalField(
        "margen (%)",
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Porcentaje que se aplica sobre el precio base (costo + IVA) del producto.",
    )
    precio_venta = models.DecimalField("precio de venta", max_digits=12, decimal_places=2)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "precio por punto"
        verbose_name_plural = "precios por punto"
        constraints = [
            models.UniqueConstraint(
                fields=["producto", "punto"], name="precio_unico_por_producto_punto"
            )
        ]

    def __str__(self):
        return f"{self.producto} @ {self.punto}: ${self.precio_venta}"

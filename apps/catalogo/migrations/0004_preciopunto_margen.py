from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations, models

CENTAVO = Decimal("0.01")
CIEN = Decimal("100")


def calcular_margenes(apps, schema_editor):
    """Deduce el margen % de los precios que ya estaban cargados a mano."""
    PrecioPunto = apps.get_model("catalogo", "PrecioPunto")
    for pp in PrecioPunto.objects.select_related("producto").iterator():
        producto = pp.producto
        iva = producto.alicuota_iva or Decimal("0")
        costo = producto.costo or Decimal("0")
        base = (costo * (Decimal("1") + iva / CIEN)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        if not base:
            continue
        pp.margen = ((pp.precio_venta / base - Decimal("1")) * CIEN).quantize(
            CENTAVO, rounding=ROUND_HALF_UP
        )
        pp.save(update_fields=["margen"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0003_producto_es_servicio"),
    ]

    operations = [
        migrations.AddField(
            model_name="preciopunto",
            name="margen",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Porcentaje que se aplica sobre el precio base (costo + IVA) del producto.",
                max_digits=6,
                null=True,
                verbose_name="margen (%)",
            ),
        ),
        migrations.RunPython(calcular_margenes, migrations.RunPython.noop),
    ]

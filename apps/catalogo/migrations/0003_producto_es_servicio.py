from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0002_producto_imagen"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="es_servicio",
            field=models.BooleanField(
                default=False,
                help_text="Recargas, SUBE y similares: se cobran pero no llevan stock.",
                verbose_name="es un servicio (sin stock)",
            ),
        ),
    ]

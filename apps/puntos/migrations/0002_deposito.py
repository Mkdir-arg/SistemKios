from django.db import migrations, models


def crear_deposito(apps, schema_editor):
    Punto = apps.get_model("puntos", "Punto")
    if not Punto.objects.filter(es_deposito=True).exists():
        Punto.objects.create(nombre="Depósito", es_deposito=True, activo=True)


def borrar_deposito(apps, schema_editor):
    Punto = apps.get_model("puntos", "Punto")
    Punto.objects.filter(es_deposito=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("puntos", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="punto",
            name="es_deposito",
            field=models.BooleanField(default=False, verbose_name="es depósito"),
        ),
        migrations.AlterModelOptions(
            name="punto",
            options={
                "ordering": ["-es_deposito", "nombre"],
                "verbose_name": "punto",
                "verbose_name_plural": "puntos",
            },
        ),
        migrations.AddConstraint(
            model_name="punto",
            constraint=models.UniqueConstraint(
                condition=models.Q(("es_deposito", True)),
                fields=("es_deposito",),
                name="un_solo_deposito",
            ),
        ),
        migrations.RunPython(crear_deposito, borrar_deposito),
    ]

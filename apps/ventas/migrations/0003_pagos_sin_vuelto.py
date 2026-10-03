"""
Les saca el vuelto a los pagos de las ventas ya registradas (REQ-VEN-006).

Hasta acá `registrar_venta` guardaba cada pago por lo que entregó el cliente, vuelto
incluido: una venta de $3600 cobrada con $5000 quedaba como $5000 en efectivo, y eso
inflaba el efectivo esperado del arqueo y el reporte de medios de pago.

En cada venta donde lo pagado supera el total, el sobrante se descuenta primero del
efectivo (de ahí sale el vuelto) y, si no alcanza, de los otros medios, de mayor a menor.
Los pagos que quedan en 0 se borran. Es idempotente: una venta bien guardada no se toca.
"""
from decimal import Decimal

from django.db import migrations
from django.db.models import F, Sum


def sacar_vuelto_de_los_pagos(apps, schema_editor):
    Venta = apps.get_model("ventas", "Venta")
    Pago = apps.get_model("ventas", "Pago")

    ventas = Venta.objects.annotate(pagado=Sum("pagos__monto")).filter(pagado__gt=F("total"))
    for venta in ventas:
        sobrante = venta.pagado - venta.total
        pagos = list(Pago.objects.filter(venta_id=venta.pk))
        # Primero el efectivo; después el resto, de mayor a menor.
        pagos.sort(key=lambda p: (p.medio != "efectivo", -p.monto, p.pk))
        for pago in pagos:
            if sobrante <= 0:
                break
            quita = min(pago.monto, sobrante)
            sobrante -= quita
            pago.monto -= quita
            if pago.monto <= Decimal("0"):
                pago.delete()
            else:
                pago.save(update_fields=["monto"])


class Migration(migrations.Migration):

    dependencies = [
        ("ventas", "0002_detalleventa_descuento_detalleventa_oferta_and_more"),
    ]

    operations = [
        # Sin vuelta atrás: el vuelto no se guardó en ningún lado, no hay cómo reponerlo.
        migrations.RunPython(sacar_vuelto_de_los_pagos, migrations.RunPython.noop),
    ]

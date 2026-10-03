"""Tests del registro de ventas: pagos y vuelto (REQ-VEN-006)."""
from decimal import Decimal
from importlib import import_module

from django.apps import apps as django_apps
from django.test import TestCase

from apps.accounts.models import User
from apps.caja.services import abrir_jornada, efectivo_esperado
from apps.catalogo.models import PrecioPunto, Producto
from apps.puntos.models import Punto
from apps.stock.services import ingresar_stock

from .models import Pago, Venta
from .services import VentaError, registrar_venta


def D(valor):
    return Decimal(str(valor))


class BaseVentas(TestCase):
    """Un punto, un vendedor con la jornada abierta y un producto de $3600."""

    def setUp(self):
        self.punto = Punto.objects.create(nombre="Palermo")
        self.vendedor = User.objects.create_user(
            "vendedor", password="x", rol=User.Rol.VENDEDOR, punto=self.punto
        )
        self.coca = Producto.objects.create(nombre="Coca 500")
        PrecioPunto.objects.create(producto=self.coca, punto=self.punto, precio_venta=D(3600))
        ingresar_stock(producto=self.coca, punto=self.punto, cantidad=10)
        self.jornada = abrir_jornada(vendedor=self.vendedor, punto=self.punto, monto_inicial=D(1000))

    def vender(self, pagos, cantidad=1):
        return registrar_venta(
            jornada=self.jornada,
            usuario=self.vendedor,
            items=[{"producto_id": self.coca.pk, "cantidad": cantidad}],
            pagos=[{"medio": m, "monto": str(v)} for m, v in pagos],
        )

    def pagos_de(self, venta):
        return {p.medio: p.monto for p in venta.pagos.all()}


class VueltoTest(BaseVentas):
    def test_el_vuelto_no_se_guarda_en_el_efectivo(self):
        venta = self.vender([("efectivo", 5000)])
        self.assertEqual(self.pagos_de(venta), {"efectivo": D(3600)})
        self.assertEqual(venta.vuelto, D(1400))

    def test_el_esperado_en_caja_no_cuenta_el_vuelto(self):
        self.vender([("efectivo", 5000)])
        self.assertEqual(efectivo_esperado(self.jornada), D(1000) + D(3600))

    def test_pago_exacto_no_tiene_vuelto(self):
        venta = self.vender([("efectivo", 3600)])
        self.assertEqual(self.pagos_de(venta), {"efectivo": D(3600)})
        self.assertEqual(venta.vuelto, D(0))

    def test_pago_mixto_el_vuelto_sale_del_efectivo(self):
        venta = self.vender([("tarjeta", 2000), ("efectivo", 2000)])
        self.assertEqual(self.pagos_de(venta), {"tarjeta": D(2000), "efectivo": D(1600)})
        self.assertEqual(venta.vuelto, D(400))

    def test_si_el_vuelto_se_come_todo_el_efectivo_no_queda_pago_en_cero(self):
        venta = self.vender([("tarjeta", 3600), ("efectivo", 500)])
        self.assertEqual(self.pagos_de(venta), {"tarjeta": D(3600)})
        self.assertEqual(venta.vuelto, D(500))

    def test_no_se_puede_dar_vuelto_de_un_pago_que_no_es_efectivo(self):
        with self.assertRaisesMessage(VentaError, "vuelto"):
            self.vender([("tarjeta", 5000)])
        self.assertFalse(Venta.objects.exists())

    def test_ni_siquiera_si_hay_algo_de_efectivo(self):
        with self.assertRaisesMessage(VentaError, "vuelto"):
            self.vender([("transferencia", 4000), ("efectivo", 100)])

    def test_dos_renglones_del_mismo_medio_se_suman(self):
        venta = self.vender([("efectivo", 2000), ("efectivo", 2000)])
        self.assertEqual(self.pagos_de(venta), {"efectivo": D(3600)})
        self.assertEqual(venta.pagos.count(), 1)


class PagosInvalidosTest(BaseVentas):
    def test_pago_insuficiente(self):
        with self.assertRaisesMessage(VentaError, "menor al total"):
            self.vender([("efectivo", 3000)])

    def test_los_pagos_en_cero_o_negativos_se_ignoran(self):
        venta = self.vender([("efectivo", 3600), ("tarjeta", 0), ("transferencia", -50)])
        self.assertEqual(self.pagos_de(venta), {"efectivo": D(3600)})

    def test_medio_desconocido(self):
        with self.assertRaisesMessage(VentaError, "Medio de pago"):
            self.vender([("cheque", 3600)])

    def test_monto_que_no_es_numero(self):
        with self.assertRaisesMessage(VentaError, "Monto"):
            self.vender([("efectivo", "mucho")])


class MigracionPagosSinVueltoTest(BaseVentas):
    """La migración de datos les saca el vuelto a las ventas viejas."""

    def migrar(self):
        modulo = import_module("apps.ventas.migrations.0003_pagos_sin_vuelto")
        modulo.sacar_vuelto_de_los_pagos(django_apps, None)

    def venta_vieja(self, pagos, total=3600):
        # Como las guardaba el código anterior: los pagos tal cual los entregó el cliente.
        venta = Venta.objects.create(
            punto=self.punto, vendedor=self.vendedor, jornada=self.jornada, total=D(total)
        )
        for medio, monto in pagos:
            Pago.objects.create(venta=venta, medio=medio, monto=D(monto))
        return venta

    def test_descuenta_el_vuelto_del_efectivo(self):
        venta = self.venta_vieja([("efectivo", 5000)])
        self.migrar()
        self.assertEqual(self.pagos_de(venta), {"efectivo": D(3600)})

    def test_pago_mixto(self):
        venta = self.venta_vieja([("tarjeta", 2000), ("efectivo", 2000)])
        self.migrar()
        self.assertEqual(self.pagos_de(venta), {"tarjeta": D(2000), "efectivo": D(1600)})

    def test_borra_el_efectivo_que_queda_en_cero(self):
        venta = self.venta_vieja([("tarjeta", 3600), ("efectivo", 500)])
        self.migrar()
        self.assertEqual(self.pagos_de(venta), {"tarjeta": D(3600)})

    def test_sobrante_sin_efectivo_se_descuenta_de_los_otros_medios(self):
        # El código viejo aceptaba esto. La plata real es el total, no lo "pagado".
        venta = self.venta_vieja([("tarjeta", 5000)])
        self.migrar()
        self.assertEqual(self.pagos_de(venta), {"tarjeta": D(3600)})

    def test_no_toca_las_ventas_bien_guardadas(self):
        venta = self.venta_vieja([("tarjeta", 1600), ("efectivo", 2000)])
        self.migrar()
        self.assertEqual(self.pagos_de(venta), {"tarjeta": D(1600), "efectivo": D(2000)})

    def test_es_idempotente(self):
        venta = self.venta_vieja([("efectivo", 5000)])
        self.migrar()
        self.migrar()
        self.assertEqual(self.pagos_de(venta), {"efectivo": D(3600)})

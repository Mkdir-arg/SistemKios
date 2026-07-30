"""
Tests de la pantalla de Stock, que es donde también se transfiere
(ver docs/requerimientos/03-stock.md · REQ-STK-013).
"""
import json

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.catalogo.models import CodigoBarras, Producto
from apps.puntos.models import Punto
from apps.transferencias.models import Transferencia

from .models import MovimientoStock, StockPunto
from .services import ingresar_stock


class BaseStock(TestCase):
    """Depósito con mercadería, dos locales, un dueño y una vendedora."""

    def setUp(self):
        self.deposito = Punto.get_deposito()
        self.centro = Punto.objects.create(nombre="Kiosco Centro")
        self.norte = Punto.objects.create(nombre="Kiosco Norte")

        self.admin = User.objects.create_superuser("dueno", password="x")
        self.vendedora = User.objects.create_user(
            "ana", password="x", rol=User.Rol.VENDEDOR, punto=self.centro
        )

        self.coca = self._producto("Coca 500", "7790001", 48)
        self.alfajor = self._producto("Alfajor", "7790002", 30)

    def _producto(self, nombre, codigo, cantidad):
        producto = Producto.objects.create(nombre=nombre)
        CodigoBarras.objects.create(producto=producto, codigo=codigo, principal=True)
        ingresar_stock(producto=producto, punto=self.deposito, cantidad=cantidad)
        return producto

    def stock(self, producto, punto):
        fila = StockPunto.objects.filter(producto=producto, punto=punto).first()
        return fila.cantidad if fila else 0

    def transferir(self, cliente, origen, destino, items):
        return cliente.post(
            reverse("stock:transferir"),
            json.dumps(
                {
                    "origen": origen.pk if origen else None,
                    "destino": destino.pk if destino else None,
                    "items": [{"producto_id": p.pk, "cantidad": c} for p, c in items],
                }
            ),
            content_type="application/json",
        )

    def como_admin(self):
        self.client.force_login(self.admin)
        return self.client

    def como_vendedora(self):
        self.client.force_login(self.vendedora)
        return self.client


class PantallaTest(BaseStock):
    def test_el_super_admin_ve_las_dos_pestanas_y_el_selector(self):
        html = self.como_admin().get(reverse("stock:ingreso")).content.decode()
        self.assertIn("Sumar mercader", html)
        self.assertIn("Transferir", html)
        self.assertIn('id="ubicacion"', html)

    def test_la_vendedora_no_ve_transferir(self):
        html = self.como_vendedora().get(reverse("stock:ingreso")).content.decode()
        self.assertNotIn("Sumar mercader", html)  # sin pestañas, un solo flujo
        self.assertNotIn('id="ubicacion"', html)  # trabaja fijo en su punto


class TransferirTest(BaseStock):
    def test_mueve_el_stock_y_deja_un_solo_remito(self):
        r = self.transferir(
            self.como_admin(), self.deposito, self.centro,
            [(self.coca, 6), (self.alfajor, 12)],
        )
        self.assertEqual(r.status_code, 200)
        datos = r.json()
        self.assertEqual(datos["unidades"], 18)
        self.assertEqual(datos["productos"], 2)

        self.assertEqual(self.stock(self.coca, self.deposito), 42)
        self.assertEqual(self.stock(self.coca, self.centro), 6)
        self.assertEqual(self.stock(self.alfajor, self.deposito), 18)
        self.assertEqual(self.stock(self.alfajor, self.centro), 12)

        transferencia = Transferencia.objects.get(pk=datos["transferencia_id"])
        self.assertEqual(transferencia.items.count(), 2)
        self.assertEqual(transferencia.punto_origen, self.deposito)
        self.assertEqual(transferencia.punto_destino, self.centro)
        self.assertEqual(transferencia.usuario, self.admin)

    def test_deja_salida_y_entrada_en_el_kardex(self):
        self.transferir(self.como_admin(), self.deposito, self.centro, [(self.coca, 6)])
        salida = MovimientoStock.objects.get(
            producto=self.coca, punto=self.deposito,
            tipo=MovimientoStock.Tipo.TRANSFERENCIA_SALIDA,
        )
        entrada = MovimientoStock.objects.get(
            producto=self.coca, punto=self.centro,
            tipo=MovimientoStock.Tipo.TRANSFERENCIA_ENTRADA,
        )
        self.assertEqual(salida.cantidad, -6)
        self.assertEqual(salida.resultante, 42)
        self.assertEqual(entrada.cantidad, 6)
        self.assertEqual(entrada.resultante, 6)

    def test_si_falta_stock_de_un_item_no_mueve_nada(self):
        r = self.transferir(
            self.como_admin(), self.deposito, self.norte,
            [(self.coca, 1), (self.alfajor, 9999)],
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("insuficiente", r.json()["error"].lower())
        # Ni la Coca, que sí tenía stock, se movió.
        self.assertEqual(self.stock(self.coca, self.deposito), 48)
        self.assertEqual(self.stock(self.coca, self.norte), 0)
        self.assertFalse(Transferencia.objects.exists())

    def test_rechaza_lo_que_no_es_una_transferencia_valida(self):
        cliente = self.como_admin()
        casos = {
            "mismo origen y destino": (self.deposito, self.deposito, [(self.coca, 1)]),
            "sin destino": (self.deposito, None, [(self.coca, 1)]),
            "sin items": (self.deposito, self.centro, []),
            "cantidad en cero": (self.deposito, self.centro, [(self.coca, 0)]),
        }
        for caso, (origen, destino, items) in casos.items():
            with self.subTest(caso=caso):
                r = self.transferir(cliente, origen, destino, items)
                self.assertEqual(r.status_code, 400)
        self.assertFalse(Transferencia.objects.exists())


class PermisosTest(BaseStock):
    def test_la_vendedora_no_puede_transferir_ni_posteando_a_mano(self):
        ingresar_stock(producto=self.coca, punto=self.centro, cantidad=10)
        r = self.transferir(
            self.como_vendedora(), self.centro, self.norte, [(self.coca, 5)]
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.stock(self.coca, self.centro), 10)
        self.assertFalse(Transferencia.objects.exists())

    def test_el_endpoint_no_acepta_get(self):
        self.assertEqual(self.como_admin().get(reverse("stock:transferir")).status_code, 405)


class CompatibilidadTest(BaseStock):
    def test_el_link_viejo_de_transferencias_lleva_al_stock(self):
        r = self.como_admin().get(reverse("transferencias:nueva"))
        self.assertRedirects(r, reverse("stock:ingreso"))

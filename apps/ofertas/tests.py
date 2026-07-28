"""Tests del motor de ofertas (`services.cotizar`)."""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.catalogo.models import PrecioPunto, Producto
from apps.puntos.models import Punto

from .models import Oferta, OfertaItem
from .services import CotizacionError, cotizar


def D(valor):
    return Decimal(str(valor))


class BaseOfertas(TestCase):
    """Dos puntos y tres productos con precios distintos por punto."""

    def setUp(self):
        self.punto = Punto.objects.create(nombre="Palermo")
        self.otro = Punto.objects.create(nombre="Caballito")
        self.coca = self._producto("Coca 500", {self.punto: 1000, self.otro: 1200})
        self.alfajor = self._producto("Alfajor", {self.punto: 900, self.otro: 900})
        self.chicle = self._producto("Chicle", {self.punto: 300, self.otro: 300})

    def _producto(self, nombre, precios):
        producto = Producto.objects.create(nombre=nombre)
        for punto, precio in precios.items():
            PrecioPunto.objects.create(
                producto=producto, punto=punto, precio_venta=D(precio)
            )
        return producto

    def crear_oferta(self, tipo, valor, items, **kwargs):
        puntos = kwargs.pop("puntos", None)
        kwargs.setdefault("nombre", f"Promo {tipo}")
        kwargs.setdefault("alcance", Oferta.Alcance.SELECCIONADOS)
        oferta = Oferta.objects.create(tipo=tipo, valor=D(valor), **kwargs)
        if oferta.alcance == Oferta.Alcance.SELECCIONADOS:
            oferta.puntos.set(puntos if puntos is not None else [self.punto])
        for producto, cantidad in items:
            OfertaItem.objects.create(
                oferta=oferta, producto=producto, cantidad=cantidad
            )
        return oferta

    def cotizar(self, carrito, punto=None, fecha=None):
        items = [{"producto_id": p.pk, "cantidad": c} for p, c in carrito]
        return cotizar(punto=punto or self.punto, items=items, fecha=fecha)

    def linea(self, cotizacion, producto):
        return next(l for l in cotizacion.lineas if l.producto == producto)


class SinOfertasTest(BaseOfertas):
    def test_total_es_el_precio_de_lista(self):
        c = self.cotizar([(self.coca, 2), (self.alfajor, 1)])
        self.assertEqual(c.total, D("2900.00"))
        self.assertEqual(c.descuento_total, D("0.00"))
        self.assertFalse(c.tiene_ofertas)

    def test_usa_el_precio_del_punto(self):
        c = self.cotizar([(self.coca, 1)], punto=self.otro)
        self.assertEqual(c.total, D("1200.00"))

    def test_items_repetidos_se_suman_en_una_linea(self):
        items = [
            {"producto_id": self.coca.pk, "cantidad": 2},
            {"producto_id": self.coca.pk, "cantidad": 3},
        ]
        c = cotizar(punto=self.punto, items=items)
        self.assertEqual(len(c.lineas), 1)
        self.assertEqual(c.lineas[0].cantidad, 5)
        self.assertEqual(c.total, D("5000.00"))

    def test_acepta_la_instancia_del_producto(self):
        c = cotizar(punto=self.punto, items=[{"producto": self.coca, "cantidad": 1}])
        self.assertEqual(c.total, D("1000.00"))


class TiposDeOfertaTest(BaseOfertas):
    def test_precio_especial_por_unidad(self):
        self.crear_oferta(Oferta.Tipo.PRECIO_UNITARIO, 800, [(self.coca, 1)])
        c = self.cotizar([(self.coca, 3)])
        self.assertEqual(c.total, D("2400.00"))
        self.assertEqual(c.descuento_total, D("600.00"))
        self.assertEqual(self.linea(c, self.coca).precio_promedio, D("800.00"))

    def test_porcentaje(self):
        self.crear_oferta(Oferta.Tipo.PORCENTAJE, 15, [(self.coca, 1)])
        c = self.cotizar([(self.coca, 2)])
        self.assertEqual(c.total, D("1700.00"))
        self.assertEqual(c.descuento_total, D("300.00"))

    def test_porcentaje_escala_con_el_precio_del_punto(self):
        self.crear_oferta(
            Oferta.Tipo.PORCENTAJE, 15, [(self.coca, 1)], alcance=Oferta.Alcance.TODOS
        )
        self.assertEqual(self.cotizar([(self.coca, 1)]).total, D("850.00"))
        self.assertEqual(
            self.cotizar([(self.coca, 1)], punto=self.otro).total, D("1020.00")
        )

    def test_precio_por_grupo_deja_el_sobrante_a_precio_de_lista(self):
        # 2 x $1500 con 5 unidades: dos grupos y una unidad suelta.
        self.crear_oferta(Oferta.Tipo.PRECIO_GRUPO, 1500, [(self.coca, 2)])
        c = self.cotizar([(self.coca, 5)])
        self.assertEqual(c.total, D("4000.00"))
        self.assertEqual(c.descuento_total, D("1000.00"))
        self.assertEqual(self.linea(c, self.coca).ofertas[0].veces, 2)

    def test_paga_n(self):
        # 3x2: se paga por las 2 unidades más caras del grupo.
        self.crear_oferta(Oferta.Tipo.PAGA_N, 2, [(self.coca, 3)])
        self.assertEqual(self.cotizar([(self.coca, 3)]).total, D("2000.00"))
        self.assertEqual(self.cotizar([(self.coca, 2)]).total, D("2000.00"))
        self.assertEqual(self.cotizar([(self.coca, 7)]).total, D("5000.00"))

    def test_combo_de_productos_distintos(self):
        self.crear_oferta(
            Oferta.Tipo.PRECIO_GRUPO, 1600, [(self.coca, 1), (self.alfajor, 1)]
        )
        c = self.cotizar([(self.coca, 1), (self.alfajor, 1)])
        self.assertEqual(c.total, D("1600.00"))
        self.assertEqual(c.descuento_total, D("300.00"))
        # El descuento se reparte entre las dos líneas y cierra exacto.
        coca, alfajor = self.linea(c, self.coca), self.linea(c, self.alfajor)
        self.assertEqual(coca.descuento + alfajor.descuento, D("300.00"))
        self.assertEqual(coca.descuento, D("157.89"))
        self.assertEqual(alfajor.descuento, D("142.11"))
        self.assertEqual(coca.subtotal + alfajor.subtotal, c.total)

    def test_combo_incompleto_no_aplica(self):
        self.crear_oferta(
            Oferta.Tipo.PRECIO_GRUPO, 1600, [(self.coca, 1), (self.alfajor, 1)]
        )
        c = self.cotizar([(self.coca, 3)])
        self.assertEqual(c.total, D("3000.00"))
        self.assertFalse(c.tiene_ofertas)


class NoSubeElPrecioTest(BaseOfertas):
    def test_precio_de_oferta_mayor_al_de_lista_no_aplica(self):
        self.crear_oferta(Oferta.Tipo.PRECIO_UNITARIO, 1200, [(self.coca, 1)])
        c = self.cotizar([(self.coca, 1)])
        self.assertEqual(c.total, D("1000.00"))
        self.assertFalse(c.tiene_ofertas)

    def test_misma_oferta_aplica_en_un_punto_y_no_en_el_otro(self):
        # $1100 fijo: descuenta en Caballito ($1200) y no en Palermo ($1000).
        self.crear_oferta(
            Oferta.Tipo.PRECIO_UNITARIO,
            1100,
            [(self.coca, 1)],
            alcance=Oferta.Alcance.TODOS,
        )
        self.assertEqual(self.cotizar([(self.coca, 1)]).total, D("1000.00"))
        self.assertEqual(
            self.cotizar([(self.coca, 1)], punto=self.otro).total, D("1100.00")
        )

    def test_paga_n_sin_ahorro_no_aplica(self):
        self.crear_oferta(Oferta.Tipo.PAGA_N, 3, [(self.coca, 3)])
        self.assertEqual(self.cotizar([(self.coca, 3)]).total, D("3000.00"))


class AlcanceYVigenciaTest(BaseOfertas):
    def test_oferta_de_otro_punto_no_aplica(self):
        self.crear_oferta(
            Oferta.Tipo.PORCENTAJE, 20, [(self.coca, 1)], puntos=[self.otro]
        )
        self.assertEqual(self.cotizar([(self.coca, 1)]).total, D("1000.00"))
        self.assertEqual(
            self.cotizar([(self.coca, 1)], punto=self.otro).total, D("960.00")
        )

    def test_alcance_todos_aplica_en_cualquier_punto(self):
        self.crear_oferta(
            Oferta.Tipo.PORCENTAJE, 10, [(self.coca, 1)], alcance=Oferta.Alcance.TODOS
        )
        self.assertEqual(self.cotizar([(self.coca, 1)]).total, D("900.00"))
        self.assertEqual(
            self.cotizar([(self.coca, 1)], punto=self.otro).total, D("1080.00")
        )

    def test_programada_para_manana_todavia_no_aplica(self):
        manana = timezone.localdate() + timedelta(days=1)
        self.crear_oferta(Oferta.Tipo.PORCENTAJE, 10, [(self.coca, 1)], desde=manana)
        self.assertEqual(self.cotizar([(self.coca, 1)]).total, D("1000.00"))
        self.assertEqual(self.cotizar([(self.coca, 1)], fecha=manana).total, D("900.00"))

    def test_vencida_no_aplica(self):
        hoy = timezone.localdate()
        oferta = self.crear_oferta(
            Oferta.Tipo.PORCENTAJE,
            10,
            [(self.coca, 1)],
            desde=hoy - timedelta(days=10),
            hasta=hoy - timedelta(days=1),
        )
        self.assertEqual(self.cotizar([(self.coca, 1)]).total, D("1000.00"))
        self.assertEqual(oferta.estado, "vencida")

    def test_sin_fecha_de_fin_sigue_vigente(self):
        self.crear_oferta(
            Oferta.Tipo.PORCENTAJE,
            10,
            [(self.coca, 1)],
            desde=timezone.localdate() - timedelta(days=365),
        )
        self.assertEqual(self.cotizar([(self.coca, 1)]).total, D("900.00"))

    def test_apagada_no_aplica(self):
        oferta = self.crear_oferta(
            Oferta.Tipo.PORCENTAJE, 10, [(self.coca, 1)], activa=False
        )
        self.assertEqual(self.cotizar([(self.coca, 1)]).total, D("1000.00"))
        self.assertEqual(oferta.estado, "apagada")


class MejorParaElClienteTest(BaseOfertas):
    def test_entre_dos_ofertas_simples_gana_la_mas_barata(self):
        self.crear_oferta(Oferta.Tipo.PORCENTAJE, 10, [(self.coca, 1)])  # $900
        mejor = self.crear_oferta(
            Oferta.Tipo.PRECIO_UNITARIO, 850, [(self.coca, 1)]
        )  # $850
        c = self.cotizar([(self.coca, 1)])
        self.assertEqual(c.total, D("850.00"))
        self.assertEqual(self.linea(c, self.coca).oferta_principal, mejor)

    def test_combina_pack_y_combo_segun_el_ahorro(self):
        # Carrito: 5 Coca ($1000) + 1 alfajor ($900) = $5900 de lista.
        # A) 2x$1500 en Coca ahorra $500 por grupo. B) combo Coca+alfajor $1600
        # ahorra $300. Gana A dos veces (4 Cocas) y después B con lo que queda.
        pack = self.crear_oferta(Oferta.Tipo.PRECIO_GRUPO, 1500, [(self.coca, 2)])
        combo = self.crear_oferta(
            Oferta.Tipo.PRECIO_GRUPO, 1600, [(self.coca, 1), (self.alfajor, 1)]
        )
        c = self.cotizar([(self.coca, 5), (self.alfajor, 1)])
        self.assertEqual(c.total_lista, D("5900.00"))
        self.assertEqual(c.descuento_total, D("1300.00"))
        self.assertEqual(c.total, D("4600.00"))

        aplicadas = {
            a.oferta: a.veces for l in c.lineas for a in l.ofertas
        }
        self.assertEqual(aplicadas[pack], 2)
        self.assertEqual(aplicadas[combo], 1)

    def test_la_suma_de_las_lineas_da_el_total(self):
        self.crear_oferta(Oferta.Tipo.PRECIO_GRUPO, 1500, [(self.coca, 2)])
        self.crear_oferta(
            Oferta.Tipo.PRECIO_GRUPO,
            1000,
            [(self.coca, 1), (self.alfajor, 1), (self.chicle, 1)],
        )
        c = self.cotizar([(self.coca, 5), (self.alfajor, 2), (self.chicle, 3)])
        self.assertEqual(sum(l.subtotal for l in c.lineas), c.total)
        self.assertEqual(sum(l.descuento for l in c.lineas), c.descuento_total)

    def test_resultado_estable_para_el_mismo_carrito(self):
        self.crear_oferta(Oferta.Tipo.PRECIO_GRUPO, 1500, [(self.coca, 2)])
        self.crear_oferta(Oferta.Tipo.PORCENTAJE, 25, [(self.coca, 1)])
        carrito = [(self.coca, 5)]
        primero = self.cotizar(carrito).total
        for _ in range(3):
            self.assertEqual(self.cotizar(carrito).total, primero)

    def test_tope_por_venta(self):
        self.crear_oferta(
            Oferta.Tipo.PRECIO_GRUPO, 1500, [(self.coca, 2)], veces_max_por_venta=1
        )
        c = self.cotizar([(self.coca, 5)])
        self.assertEqual(c.total, D("4500.00"))
        self.assertEqual(self.linea(c, self.coca).ofertas[0].veces, 1)


class ErroresTest(BaseOfertas):
    def test_producto_sin_precio_en_el_punto(self):
        sin_precio = Producto.objects.create(nombre="Nuevo sin precio")
        with self.assertRaises(CotizacionError) as ctx:
            self.cotizar([(sin_precio, 1)])
        self.assertIn("no tiene precio", str(ctx.exception))

    def test_producto_inactivo(self):
        self.coca.activo = False
        self.coca.save(update_fields=["activo"])
        with self.assertRaises(CotizacionError):
            self.cotizar([(self.coca, 1)])

    def test_producto_inexistente(self):
        with self.assertRaises(CotizacionError):
            cotizar(punto=self.punto, items=[{"producto_id": 99999, "cantidad": 1}])

    def test_carrito_vacio(self):
        with self.assertRaises(CotizacionError):
            cotizar(punto=self.punto, items=[])

    def test_cantidad_invalida(self):
        with self.assertRaises(CotizacionError):
            self.cotizar([(self.coca, 0)])
        with self.assertRaises(CotizacionError):
            self.cotizar([(self.coca, -2)])


class ConfiguracionTest(BaseOfertas):
    def test_valor_de_porcentaje_fuera_de_rango(self):
        with self.assertRaises(ValidationError):
            Oferta(
                nombre="Mal", tipo=Oferta.Tipo.PORCENTAJE, valor=D(120)
            ).full_clean()

    def test_fecha_de_fin_anterior_al_inicio(self):
        hoy = timezone.localdate()
        with self.assertRaises(ValidationError):
            Oferta(
                nombre="Mal",
                tipo=Oferta.Tipo.PORCENTAJE,
                valor=D(10),
                desde=hoy,
                hasta=hoy - timedelta(days=1),
            ).full_clean()

    def test_oferta_bien_armada_no_tiene_errores(self):
        oferta = self.crear_oferta(Oferta.Tipo.PRECIO_GRUPO, 1500, [(self.coca, 2)])
        self.assertEqual(oferta.errores_de_configuracion(), [])

    def test_precio_unitario_con_varios_productos(self):
        oferta = self.crear_oferta(
            Oferta.Tipo.PRECIO_UNITARIO, 800, [(self.coca, 1), (self.alfajor, 1)]
        )
        self.assertTrue(oferta.errores_de_configuracion())

    def test_paga_n_tiene_que_ahorrar_una_unidad(self):
        oferta = self.crear_oferta(Oferta.Tipo.PAGA_N, 3, [(self.coca, 3)])
        self.assertTrue(oferta.errores_de_configuracion())

    def test_sin_productos_o_sin_puntos(self):
        oferta = Oferta.objects.create(
            nombre="Vacía", tipo=Oferta.Tipo.PORCENTAJE, valor=D(10)
        )
        errores = oferta.errores_de_configuracion()
        self.assertEqual(len(errores), 2)

    def test_avisa_donde_no_descontaria(self):
        oferta = self.crear_oferta(
            Oferta.Tipo.PRECIO_UNITARIO,
            1100,
            [(self.coca, 1)],
            alcance=Oferta.Alcance.TODOS,
        )
        self.assertEqual(oferta.puntos_sin_descuento(), [self.punto])

    def test_etiquetas(self):
        casos = [
            ((Oferta.Tipo.PRECIO_UNITARIO, 800, [(self.coca, 1)]), "$800"),
            ((Oferta.Tipo.PORCENTAJE, 15, [(self.coca, 1)]), "−15%"),
            ((Oferta.Tipo.PRECIO_GRUPO, 1500, [(self.coca, 2)]), "2 x $1500"),
            ((Oferta.Tipo.PAGA_N, 2, [(self.coca, 3)]), "3x2"),
            (
                (Oferta.Tipo.PRECIO_GRUPO, 1600, [(self.coca, 1), (self.alfajor, 1)]),
                "combo $1600",
            ),
        ]
        for (tipo, valor, items), esperada in casos:
            with self.subTest(tipo=tipo):
                oferta = self.crear_oferta(tipo, valor, items)
                self.assertEqual(oferta.etiqueta, esperada)
                oferta.delete()

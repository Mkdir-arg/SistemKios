from decimal import Decimal

from django.template import Context, Template
from django.test import SimpleTestCase

from apps.core.formato import plata


class PlataTests(SimpleTestCase):
    def test_formato_argentino(self):
        self.assertEqual(plata(Decimal("1234567.5")), "$1.234.567,50")
        self.assertEqual(plata(Decimal("0")), "$0,00")
        self.assertEqual(plata("950"), "$950,00")

    def test_negativo_y_redondeo(self):
        self.assertEqual(plata(Decimal("-2500.505")), "−$2.500,51")

    def test_vacio_e_invalido(self):
        self.assertEqual(plata(None), "$0,00")
        self.assertEqual(plata("abc"), "")

    def test_filtro_de_template(self):
        html = Template("{% load sk %}{{ v|plata }}").render(Context({"v": Decimal("15000")}))
        self.assertEqual(html, "$15.000,00")

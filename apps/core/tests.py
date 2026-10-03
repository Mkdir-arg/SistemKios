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


# --- Tiempo real (Supabase Realtime) ------------------------------------------
from unittest import mock

import jwt
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.core import realtime
from apps.puntos.models import Punto

SUPABASE = dict(
    TIEMPO_REAL_HABILITADO=True,
    SUPABASE_URL="https://abc.supabase.co",
    SUPABASE_ANON_KEY="anon",
    SUPABASE_JWT_SECRET="secreto-de-prueba-con-largo-suficiente-32b",
    SUPABASE_JWT_PRIVATE_KEY="",
)


def leer(token):
    return jwt.decode(token, SUPABASE["SUPABASE_JWT_SECRET"], algorithms=["HS256"], audience="authenticated")


@override_settings(**SUPABASE)
class TokenTiempoRealTest(TestCase):
    def setUp(self):
        self.punto = Punto.objects.create(nombre="Palermo")
        self.vendedor = User.objects.create_user("ven", password="x", rol=User.Rol.VENDEDOR, punto=self.punto)
        self.admin = User.objects.create_user("adm", password="x", rol=User.Rol.SUPER_ADMIN)

    def test_el_vendedor_solo_escucha_su_punto(self):
        claims = leer(realtime.token_para(self.vendedor))
        self.assertEqual(claims["role"], "authenticated")
        self.assertEqual(claims["sk_canales"], [f"punto-{self.punto.pk}"])
        self.assertFalse(claims["sk_admin"])

    def test_el_super_admin_escucha_todo(self):
        claims = leer(realtime.token_para(self.admin))
        self.assertTrue(claims["sk_admin"])
        self.assertEqual(claims["sk_canales"], [])

    def test_vence_en_una_hora(self):
        claims = leer(realtime.token_para(self.vendedor))
        self.assertEqual(claims["exp"] - claims["iat"], realtime.DURACION_TOKEN)

    def test_la_vista_pide_login(self):
        r = self.client.get("/tiempo-real/token/")
        self.assertEqual(r.status_code, 302)

    def test_la_vista_entrega_config_y_token(self):
        self.client.force_login(self.vendedor)
        data = self.client.get("/tiempo-real/token/").json()
        self.assertTrue(data["habilitado"])
        self.assertEqual(data["url"], "https://abc.supabase.co")
        self.assertEqual(data["anon_key"], "anon")
        self.assertEqual(leer(data["token"])["sk_canales"], [f"punto-{self.punto.pk}"])

    @override_settings(TIEMPO_REAL_HABILITADO=False)
    def test_sin_supabase_la_vista_lo_dice(self):
        self.client.force_login(self.vendedor)
        self.assertEqual(self.client.get("/tiempo-real/token/").json(), {"habilitado": False})


class NotificarPuntoTest(TestCase):
    @override_settings(TIEMPO_REAL_HABILITADO=False)
    def test_sin_supabase_no_publica(self):
        with mock.patch.object(realtime, "connection") as conn:
            realtime.notificar_punto(1, "venta", total="10.00")
        conn.cursor.assert_not_called()

    @override_settings(**SUPABASE)
    def test_publica_en_el_canal_del_punto(self):
        with mock.patch.object(realtime, "connection") as conn:
            realtime.notificar_punto(7, "venta", total="10.00")
        cursor = conn.cursor.return_value.__enter__.return_value
        sql, params = cursor.execute.call_args.args
        self.assertIn("realtime.send", sql)
        self.assertEqual(params[1:], ["venta", "punto-7"])
        self.assertEqual(params[0], '{"tipo": "venta", "total": "10.00"}')

    @override_settings(**SUPABASE)
    def test_un_error_al_publicar_no_rompe_la_operacion(self):
        with mock.patch.object(realtime, "connection") as conn:
            conn.cursor.side_effect = RuntimeError("sin realtime")
            with self.assertLogs("apps.core.realtime", "ERROR"):
                realtime.notificar_punto(7, "venta")

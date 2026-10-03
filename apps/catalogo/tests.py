"""Tests del catálogo."""
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from .views import _achicar_imagen


def imagen(ancho, alto, formato="JPEG", modo="RGB"):
    buf = BytesIO()
    Image.new(modo, (ancho, alto)).save(buf, format=formato)
    return SimpleUploadedFile(f"foto.{formato.lower()}", buf.getvalue())


class AchicarImagenTest(SimpleTestCase):
    def test_achica_las_fotos_grandes_sin_tocar_disco(self):
        resultado = _achicar_imagen(imagen(2000, 1000))
        img = Image.open(resultado)
        self.assertEqual(img.size, (800, 400))
        self.assertEqual(resultado.name, "foto.jpeg")

    def test_deja_igual_las_chicas(self):
        original = imagen(300, 200)
        self.assertIs(_achicar_imagen(original), original)

    def test_respeta_el_formato_png(self):
        resultado = _achicar_imagen(imagen(1600, 1600, "PNG", "RGBA"))
        self.assertEqual(Image.open(resultado).format, "PNG")

    def test_si_no_es_imagen_devuelve_el_archivo(self):
        basura = SimpleUploadedFile("x.jpg", b"no soy una imagen")
        self.assertIs(_achicar_imagen(basura), basura)

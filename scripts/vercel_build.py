"""
Paso de build en Vercel (`[tool.vercel.scripts] build` en pyproject.toml).

Corre después de instalar las dependencias y antes de publicar el deploy: aplica las
migraciones y crea el Super Admin inicial. `collectstatic` no va acá: Vercel lo corre solo.

Solo actúa en el deploy de **producción**. Un preview (una rama, un PR) no migra: si lo
hiciera, código a medio terminar cambiaría el esquema de la base real.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def main():
    entorno = os.environ.get("VERCEL_ENV", "")
    if entorno != "production":
        print(f"→ Deploy '{entorno or 'local'}': no se migra (solo en producción).")
        return

    # Las migraciones van por la conexión de sesión (puerto 5432), no por el pooler en modo
    # transacción que usa la app: DDL y transacciones largas no se llevan bien con ese modo.
    directa = os.environ.get("DATABASE_URL_MIGRACIONES")
    if directa:
        os.environ["DATABASE_URL"] = directa

    import django

    django.setup()
    from django.core.management import call_command

    print("→ Aplicando migraciones...")
    call_command("migrate", interactive=False)
    print("→ Verificando Super Admin inicial...")
    call_command("seed_admin")


if __name__ == "__main__":
    main()

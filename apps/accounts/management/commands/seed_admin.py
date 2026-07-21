import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Crea el Super Admin inicial si todavía no existe. "
        "Usa las variables de entorno DJANGO_SUPERUSER_USERNAME / "
        "DJANGO_SUPERUSER_PASSWORD / DJANGO_SUPERUSER_EMAIL."
    )

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")

        if not password:
            self.stdout.write(
                self.style.WARNING(
                    "No hay DJANGO_SUPERUSER_PASSWORD definida: se omite la creación "
                    "del Super Admin. Podés crearlo con `manage.py createsuperuser`."
                )
            )
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f"El usuario «{username}» ya existe. Nada que hacer.")
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(
            self.style.SUCCESS(f"Super Admin «{username}» creado correctamente.")
        )

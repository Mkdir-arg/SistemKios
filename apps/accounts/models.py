from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Usuario del sistema. Solo dos roles:

    - Super Admin: crea usuarios y puntos y maneja todo (productos, precios,
      transferencias, reportes).
    - Vendedor: trabaja en un punto; solo vende y suma stock.
    """

    class Rol(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        VENDEDOR = "vendedor", "Vendedor"

    rol = models.CharField(
        "rol", max_length=20, choices=Rol.choices, default=Rol.VENDEDOR
    )
    punto = models.ForeignKey(
        "puntos.Punto",
        verbose_name="punto",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vendedores",
        help_text="Punto donde trabaja el vendedor. El Super Admin no tiene punto.",
    )

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    @property
    def es_super_admin(self):
        return self.is_superuser or self.rol == self.Rol.SUPER_ADMIN

    @property
    def es_vendedor(self):
        return self.rol == self.Rol.VENDEDOR and not self.is_superuser

    def save(self, *args, **kwargs):
        # Un superusuario de Django es, por definición, Super Admin del negocio.
        if self.is_superuser:
            self.rol = self.Rol.SUPER_ADMIN
            self.punto = None
        super().save(*args, **kwargs)

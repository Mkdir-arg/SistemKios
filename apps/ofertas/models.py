"""
Ofertas: promociones sobre productos, vigentes por fecha y por punto.

Acá viven el modelo y las reglas de precio de cada tipo de oferta. El motor que
resuelve un carrito completo está en `services.cotizar`.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

CENTAVO = Decimal("0.01")
CERO = Decimal("0.00")


def redondear(monto):
    """Redondea a dos decimales; todo el dinero del sistema se maneja así."""
    return Decimal(monto).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _num(valor):
    """Formatea un valor para mostrarlo: 15.00 -> «15», 15.50 -> «15,50»."""
    if valor == valor.to_integral_value():
        return f"{valor:.0f}"
    return f"{valor:.2f}".replace(".", ",")


class OfertaQuerySet(models.QuerySet):
    def vigentes(self, punto=None, fecha=None):
        """
        Ofertas activas en la fecha dada (por defecto hoy) y, si se pasa un
        punto, que además lo alcancen.
        """
        fecha = fecha or timezone.localdate()
        qs = self.filter(activa=True, desde__lte=fecha).filter(
            models.Q(hasta__isnull=True) | models.Q(hasta__gte=fecha)
        )
        if punto is not None:
            qs = qs.filter(
                models.Q(alcance=Oferta.Alcance.TODOS) | models.Q(puntos=punto)
            )
        return qs.distinct()


class Oferta(models.Model):
    """
    Una promoción. `tipo` define cómo se lee `valor`:

    - PRECIO_UNITARIO: `valor` es el precio final de la unidad (alfajor a $800).
    - PORCENTAJE:      `valor` es el descuento sobre el precio de lista (15 = 15%).
    - PRECIO_GRUPO:    `valor` es el precio de todo el grupo (2 unidades a $1500,
                       o alfajor + gaseosa a $1200).
    - PAGA_N:          `valor` es cuántas unidades se pagan del grupo
                       (3x2 -> un ítem con cantidad 3 y valor 2).

    Qué productos y cuántas unidades forman el grupo se define en `OfertaItem`.
    Los tipos con importe fijo (PRECIO_UNITARIO, PRECIO_GRUPO) usan el mismo
    valor en todos los puntos alcanzados: si el precio de lista de un punto es
    más bajo que el de la oferta, ahí simplemente no se aplica.
    """

    class Tipo(models.TextChoices):
        PRECIO_UNITARIO = "precio_unitario", "Precio especial por unidad"
        PORCENTAJE = "porcentaje", "% de descuento"
        PRECIO_GRUPO = "precio_grupo", "Precio por el conjunto (2x$1500, combo)"
        PAGA_N = "paga_n", "Llevá N, pagá M (3x2)"

    class Alcance(models.TextChoices):
        TODOS = "todos", "Todos los puntos"
        SELECCIONADOS = "seleccionados", "Solo los puntos elegidos"

    nombre = models.CharField("nombre", max_length=120)
    tipo = models.CharField("tipo", max_length=16, choices=Tipo.choices)
    valor = models.DecimalField("valor", max_digits=12, decimal_places=2)
    alcance = models.CharField(
        "alcance", max_length=14, choices=Alcance.choices, default=Alcance.SELECCIONADOS
    )
    puntos = models.ManyToManyField(
        "puntos.Punto", verbose_name="puntos", blank=True, related_name="ofertas"
    )
    desde = models.DateField("desde", default=timezone.localdate)
    hasta = models.DateField(
        "hasta", null=True, blank=True, help_text="Vacío: la oferta no vence."
    )
    activa = models.BooleanField("activa", default=True)
    veces_max_por_venta = models.PositiveSmallIntegerField(
        "tope por venta",
        null=True,
        blank=True,
        help_text="Cuántas veces puede aplicarse en una misma venta. Vacío: sin tope.",
    )
    creado = models.DateTimeField("creado", auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="creada por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ofertas",
    )

    objects = OfertaQuerySet.as_manager()

    class Meta:
        verbose_name = "oferta"
        verbose_name_plural = "ofertas"
        ordering = ["-desde", "nombre"]

    def __str__(self):
        return self.nombre

    # --- vigencia y alcance -------------------------------------------------

    def esta_vigente(self, fecha=None):
        fecha = fecha or timezone.localdate()
        if not self.activa or self.desde > fecha:
            return False
        return self.hasta is None or self.hasta >= fecha

    def alcanza_a(self, punto):
        if self.alcance == self.Alcance.TODOS:
            return True
        return self.puntos.filter(pk=punto.pk).exists()

    # --- precio del grupo ---------------------------------------------------

    def _unitarios(self, precios):
        """
        [(producto_id, precio_de_lista, cantidad), ...] del grupo.

        `precios` es {producto_id: precio de lista en el punto}. Devuelve None
        si la oferta no tiene ítems o si falta el precio de alguno: en ese caso
        la oferta no se puede evaluar y el motor la saltea.
        """
        items = list(self.items.all())
        if not items:
            return None
        if any(i.producto_id not in precios for i in items):
            return None
        return [(i.producto_id, precios[i.producto_id], i.cantidad) for i in items]

    def total_lista_del_grupo(self, precios):
        """Cuánto costaría un grupo completo sin la oferta."""
        unitarios = self._unitarios(precios)
        if unitarios is None:
            return None
        return redondear(sum((p * c for _, p, c in unitarios), CERO))

    def precio_del_grupo(self, precios):
        """Cuánto cuesta un grupo completo con la oferta aplicada."""
        unitarios = self._unitarios(precios)
        if unitarios is None:
            return None

        unidades = sum(c for _, _, c in unitarios)
        lista = sum((p * c for _, p, c in unitarios), CERO)

        if self.tipo == self.Tipo.PRECIO_UNITARIO:
            total = self.valor * unidades
        elif self.tipo == self.Tipo.PORCENTAJE:
            total = lista * (Decimal("100") - self.valor) / Decimal("100")
        elif self.tipo == self.Tipo.PRECIO_GRUPO:
            total = self.valor
        elif self.tipo == self.Tipo.PAGA_N:
            # Se pagan las `valor` unidades más caras: las baratas van de regalo.
            todas = sorted(
                (p for _, p, c in unitarios for _ in range(c)), reverse=True
            )
            total = sum(todas[: int(self.valor)], CERO)
        else:
            return None
        return redondear(total)

    def descuento_del_grupo(self, precios):
        """
        Cuánto ahorra un grupo completo. Devuelve 0 si la oferta no conviene:
        una oferta nunca puede subir el precio de lista.
        """
        total = self.precio_del_grupo(precios)
        if total is None:
            return CERO
        descuento = self.total_lista_del_grupo(precios) - total
        return descuento if descuento > 0 else CERO

    # --- presentación -------------------------------------------------------

    @property
    def unidades_del_grupo(self):
        return sum(i.cantidad for i in self.items.all())

    @property
    def etiqueta(self):
        """Texto corto para el POS: «2 x $1500», «−15%», «3x2», «$800»."""
        items = list(self.items.all())
        unidades = sum(i.cantidad for i in items)
        if self.tipo == self.Tipo.PORCENTAJE:
            return f"−{_num(self.valor)}%"
        if self.tipo == self.Tipo.PRECIO_UNITARIO:
            return f"${_num(self.valor)}"
        if self.tipo == self.Tipo.PAGA_N:
            return f"{unidades}x{_num(self.valor)}"
        if self.tipo == self.Tipo.PRECIO_GRUPO:
            if len(items) == 1:
                return f"{unidades} x ${_num(self.valor)}"
            return f"combo ${_num(self.valor)}"
        return self.nombre

    @property
    def estado(self):
        """vigente · programada · vencida · apagada (para la lista del ABM)."""
        hoy = timezone.localdate()
        if not self.activa:
            return "apagada"
        if self.desde > hoy:
            return "programada"
        if self.hasta is not None and self.hasta < hoy:
            return "vencida"
        return "vigente"

    # --- validación ---------------------------------------------------------

    def clean(self):
        errores = {}
        if self.desde and self.hasta and self.hasta < self.desde:
            errores["hasta"] = "La fecha de fin no puede ser anterior al inicio."
        if self.valor is not None:
            if self.tipo == self.Tipo.PORCENTAJE and not (0 < self.valor < 100):
                errores["valor"] = "El descuento tiene que estar entre 0 y 100%."
            elif (
                self.tipo in (self.Tipo.PRECIO_UNITARIO, self.Tipo.PRECIO_GRUPO)
                and self.valor < 0
            ):
                errores["valor"] = "El precio de la oferta no puede ser negativo."
            elif self.tipo == self.Tipo.PAGA_N and self.valor < 1:
                errores["valor"] = "Tiene que pagarse al menos una unidad."
        if errores:
            raise ValidationError(errores)

    def errores_de_configuracion(self):
        """
        Valida lo que depende de los ítems y los puntos, que recién existen
        después de guardar (el ABM la llama al final del alta/edición).

        Devuelve una lista de mensajes; vacía si la oferta está bien armada. El
        motor de cálculo no la usa: ante una oferta rota prefiere ignorarla
        antes que hacer fallar una venta.
        """
        errores = []
        items = list(self.items.all())
        if not items:
            errores.append("La oferta necesita al menos un producto.")
        if self.alcance == self.Alcance.SELECCIONADOS and not self.puntos.exists():
            errores.append("Elegí al menos un punto donde aplicar la oferta.")
        if not items:
            return errores

        unidades = sum(i.cantidad for i in items)
        if self.tipo == self.Tipo.PRECIO_UNITARIO and (
            len(items) > 1 or unidades > 1
        ):
            errores.append(
                "Un precio especial va sobre un solo producto y una unidad. "
                "Para varios productos juntos usá «precio por el conjunto»."
            )
        if self.tipo == self.Tipo.PORCENTAJE and unidades != len(items):
            errores.append("En un % de descuento cada producto va con cantidad 1.")
        if self.tipo == self.Tipo.PRECIO_GRUPO and unidades < 2:
            errores.append(
                "Un precio por el conjunto necesita 2 unidades o más. "
                "Para una sola usá «precio especial por unidad»."
            )
        if self.tipo == self.Tipo.PAGA_N:
            if len(items) > 1:
                errores.append("«Llevá N, pagá M» va sobre un solo producto.")
            elif unidades < 2:
                errores.append("«Llevá N, pagá M» necesita 2 unidades o más.")
            elif self.valor is not None and self.valor >= unidades:
                errores.append(
                    f"Si se llevan {unidades} unidades, hay que pagar menos de {unidades}."
                )
        return errores

    def puntos_sin_descuento(self):
        """
        Puntos alcanzados donde la oferta no descontaría nada, porque el precio
        de lista de ahí ya es igual o menor. Sirve para avisar en el ABM.
        """
        from apps.catalogo.models import PrecioPunto
        from apps.puntos.models import Punto

        items = list(self.items.all())
        if not items:
            return []
        if self.alcance == self.Alcance.TODOS:
            # «Todos» son los locales a la calle: en el depósito no se vende.
            puntos = Punto.objects.filter(activo=True, es_deposito=False)
        else:
            puntos = self.puntos.all()

        sin_descuento = []
        for punto in puntos:
            precios = dict(
                PrecioPunto.objects.filter(
                    punto=punto, producto_id__in=[i.producto_id for i in items]
                ).values_list("producto_id", "precio_venta")
            )
            if self.descuento_del_grupo(precios) <= 0:
                sin_descuento.append(punto)
        return sin_descuento


class OfertaItem(models.Model):
    """Un producto (con su cantidad) dentro del grupo que arma la oferta."""

    oferta = models.ForeignKey(
        Oferta, verbose_name="oferta", on_delete=models.CASCADE, related_name="items"
    )
    producto = models.ForeignKey(
        "catalogo.Producto",
        verbose_name="producto",
        on_delete=models.PROTECT,
        related_name="oferta_items",
    )
    cantidad = models.PositiveSmallIntegerField("cantidad", default=1)

    class Meta:
        verbose_name = "ítem de oferta"
        verbose_name_plural = "ítems de oferta"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["oferta", "producto"], name="oferta_item_unico"
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad__gte=1),
                name="oferta_item_cantidad_positiva",
            ),
        ]

    def __str__(self):
        return f"{self.cantidad}× {self.producto}"

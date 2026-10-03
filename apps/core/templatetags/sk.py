from django import template

from apps.core.formato import plata as _plata

register = template.Library()


@register.filter
def plata(valor):
    """`{{ monto|plata }}` → `$1.234,50`."""
    return _plata(valor)

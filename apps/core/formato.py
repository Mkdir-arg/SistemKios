from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def plata(valor):
    """Importe con formato argentino: `$1.234,50` (negativos: `−$1.234,50`).

    Es el mismo formato que `SK.fmt` en el navegador, para que un monto se lea igual
    en todas las pantallas.
    """
    try:
        d = Decimal(str(valor if valor is not None else 0))
    except InvalidOperation:
        return ""
    d = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    texto = f"{abs(d):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{'−' if d < 0 else ''}${texto}"

# Ventas y POS

## Acceso

### REQ-VEN-001 · El POS es del vendedor con jornada abierta
**Estado:** implementado · **Dónde:** [ventas/views.py](../../apps/ventas/views.py)

`/vender/` exige rol vendedor (el Super Admin recibe un aviso y vuelve al inicio) y jornada
abierta (si no la tiene, va a abrirla). Todos los endpoints del POS revalidan la jornada.

Ver [REQ-CAJ-001](04-caja-y-jornada.md#req-caj-001--vender-exige-una-jornada-abierta) y
[REQ-CAJ-004](04-caja-y-jornada.md#req-caj-004--la-jornada-es-solo-de-los-vendedores).

## Escaneo

### REQ-VEN-002 · Se vende escaneando; cada escaneo trae precio y stock del punto
**Estado:** implementado · **Dónde:** [ventas/views.py](../../apps/ventas/views.py)

`/vender/buscar/?codigo=` devuelve nombre, precio de lista **del punto de la jornada**, stock
en ese punto, si es servicio, la comisión y la imagen. Un producto inactivo se responde como
no encontrado.

### REQ-VEN-003 · Un producto sin precio en el punto no entra al carrito
**Estado:** implementado · **Dónde:** [ventas/views.py](../../apps/ventas/views.py)

El escaneo devuelve error 400 con el nombre del producto y el punto. Antes se iba al carrito
en $0; se cambió a propósito.

**Por qué:** ver [REQ-CAT-007](02-catalogo-y-precios.md#req-cat-007--sin-precio-en-un-punto-el-producto-no-se-vende-ahí). Vender en $0 es peor que no vender.

## Precio

### REQ-VEN-004 · El precio de la venta lo resuelve el servidor
**Estado:** implementado · **Dónde:** [ventas/views.py](../../apps/ventas/views.py), [ventas/services.py](../../apps/ventas/services.py)

El carrito lo maneja el navegador (para que el escaneo sea instantáneo), pero **los importes
no**:

- en cada cambio del carrito, el POS llama a `/vender/cotizar/` y muestra lo que devuelve;
- al confirmar, `registrar_venta` **vuelve a cotizar** y graba ese resultado;
- lo único que manda el navegador es `producto_id`, `cantidad` y, en servicios, el `monto`.

**Por qué:** es la regla de [REQ-GEN-009](00-generales.md#req-gen-009--el-navegador-no-decide-ningún-número).
Con las ofertas la tentación de calcular en el cliente es grande, y el resultado sería un total
manipulable y dos implementaciones del mismo cálculo que se desincronizan.

**Depende de:** [REQ-OFE-001](06-ofertas.md#req-ofe-001--cotizar-es-la-única-fuente-de-verdad-del-precio).

### REQ-VEN-005 · El carrito vacío no es un error
**Estado:** implementado · **Dónde:** [ventas/views.py](../../apps/ventas/views.py)

`/vender/cotizar/` con cero ítems devuelve una cotización en cero, no un 400.

**Por qué:** el POS pide cotización en cada cambio, y borrar la última línea es un cambio
normal, no una falla.

## Cobro

### REQ-VEN-006 · Se cobra con pago mixto y lo pagado no puede ser menor al total
**Estado:** implementado · **Dónde:** [ventas/services.py](../../apps/ventas/services.py) (`_pagos_netos`), [ventas/migrations/0003_pagos_sin_vuelto.py](../../apps/ventas/migrations/0003_pagos_sin_vuelto.py) · **Verifica:** `apps/ventas/tests.py` (`VueltoTest`, `PagosInvalidosTest`, `MigracionPagosSinVueltoTest`)

Una venta tiene N `Pago`, cada uno con medio (efectivo, tarjeta, transferencia/QR) y monto.
La suma tiene que alcanzar el total; si sobra, la diferencia es el vuelto y **no se guarda**:
el vuelto sale del efectivo, así que el `Pago` en efectivo se guarda por lo que queda en la
caja (lo entregado menos el vuelto) y la suma de los pagos da exacto el total. Si lo que
sobra supera al efectivo (pagaron de más con tarjeta o transferencia), la venta se rechaza.
Los pagos en 0 o negativos se ignoran, un medio desconocido es error, y dos renglones del
mismo medio se suman. Las ventas registradas antes de esta regla se corrigieron con la
migración `ventas/0003_pagos_sin_vuelto`.

En el POS el cobro se hace con teclado: el foco arranca en Efectivo, Enter confirma y Escape
cierra. El vuelto se ve mientras se cobra y queda a la vista después de confirmar, hasta la
próxima venta, porque el cajero lo necesita mientras da el cambio.

**Por qué:** «te pago $5000 en efectivo y el resto con QR» es lo normal en el mostrador. El
vuelto no se registra porque no es plata del negocio: si se guardara, el efectivo esperado
del arqueo daría de más y marcaría un faltante que no existe (pasó).

## Registro

### REQ-VEN-007 · El stock se descuenta al confirmar, en la misma transacción
**Estado:** implementado · **Dónde:** [ventas/services.py](../../apps/ventas/services.py)

No se reserva stock al escanear. Al confirmar, cada línea genera un movimiento de tipo venta
vía `aplicar_movimiento`. Si falta stock de un solo ítem, **no se registra nada**: ni venta,
ni pagos, ni descuentos de las otras líneas.

**Por qué:** reservar en el escaneo obligaría a liberar reservas abandonadas (el cliente que
se arrepiente, la pestaña que se cierra), y eso es una fuente de stock fantasma.

### REQ-VEN-008 · Los servicios no descuentan stock
**Estado:** implementado · **Dónde:** [ventas/services.py](../../apps/ventas/services.py)

Las líneas de productos con `es_servicio=True` se graban en la venta y entran a la caja, pero
no generan movimiento de stock.

Ver [REQ-CAT-008](02-catalogo-y-precios.md#req-cat-008--un-producto-puede-ser-un-servicio-se-cobra-pero-no-lleva-stock).

### REQ-VEN-009 · La línea guarda el precio de lista, el descuento y la oferta que lo causó
**Estado:** implementado · **Dónde:** [ventas/models.py](../../apps/ventas/models.py)

`DetalleVenta` guarda `precio_unitario` (el precio de **lista** del punto), `descuento` (lo
que quitó la oferta sobre la línea entera), la **oferta que más descontó** y el `subtotal`,
donde `subtotal = precio_unitario × cantidad − descuento`. La venta guarda además su
`descuento_total` y expone `total_lista`.

**Por qué:** un «2 x $1500» no da un precio unitario parejo: con 5 unidades, 4 entran en la
promo y 1 va a precio de lista. Guardar un unitario promedio perdería el dato de cuánto se
resignó por promociones, que es justo lo que el dueño quiere medir.

### REQ-VEN-010 · La venta confirmada avisa al punto en vivo
**Estado:** implementado · **Dónde:** [ventas/services.py](../../apps/ventas/services.py)

En `on_commit` se publica el evento `venta` (id, total, cantidad de ítems, vendedor) al grupo
del punto. Ver [REQ-RT-002](09-tiempo-real.md#req-rt-002--los-eventos-se-publican-recién-cuando-la-transacción-cerró).

## Pendientes

### REQ-VEN-011 · Anular una venta
**Estado:** pendiente

`Venta.Estado.ANULADA` existe en el modelo y los reportes y el arqueo ya filtran por
`confirmada`, pero **nada la setea**: no hay forma de anular. Falta definir quién puede
(¿el vendedor en su turno, el Super Admin siempre?) y que la anulación devuelva el stock y
ajuste el efectivo esperado de la jornada.

### REQ-VEN-012 · Ver el detalle de una venta en la app
**Estado:** pendiente

Las ventas se consultan solo desde el panel de Django o agregadas en los reportes. Falta el
comprobante / detalle por venta (líneas, ofertas aplicadas, pagos).

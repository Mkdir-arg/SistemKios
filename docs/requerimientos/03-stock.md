# Stock

## Modelo

### REQ-STK-001 · El stock se lleva por producto y punto
**Estado:** implementado · **Dónde:** [stock/models.py](../../apps/stock/models.py)

`StockPunto` es único por (producto, punto) y guarda `cantidad` y `stock_minimo`. La
cantidad es un entero **no negativo** a nivel de base (`PositiveIntegerField`).

### REQ-STK-002 · Cada variación de stock queda registrada en el kardex
**Estado:** implementado · **Dónde:** [stock/models.py](../../apps/stock/models.py)

`MovimientoStock` guarda el delta con signo, el **saldo resultante**, el tipo, el usuario, la
nota y la fecha. Tipos: ingreso de mercadería, salida, ajuste, venta, transferencia de
entrada y transferencia de salida.

**Por qué:** cuando el stock del sistema no coincide con el del estante, la única forma de
entender qué pasó es la lista de movimientos con el saldo que dejó cada uno.

### REQ-STK-003 · Toda variación pasa por `aplicar_movimiento`
**Estado:** implementado · **Dónde:** [stock/services.py](../../apps/stock/services.py)

Es la única puerta para tocar el stock. Hace, en una transacción:

1. `select_for_update` sobre la fila de `StockPunto` (la crea si no existía);
2. rechaza el delta 0 y el saldo negativo (`StockInsuficiente`);
3. guarda la nueva cantidad y crea el movimiento del kardex;
4. avisa al punto por WebSocket en `on_commit`, indicando si quedó bajo el mínimo.

**Por qué:** dos cajas del mismo punto pueden vender el mismo producto al mismo tiempo. Sin
el lock, las dos leerían el mismo saldo y una sobreescribiría a la otra.

### REQ-STK-004 · El stock nunca queda negativo
**Estado:** implementado · **Dónde:** [stock/services.py](../../apps/stock/services.py)

Si un movimiento dejaría el saldo por debajo de 0, se levanta `StockInsuficiente` con el
detalle (cuánto hay y cuánto se quiso restar) y la transacción completa se revierte: la
venta o transferencia no se registra.

**Por qué:** un stock negativo no significa nada físicamente y contamina todos los reportes.

### REQ-STK-005 · El stock mínimo dispara el aviso de faltante
**Estado:** implementado · **Dónde:** [stock/models.py](../../apps/stock/models.py), [core/views.py](../../apps/core/views.py)

Con `stock_minimo > 0`, cuando la cantidad queda **menor o igual** al mínimo el producto
pasa a estar «bajo mínimo»: se marca en el evento en vivo y aparece en el reporte
([REQ-REP-004](08-reportes.md#req-rep-004--el-reporte-marca-el-stock-bajo-mínimo)). Con mínimo en 0 el aviso está apagado.

## Pantalla de stock

### REQ-STK-006 · Se puede dar de alta un producto desde el lector
**Estado:** implementado · **Dónde:** [stock/views.py](../../apps/stock/views.py)

Si el código escaneado no existe, la pantalla ofrece crearlo ahí mismo con código, nombre,
categoría, costo, precio de venta y cantidad inicial. En una sola transacción se crea el
producto, su código (principal), el precio y el ingreso de stock. Si el código ya está
usado, responde 409.

El **precio se replica a todos los puntos de venta activos** (calculando el margen contra el
precio base), **no al Depósito** — ahí no se vende
([REQ-GEN-002](00-generales.md#req-gen-002--el-depósito-es-un-punto-especial-y-hay-uno-solo)).

**Por qué:** cuando llega mercadería nueva, el que la está guardando no puede cortar para
ir a cargar el producto en otra pantalla. Y el precio suele ser el mismo en todos los locales.

### REQ-STK-007 · Al escanear se ve el stock de la ubicación, el total y el desglose
**Estado:** implementado · **Dónde:** [stock/views.py](../../apps/stock/views.py)

La respuesta trae la cantidad en la ubicación seleccionada, el **total del negocio** y el
detalle por ubicación (Depósito primero, después cada punto), más el precio de venta ahí.

**Por qué:** antes de sumar mercadería conviene ver si el faltante es real o si el stock está
en otro local y lo que hace falta es una transferencia.

### REQ-STK-008 · Los servicios quedan afuera del stock
**Estado:** implementado · **Dónde:** [stock/views.py](../../apps/stock/views.py)

Al escanear un servicio en la pantalla de stock, la respuesta lo identifica como tal en vez
de ofrecer sumar cantidad. La tabla de stock lista solo productos activos con
`es_servicio=False`.

Ver [REQ-CAT-008](02-catalogo-y-precios.md#req-cat-008--un-producto-puede-ser-un-servicio-se-cobra-pero-no-lleva-stock).

### REQ-STK-009 · El vendedor opera en su punto; el Super Admin elige la ubicación
**Estado:** implementado · **Dónde:** [stock/views.py](../../apps/stock/views.py)

`_resolver_punto` decide: el vendedor siempre trabaja sobre su punto (no puede elegir otro);
el Super Admin elige entre las ubicaciones activas y, si no elige nada, se asume el
**Depósito**.

**Por qué:** la mercadería que compra el dueño entra al Depósito; que sea el default evita el
error más común de la pantalla.

### REQ-STK-010 · La tabla de stock muestra una fila por producto y una columna por ubicación
**Estado:** implementado · **Dónde:** [stock/views.py](../../apps/stock/views.py), [partials/stock_tabla.html](../../templates/partials/stock_tabla.html)

Se sirve como JSON (`/stock/tabla/`) para poder refrescarla sin recargar la página cuando
llega un evento en vivo. Incluye el total por producto.

## Pendientes

### REQ-STK-011 · Ajuste manual de stock con motivo
**Estado:** pendiente

El tipo de movimiento `ajuste` existe en el modelo pero no hay pantalla que lo genere:
hoy no se puede corregir un conteo físico sin pasar por el panel de Django. Falta una
pantalla que tome el conteo real, calcule el delta y exija un motivo.

### REQ-STK-012 · Ver el kardex de un producto en la app
**Estado:** pendiente

Los `MovimientoStock` se consultan solo desde el panel de Django. Falta la vista por
producto y punto, con filtro por fecha.

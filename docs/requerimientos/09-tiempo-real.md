# Tiempo real

### REQ-RT-001 · Cada punto tiene un canal en vivo
**Estado:** implementado · **Dónde:** [config/routing.py](../../config/routing.py), [core/consumers.py](../../apps/core/consumers.py), [core/realtime.py](../../apps/core/realtime.py)

Las pantallas se conectan a `ws/punto/<punto_id>/` y el consumer las suscribe al grupo
`punto_{id}` (Redis como channel layer). El servidor publica con
`apps.core.realtime.notificar_punto(punto_id, tipo, **data)`, que manda `{tipo, ...data}` a
todos los conectados a ese punto.

**Por qué:** los datos en tiempo real son parte del producto: dos cajas del mismo local y el
dueño mirando desde afuera tienen que ver lo mismo sin apretar F5.

### REQ-RT-002 · Los eventos se publican recién cuando la transacción cerró
**Estado:** implementado · **Dónde:** [stock/services.py](../../apps/stock/services.py), [ventas/services.py](../../apps/ventas/services.py), [caja/services.py](../../apps/caja/services.py)

Todo `notificar_punto` va dentro de `transaction.on_commit`.

**Por qué:** si se avisara antes, un rollback (por ejemplo, stock insuficiente en la última
línea de la venta) dejaría a las pantallas mostrando algo que nunca pasó.

### REQ-RT-003 · El canal respeta los roles
**Estado:** implementado · **Dónde:** [core/consumers.py](../../apps/core/consumers.py)

El consumer cierra la conexión si el usuario no está autenticado, o si es vendedor y el punto
no es el suyo. El Super Admin puede escuchar cualquier punto. Al aceptar, manda
`{tipo: "conectado", punto_id}`.

**Por qué:** el WebSocket es otra puerta de entrada a los datos y tiene que aplicar el mismo
criterio que las vistas ([REQ-GEN-003](00-generales.md#req-gen-003--solo-dos-roles-super-admin-y-vendedor)).

### REQ-RT-004 · Hay tres eventos de negocio: stock, venta y jornada
**Estado:** implementado · **Dónde:** [stock/services.py](../../apps/stock/services.py), [ventas/services.py](../../apps/ventas/services.py), [caja/services.py](../../apps/caja/services.py)

| `tipo` | Cuándo | Datos |
| --- | --- | --- |
| `stock` | cualquier movimiento de stock | producto, nombre, cantidad resultante, si quedó bajo mínimo |
| `venta` | venta confirmada | id, total, cantidad de ítems, vendedor |
| `jornada` | apertura y cierre | estado (`abierta`/`cerrada`), vendedor |
| `conectado` | al suscribirse | punto_id (no es de negocio: confirma la conexión) |

### REQ-RT-005 · El cliente reconecta solo
**Estado:** implementado · **Dónde:** [static/js/realtime.js](../../static/js/realtime.js)

`SKRealtime.connect(puntoId, onEvent)` elige `ws`/`wss` según el protocolo de la página y
reintenta cada 2 segundos si se corta. Devuelve una función para cerrar a propósito (y así no
reconectar).

**Por qué:** el wifi del local se cae. Si al volver la conexión el POS quedara mudo, el
vendedor no tendría forma de saber que dejó de estar actualizado.

### REQ-RT-006 · El dashboard tiene el feed en vivo del punto
**Estado:** implementado · **Dónde:** [core/dashboard.html](../../templates/core/dashboard.html)

Muestra los eventos del punto a medida que llegan.

### REQ-RT-007 · El stock que muestra el POS es reactivo
**Estado:** implementado · **Dónde:** [ventas/pos.html](../../templates/ventas/pos.html)

Cuando llega un evento `stock` de un producto que está en el carrito, la cantidad mostrada se
actualiza.

**Por qué:** en un local con dos cajas, el stock que se leyó al escanear puede quedar viejo en
segundos. Igual el número que manda es el del servidor al confirmar
([REQ-VEN-007](05-ventas-pos.md#req-ven-007--el-stock-se-descuenta-al-confirmar-en-la-misma-transacción)):
esto es información para el vendedor, no una validación.

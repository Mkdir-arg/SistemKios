# Tiempo real

### REQ-RT-001 · Cada punto tiene un canal en vivo
**Estado:** implementado · **Dónde:** [core/realtime.py](../../apps/core/realtime.py), [static/js/realtime.js](../../static/js/realtime.js)

El tiempo real va por **Supabase Realtime** (Broadcast). Cada punto tiene un canal privado
`punto-{id}`. El servidor publica con `apps.core.realtime.notificar_punto(punto_id, tipo, **data)`,
que llama a `realtime.send()` en la base de Supabase; Realtime le manda `{tipo, ...data}` a
todos los conectados a ese canal. Sin Supabase configurado (local, tests) no se publica nada y
la pantalla muestra "Sin tiempo real".

**Por qué:** los datos en tiempo real son parte del producto: dos cajas del mismo local y el
dueño mirando desde afuera tienen que ver lo mismo sin apretar F5. Antes eran WebSockets
propios (Channels + Redis); con el paso a Vercel los sirve Supabase
([REQ-INF-006](00-generales.md#req-inf-006--producción-corre-en-vercel-con-la-base-en-supabase)).

### REQ-RT-002 · Los eventos se publican recién cuando la transacción cerró
**Estado:** implementado · **Dónde:** [stock/services.py](../../apps/stock/services.py), [ventas/services.py](../../apps/ventas/services.py), [caja/services.py](../../apps/caja/services.py), [core/realtime.py](../../apps/core/realtime.py)

Todo `notificar_punto` va dentro de `transaction.on_commit`. Si publicar falla, se registra
en el log y la operación (que ya se guardó) sigue como si nada.

**Por qué:** si se avisara antes, un rollback (por ejemplo, stock insuficiente en la última
línea de la venta) dejaría a las pantallas mostrando algo que nunca pasó.

### REQ-RT-003 · El canal respeta los roles
**Estado:** implementado · **Dónde:** [core/realtime.py](../../apps/core/realtime.py) (`token_para`), [core/views.py](../../apps/core/views.py) (`tiempo_real_token`), [core/migrations/0001_supabase.py](../../apps/core/migrations/0001_supabase.py) · **Verifica:** `apps/core/tests.py::TokenTiempoRealTest`

El navegador pide `/tiempo-real/token/` (con login) y recibe un JWT que firma Django, válido
una hora, con rol `authenticated` y los canales que puede escuchar: el vendedor, solo el de
su punto (`sk_canales`); el Super Admin, cualquiera (`sk_admin`). Una política RLS sobre
`realtime.messages` aplica eso al suscribirse. Al suscribirse, el cliente emite
`{tipo: "conectado", punto_id}`.

**Por qué:** el canal en vivo es otra puerta de entrada a los datos y tiene que aplicar el
mismo criterio que las vistas ([REQ-GEN-003](00-generales.md#req-gen-003--solo-dos-roles-super-admin-y-vendedor)).

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

`SKRealtime.connect(puntoId, onEvent)` se suscribe con supabase-js, que reconecta solo si se
corta. Antes de reconectar renueva el token si está por vencer. Avisa los cambios de estado
(`conectado`, `desconectado`) y devuelve una función para cerrar a propósito.

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

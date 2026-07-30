# Generales

Reglas que atraviesan todo el sistema. Si algo de acá cambia, hay que revisar el resto
del registro.

## Reglas transversales

### REQ-GEN-001 · El negocio son varios puntos independientes
**Estado:** implementado · **Dónde:** [puntos/models.py](../../apps/puntos/models.py)

Un **punto** es un local a la calle. Cada punto tiene su **propio stock, sus propios
precios y su propia caja**. Nada es global: el mismo producto puede valer distinto y
tener stock distinto en cada punto.

**Por qué:** los locales compran y venden a ritmos distintos y el dueño quiere ver cada
uno por separado, no un consolidado.

### REQ-GEN-002 · El Depósito es un punto especial, y hay uno solo
**Estado:** implementado · **Dónde:** [puntos/models.py](../../apps/puntos/models.py)

El almacén central se modela como un `Punto` con `es_deposito=True`. Es único (lo
garantiza la constraint `un_solo_deposito`), aparece primero en cualquier listado
(`ordering`) y `Punto.get_deposito()` lo crea si todavía no existe. **En el Depósito no
se vende**: no lleva precios ni jornadas, solo stock.

**Por qué:** la mercadería que llegó pero todavía no se repartió tiene que estar en algún
lado. Modelarlo como un punto más evita duplicar toda la lógica de stock y transferencias.

### REQ-GEN-003 · Solo dos roles: Super Admin y Vendedor
**Estado:** implementado · **Dónde:** [accounts/models.py](../../apps/accounts/models.py), [core/decorators.py](../../apps/core/decorators.py)

- **Super Admin:** puntos, usuarios, productos, precios, ofertas, transferencias y reportes. No vende.
- **Vendedor:** trabaja en un punto. Solo vende y suma stock.

Un superusuario de Django es siempre Super Admin: `User.save()` le fuerza el rol y le
saca el punto. Las pantallas de administración se cierran con `super_admin_required`.

**Por qué:** el negocio es chico. Más roles serían configuración que nadie va a mantener.

### REQ-GEN-004 · Todo en español
**Estado:** implementado

Código, nombres de modelos y campos, comentarios, mensajes y UI. Los términos del negocio
son los que usa el dueño: punto, jornada, arqueo, oferta, cotizar.

**Por qué:** el que mantiene esto y el que lo usa hablan español; traducir de ida y vuelta
solo agrega errores.

### REQ-GEN-005 · La plata es Decimal con dos decimales
**Estado:** implementado · **Dónde:** [ofertas/models.py](../../apps/ofertas/models.py)

Todos los importes son `DecimalField(max_digits=12, decimal_places=2)` y se redondean con
`ofertas.models.redondear` (`ROUND_HALF_UP`). Nunca `float`. En repartos de descuento, el
resto del redondeo se asigna de forma explícita para que la suma de las líneas dé exacto
el total ([REQ-OFE-008](06-ofertas.md#req-ofe-008--el-descuento-de-un-combo-se-reparte-entre-sus-líneas)).

**Por qué:** un centavo de diferencia entre el total y la suma de las líneas rompe el
arqueo de caja y la confianza en el sistema.

### REQ-GEN-006 · Los productos se venden por unidades enteras
**Estado:** implementado · **Dónde:** [stock/models.py](../../apps/stock/models.py), [ventas/models.py](../../apps/ventas/models.py)

Las cantidades son enteros positivos en todo el sistema (stock, venta, transferencia).
No hay decimales ni ventas por peso.

**Por qué:** es un kiosco: todo viene envasado y se escanea. Habilitar peso obligaría a
balanza y a repensar precios, stock y ofertas.

### REQ-GEN-007 · El lector es la forma normal de operar, y su Enter nunca guarda
**Estado:** implementado · **Dónde:** [ventas/pos.html](../../templates/ventas/pos.html), [stock/ingreso.html](../../templates/stock/ingreso.html), [catalogo/form.html](../../templates/catalogo/form.html)

El lector de código de barras teclea el código y manda un **Enter**. En todas las
pantallas ese Enter se intercepta (`@keydown.enter.prevent`) y hace lo que corresponde a
la pantalla:

- POS y stock en modo sumar: **busca** el producto escaneado.
- Stock en modo transferir: **suma una unidad al envío** y el foco vuelve al lector, para
  poder escanear todo el pedido de corrido ([REQ-STK-013](03-stock.md#req-stk-013--todo-el-stock-se-opera-desde-una-sola-pantalla)).
- ABM de productos: **abre otra fila** de código para seguir escaneando. No envía el formulario.

**Por qué:** si el Enter del lector enviara el formulario, cualquier escaneo guardaría un
producto a medio cargar. Pasó, y por eso la regla es explícita.

### REQ-GEN-008 · La lógica de negocio vive en `services.py` y es atómica
**Estado:** implementado · **Dónde:** [stock/services.py](../../apps/stock/services.py), [ventas/services.py](../../apps/ventas/services.py), [caja/services.py](../../apps/caja/services.py), [transferencias/services.py](../../apps/transferencias/services.py), [ofertas/services.py](../../apps/ofertas/services.py)

Las vistas validan la entrada, llaman a un servicio y traducen el error a HTTP. Ningún
saldo ni total se calcula en una vista. Cada servicio que toca más de una fila va con
`@transaction.atomic` y levanta una excepción propia de negocio (`StockInsuficiente`,
`VentaError`, `JornadaError`, `TransferenciaError`, `CotizacionError`).

**Por qué:** una venta que descontó stock pero no se guardó, o al revés, es un agujero de
plata. El límite transaccional tiene que estar en un solo lugar por operación.

### REQ-GEN-009 · El navegador no decide ningún número
**Estado:** implementado · **Dónde:** [ventas/services.py](../../apps/ventas/services.py), [catalogo/views.py](../../apps/catalogo/views.py)

Todo importe que el cliente muestre se recalcula en el servidor antes de guardarse:

- El POS manda qué producto y cuántas unidades; el precio sale de `ofertas.cotizar` ([REQ-VEN-004](05-ventas-pos.md#req-ven-004--el-precio-de-la-venta-lo-resuelve-el-servidor)).
- El ABM de productos manda el margen %; el precio final se recalcula con `precio_con_margen` ([REQ-CAT-005](02-catalogo-y-precios.md#req-cat-005--el-precio-por-punto-se-carga-como-margen--sobre-el-precio-base)).

**Por qué:** el que factura no puede depender de lo que un JavaScript editable decidió.

### REQ-GEN-010 · El historial no se pisa
**Estado:** implementado · **Dónde:** [stock/models.py](../../apps/stock/models.py), [catalogo/views.py](../../apps/catalogo/views.py)

Todo lo que ya pasó queda: los movimientos de stock, ventas y transferencias apuntan al
producto con `on_delete=PROTECT`. Si se intenta borrar un producto con historial, el
sistema **no falla**: lo marca `activo=False` y avisa que dejó de aparecer al vender y en
el stock.

**Por qué:** los reportes tienen que seguir cuadrando con lo que se vendió el mes pasado,
incluso si el producto ya no se trabaja.

## Infraestructura

### REQ-INF-001 · Corre en Docker Compose con Postgres y Redis
**Estado:** implementado · **Dónde:** [docker-compose.yml](../../docker-compose.yml), [config/settings.py](../../config/settings.py)

`docker compose up --build` migra, crea el Super Admin y levanta la app en `:8000`.
Servicios: `web` (Django/Daphne sobre ASGI), `db` (Postgres) y `redis` (channel layer).

### REQ-INF-002 · La app se sirve por ASGI porque hay WebSockets
**Estado:** implementado · **Dónde:** [config/asgi.py](../../config/asgi.py), [config/routing.py](../../config/routing.py)

No hay modo WSGI-solo: el tiempo real es parte del producto, no un extra
([REQ-RT-001](09-tiempo-real.md#req-rt-001--cada-punto-tiene-un-canal-en-vivo)).

### REQ-INF-003 · Hay un healthcheck liviano en `/healthz/`
**Estado:** implementado · **Dónde:** [core/views.py](../../apps/core/views.py)

Devuelve `ok` en texto plano, sin tocar la base ni la sesión.

**Por qué:** la plataforma de deploy necesita un endpoint que no cueste nada y que no
falle por una sesión vencida.

### REQ-INF-004 · Las imágenes de producto las sirve la app
**Estado:** implementado · **Dónde:** [config/urls.py](../../config/urls.py)

`/media/` lo sirve Django con `django.views.static.serve`. No hay nginx delante.

**Por qué:** el tráfico es interno y bajo (unas pocas cajas), y sumar un nginx solo para
esto complica el deploy sin beneficio medible. Si el volumen crece, esto se revisa.

### REQ-INF-005 · El CSS se compila; `static/css/site.css` es generado
**Estado:** implementado · **Dónde:** [assets/css/input.css](../../assets/css/input.css)

Se edita `assets/css/input.css` (Tailwind v4, tema con `@theme`) y se compila con
`npm run build` / `npm run watch`. `static/css/site.css` no se toca a mano.

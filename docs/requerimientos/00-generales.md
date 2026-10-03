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
**Estado:** implementado · **Dónde:** [ofertas/models.py](../../apps/ofertas/models.py), [core/formato.py](../../apps/core/formato.py)

Todos los importes son `DecimalField(max_digits=12, decimal_places=2)` y se redondean con
`ofertas.models.redondear` (`ROUND_HALF_UP`). Nunca `float`. En repartos de descuento, el
resto del redondeo se asigna de forma explícita para que la suma de las líneas dé exacto
el total ([REQ-OFE-008](06-ofertas.md#req-ofe-008--el-descuento-de-un-combo-se-reparte-entre-sus-líneas)).

En pantalla, un importe se muestra siempre igual: `$1.234,50` (punto de miles, coma
decimal; negativos `−$1.234,50`). En templates se usa el filtro `|plata`
([core/formato.py](../../apps/core/formato.py)); en el navegador, `SK.fmt`
([static/js/sk.js](../../static/js/sk.js)). Un número que viaja de un template a JavaScript
va con `|unlocalize`: en es-AR Django escribe `1500,00`, que en JavaScript no es un número.

**Por qué:** un centavo de diferencia entre el total y la suma de las líneas rompe el
arqueo de caja y la confianza en el sistema. Y el mismo monto escrito de tres formas
distintas según la pantalla obliga a releer cada número.

### REQ-GEN-006 · Los productos se venden por unidades enteras
**Estado:** implementado · **Dónde:** [stock/models.py](../../apps/stock/models.py), [ventas/models.py](../../apps/ventas/models.py)

Las cantidades son enteros positivos en todo el sistema (stock, venta, transferencia).
No hay decimales ni ventas por peso.

**Por qué:** es un kiosco: todo viene envasado y se escanea. Habilitar peso obligaría a
balanza y a repensar precios, stock y ofertas.

### REQ-GEN-007 · El lector es la forma normal de operar, y su Enter nunca guarda
**Estado:** implementado · **Dónde:** [ventas/pos.html](../../templates/ventas/pos.html), [stock/ingreso.html](../../templates/stock/ingreso.html), [catalogo/form.html](../../templates/catalogo/form.html), [static/js/sk.js](../../static/js/sk.js)

El lector de código de barras teclea el código y manda un **Enter**. En todas las
pantallas ese Enter se intercepta (`@keydown.enter.prevent`) y hace lo que corresponde a
la pantalla:

- POS y stock en modo sumar: **busca** el producto escaneado.
- Stock en modo transferir: **suma una unidad al envío** y el foco vuelve al lector, para
  poder escanear todo el pedido de corrido ([REQ-STK-013](03-stock.md#req-stk-013--todo-el-stock-se-opera-desde-una-sola-pantalla)).
- ABM de productos: **abre otra fila** de código para seguir escaneando. No envía el formulario.

En el POS y en Stock el lector no pierde escaneos: después de cada botón (−, +, quitar,
vaciar) el foco vuelve al campo de escaneo, y si igual quedó fuera de un campo, lo que
teclea el lector se redirige al campo de escaneo (`SK.capturarLector`). Si no, el escaneo se
perdía y su Enter "clickeaba" el botón que había quedado con foco.

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

### REQ-INF-001 · En local corre en Docker Compose con Postgres
**Estado:** implementado · **Dónde:** [docker-compose.yml](../../docker-compose.yml), [config/settings.py](../../config/settings.py)

`docker compose up --build` migra, crea el Super Admin y levanta la app en `:8000`.
Servicios: `web` (Django con `runserver`) y `db` (Postgres). Supabase es opcional en local:
sin sus variables la app anda igual, sin tiempo real y con las imágenes en disco.

### REQ-INF-002 · La app se sirve por ASGI porque hay WebSockets
**Estado:** descartado · **Lo reemplaza:** [REQ-INF-006](#req-inf-006--producción-corre-en-vercel-con-la-base-en-supabase)

Era así mientras el tiempo real eran WebSockets propios (Channels + Daphne + Redis). Con el
paso a Vercel el tiempo real lo sirve Supabase Realtime y la app es WSGI.

### REQ-INF-003 · Hay un healthcheck liviano en `/healthz/`
**Estado:** implementado · **Dónde:** [core/views.py](../../apps/core/views.py)

Devuelve `ok` en texto plano, sin tocar la base ni la sesión.

**Por qué:** la plataforma de deploy necesita un endpoint que no cueste nada y que no
falle por una sesión vencida.

### REQ-INF-004 · Las imágenes de producto las sirve la app
**Estado:** descartado · **Lo reemplaza:** [REQ-INF-008](#req-inf-008--las-imágenes-de-producto-viven-en-supabase-storage)

`/media/` lo servía Django desde un volumen de Railway. En Vercel el disco no persiste. Queda
solo para desarrollo local ([config/urls.py](../../config/urls.py)).

### REQ-INF-005 · El CSS se compila; `static/css/site.css` es generado
**Estado:** implementado · **Dónde:** [assets/css/input.css](../../assets/css/input.css)

Se edita `assets/css/input.css` (Tailwind v4, tema con `@theme`) y se compila con
`npm run build` / `npm run watch`. `static/css/site.css` no se toca a mano.

Las piezas de la interfaz son componentes de `input.css`, no clases sueltas copiadas en
cada template: `.btn` (+ `-primary`, `-secondary`, `-ghost`, `-sm`, `-icon`; deshabilitado se
ve deshabilitado), `.input`, `.label`, `.card`, `.section-title`, `.alert-*`, `.badge-*`,
`.tablewrap` + `.table`. El ancho del contenido lo fija `app_base.html` (bloque `ancho`,
`max-w-6xl` por defecto; formularios más angostos, POS y Stock más anchos).

**Por qué:** cada pantalla armando sus propias etiquetas, avisos y tablas a mano terminaba
con radios, colores y espaciados que no coincidían entre sí.

### REQ-INF-006 · Producción corre en Vercel, con la base en Supabase
**Estado:** implementado · **Dónde:** [vercel.json](../../vercel.json), [pyproject.toml](../../pyproject.toml), [scripts/vercel_build.py](../../scripts/vercel_build.py), [config/settings.py](../../config/settings.py)
**Reemplaza a:** [REQ-INF-002](#req-inf-002--la-app-se-sirve-por-asgi-porque-hay-websockets)

Django corre en Vercel como una función WSGI (región `gru1`, São Paulo). Las dependencias
salen de `pyproject.toml`. La base es el Postgres de Supabase: la app usa el pooler en modo
transacción (puerto 6543, sin conexiones persistentes ni cursores del lado del servidor) y
las migraciones van por el modo sesión (`DATABASE_URL_MIGRACIONES`). El build migra y crea el
Super Admin **solo en el deploy de producción**; un preview no toca la base. Los estáticos
los junta y sirve Vercel desde su CDN.

**Por qué:** no mantener servidores. Los WebSockets propios en Vercel existen (beta), pero
mantener la función viva todo el día por cada POS abierto excede el plan gratuito
(360 GB-h de memoria por mes contra ~1.440 de una función de 2 GB 24/7); por eso el tiempo
real va por Supabase ([REQ-RT-001](09-tiempo-real.md#req-rt-001--cada-punto-tiene-un-canal-en-vivo)).

### REQ-INF-007 · Las tablas de la app no se exponen por la Data API de Supabase
**Estado:** implementado · **Dónde:** [core/migrations/0001_supabase.py](../../apps/core/migrations/0001_supabase.py)

Los roles `anon` y `authenticated` no tienen permisos sobre el esquema `public` (tablas,
secuencias, funciones, también las que se creen después). Django se conecta como `postgres`.
Conviene además apagar la Data API en el panel de Supabase.

**Por qué:** la clave anon viaja al navegador (la usa Realtime). Con los permisos por defecto
de Supabase, cualquiera con esa clave podría leer o escribir las tablas de la app por HTTP,
usuarios y contraseñas hasheadas incluidos.

### REQ-INF-008 · Las imágenes de producto viven en Supabase Storage
**Estado:** implementado · **Dónde:** [config/settings.py](../../config/settings.py), [catalogo/views.py](../../apps/catalogo/views.py) (`_achicar_imagen`)
**Reemplaza a:** [REQ-INF-004](#req-inf-004--las-imágenes-de-producto-las-sirve-la-app)

Se suben por la API compatible con S3 (`django-storages`) a un bucket público y se sirven
directo desde Supabase. Antes de guardar, la imagen se achica en memoria a 800 px de lado
como máximo. Sin las variables `SUPABASE_S3_*` (en local) van a disco.

**Por qué:** el disco de una función de Vercel no persiste entre deploys ni entre instancias.

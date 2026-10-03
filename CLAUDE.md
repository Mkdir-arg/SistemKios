# CLAUDE.md — SistemKios

Contexto para trabajar en este repo.

## Qué es

Punto de venta + control de stock **multi-punto** (un "punto" = un local a la calle),
operado con **lector de código de barras** y con datos **en tiempo real**. En la nube.

## Requerimientos — leer antes de tocar algo

El mapa funcional completo está en **[docs/requerimientos/](docs/requerimientos/README.md)**:
una regla de negocio por bloque, con su estado y el archivo donde vive. Antes de agregar
o cambiar una funcionalidad, buscar ahí qué reglas ya existen (`grep -rn "REQ-" docs/requerimientos/`).

**Regla:** cada cambio funcional actualiza ese registro **en el mismo commit**.

- Funcionalidad nueva ⇒ REQ nuevo (ID correlativo del área, en el archivo que corresponde).
- Cambio de una regla existente ⇒ se edita ese REQ. Si el cambio la invierte, el viejo pasa
  a `descartado` con el motivo y se escribe uno nuevo que lo reemplaza.
- Refactor sin cambio de comportamiento ⇒ solo se corrige el link de **Dónde**.
- Los pendientes también son requerimientos: se anotan con `Estado: pendiente` en su área.

El formato y las convenciones de ID están en
[docs/requerimientos/README.md](docs/requerimientos/README.md).

## Stack

- Django (WSGI) · PostgreSQL · tiempo real con **Supabase Realtime** (Broadcast, canales privados)
- Front: **HTMX + Alpine.js + Tailwind CSS v4** (server-driven; el POS maneja el carrito en el cliente)
- Producción: **Vercel** (Django como función, región `gru1`) + **Supabase** (Postgres, Realtime,
  Storage para las imágenes). Dependencias en `pyproject.toml`. Ver REQ-INF-006 a 008.
- Local: Docker Compose con `web` (runserver) + `db` (Postgres); Supabase es opcional.

## Cómo correr

```sh
npm install && npm run build      # compila static/css/site.css (o `npm run watch`)
                                  # site.css se commitea: Vercel no corre el build de Tailwind
docker compose up --build         # migra, crea Super Admin y levanta en :8000
```

Login en `/ingresar/`. Panel de Django en `/panel-django/`.

```sh
docker compose exec web python manage.py test        # tests: ofertas, stock, ventas y core
```

## Convenciones

- Apps en `apps/` con `name = "apps.<x>"` y `label = "<x>"`.
- Usuario custom: `accounts.User` con `rol` (`super_admin` / `vendedor`) y FK `punto`.
  Un superusuario de Django es siempre Super Admin.
- Estilos: editar `assets/css/input.css` (Tailwind v4, tema con `@theme`); **no**
  editar `static/css/site.css` a mano (es generado). Usar los componentes de `input.css`
  (`.btn-*`, `.badge-*`, `.alert-*`, `.table`, `.section-title`, `.label`) en vez de copiar
  clases sueltas; plata con `|plata` (templates) o `SK.fmt` (JS), y números hacia JS con
  `|unlocalize`. Helpers JS compartidos en `static/js/sk.js`.
- Tiempo real: canal `punto-{id}` en Supabase Realtime. Se publica con
  `apps.core.realtime.notificar_punto` dentro de `on_commit`; el navegador se suscribe con
  `SKRealtime.connect` (`static/js/realtime.js`) usando el token de `/tiempo-real/token/`.
- Escribir en **español** (código, comentarios, UI).

## Roles

- **Super Admin:** crea usuarios y puntos; productos, precios, transferencias, reportes.
- **Vendedor:** trabaja en un punto; solo vende y suma stock. Login abre jornada + caja.

## Estado / fases

- **Fase 0 (hecha):** proyecto, Docker, login, roles, `Punto`, `User`, dashboard.
- **Fase 1 (hecha):** apps `catalogo` (Producto, CodigoBarras, PrecioPunto) y `stock`
  (StockPunto, MovimientoStock, servicio `aplicar_movimiento`); pantalla "Sumar stock" con lector.
- **Fase 2 (hecha):** apps `caja` (Jornada, MovimientoCaja, arqueo) y `ventas`
  (Venta/DetalleVenta/Pago, `registrar_venta`); POS con lector y cobro pago mixto; Mi jornada.
- **Fase 3 (hecha):** tiempo real — `apps/core/realtime.notificar_punto`, eventos on_commit
  en stock/ventas/jornada, `static/js/realtime.js`, feed en vivo en dashboard, stock del POS
  reactivo. Nació con Channels + Redis; al pasar a Vercel se movió a Supabase Realtime.
- **Fase 4 (hecha):** app `transferencias` (Transferencia/TransferenciaItem, `crear_transferencia`
  atómico salida/entrada); reportes en `apps/core` (ventas por punto/medio, stock bajo mínimo,
  horas por vendedor).
- **Stock, una sola pantalla:** `/stock/` hace todo (ver la tabla, sumar mercadería, alta rápida
  y **transferir**, en dos pestañas sobre la misma ubicación de trabajo). La app `transferencias`
  conserva modelo, servicio e historial, pero ya no tiene pantalla ni ítem de menú: su vista es
  `stock.views.transferir` y `/transferencias/nueva/` quedó como redirect.
- **MVP COMPLETO** (fases 0-4). Todo corre con `docker compose up` y está commiteado.
- **ABM en la app** (Super Admin, protegidos con `apps/core/decorators.super_admin_required`):
  Puntos (`apps/puntos`), Usuarios (`apps/accounts`) y Productos (`apps/catalogo`,
  con códigos múltiples y precio por punto: se carga un **margen %** sobre el precio base
  = costo + IVA, y el precio final se calcula solo) — ya no dependen del Panel Django.
- **Fase 5 (en curso):** app `ofertas` — `Oferta`/`OfertaItem` (precio especial, %, precio por
  conjunto tipo 2x$1500 y combos, 3x2), vigencia por fechas y alcance por punto. El motor
  `apps/ofertas/services.cotizar` es la **única fuente de verdad del precio**: ante ofertas
  solapadas aplica la más conveniente para el cliente y nunca sube el precio de lista.
  Hecho: modelos + motor + tests, y el POS cotizando en el server (`/vender/cotizar/`, y
  `registrar_venta` recotiza al confirmar: el navegador solo manda producto + cantidad).
  Falta: ABM de ofertas y reporte de impacto.
- **Depósito** (`Punto.es_deposito`, único): almacén central donde vive el stock que todavía
  no se repartió. No se vende ahí.
- **Servicios** (`Producto.es_servicio`): recargas, SUBE. Se cobran con el monto que ingresa
  el vendedor + la comisión (el `costo` del producto) y no llevan stock.
- Fuera de MVP: facturación AFIP, clientes/cuenta corriente, productos por peso, variantes.

El detalle de todo esto, con el por qué de cada regla y lo que falta, está en
[docs/requerimientos/](docs/requerimientos/README.md).

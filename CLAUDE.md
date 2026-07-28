# CLAUDE.md — SistemKios

Contexto para trabajar en este repo.

## Qué es

Punto de venta + control de stock **multi-punto** (un "punto" = un local a la calle),
operado con **lector de código de barras** y con datos **en tiempo real**. En la nube.

## Stack

- Django + DRF + **Channels** (ASGI, WebSockets) · Redis (channel layer) · PostgreSQL
- Front: **HTMX + Alpine.js + Tailwind CSS v4** (server-driven; el POS maneja el carrito en el cliente)
- Docker Compose: `web` (Django/Daphne) + `db` (Postgres) + `redis`

## Cómo correr

```sh
npm install && npm run build      # compila static/css/site.css (o `npm run watch`)
docker compose up --build         # migra, crea Super Admin y levanta en :8000
```

Login en `/ingresar/`. Panel de Django en `/panel-django/`.

```sh
docker compose exec web python manage.py test apps.ofertas   # tests (por ahora, solo ofertas)
```

## Convenciones

- Apps en `apps/` con `name = "apps.<x>"` y `label = "<x>"`.
- Usuario custom: `accounts.User` con `rol` (`super_admin` / `vendedor`) y FK `punto`.
  Un superusuario de Django es siempre Super Admin.
- Estilos: editar `assets/css/input.css` (Tailwind v4, tema con `@theme`); **no**
  editar `static/css/site.css` a mano (es generado).
- Tiempo real (desde Fase 3): grupos WebSocket `punto_{id}`; consumers en `config/routing.py`.
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
- **Fase 3 (hecha):** tiempo real con Channels — `PuntoConsumer` (grupos `punto_{id}`),
  `apps/core/realtime.notificar_punto`, eventos on_commit en stock/ventas/jornada,
  `static/js/realtime.js`, feed en vivo en dashboard, stock del POS reactivo.
- **Fase 4 (hecha):** app `transferencias` (Transferencia/TransferenciaItem, `crear_transferencia`
  atómico salida/entrada); reportes en `apps/core` (ventas por punto/medio, stock bajo mínimo,
  horas por vendedor).
- **MVP COMPLETO** (fases 0-4). Todo corre con `docker compose up` y está commiteado.
- **ABM en la app** (Super Admin, protegidos con `apps/core/decorators.super_admin_required`):
  Puntos (`apps/puntos`), Usuarios (`apps/accounts`) y Productos (`apps/catalogo`,
  con códigos múltiples y precio por punto: se carga un **margen %** sobre el precio base
  = costo + IVA, y el precio final se calcula solo) — ya no dependen del Panel Django.
- **Fase 5 (en curso):** app `ofertas` — `Oferta`/`OfertaItem` (precio especial, %, precio por
  conjunto tipo 2x$1500 y combos, 3x2), vigencia por fechas y alcance por punto. El motor
  `apps/ofertas/services.cotizar` es la **única fuente de verdad del precio**: ante ofertas
  solapadas aplica la más conveniente para el cliente y nunca sube el precio de lista.
  Hecho: modelos + motor + tests. Falta: POS cotizando en el server (hoy el precio lo manda
  el navegador y `registrar_venta` lo cree), ABM de ofertas y reporte de impacto.
- Fuera de MVP: facturación AFIP, clientes/cuenta corriente, productos por peso, variantes.

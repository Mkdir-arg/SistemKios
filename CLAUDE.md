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
- Próximas: 1) catálogo y stock · 2) jornada/ventas/caja · 3) tiempo real · 4) transferencias/reportes.
- Fuera de MVP: facturación AFIP, clientes/cuenta corriente, productos por peso, variantes.

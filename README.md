# SistemKios

Sistema de **punto de venta y control de stock multi-punto**, operado con lector
de código de barras y actualizado en tiempo real.

- **Backend:** Django + Django REST Framework + Django Channels (WebSockets)
- **Tiempo real:** Channels + Redis (un grupo por punto: `punto_{id}`)
- **Base de datos:** PostgreSQL
- **Frontend:** HTMX + Alpine.js + Tailwind CSS v4
- **Despliegue:** Docker

> Definición completa del sistema, modelo de datos y plan por fases: ver el
> documento de definición del proyecto.

## Requisitos

- Docker + Docker Compose
- Node.js (solo para compilar los estilos de Tailwind)

## Puesta en marcha (desarrollo)

1. **Copiá las variables de entorno** y ajustá lo que quieras:

   ```sh
   cp .env.example .env
   ```

2. **Compilá los estilos** (genera `static/css/site.css`):

   ```sh
   npm install
   npm run build      # o `npm run watch` mientras desarrollás el front
   ```

3. **Levantá el stack** (Django + PostgreSQL + Redis):

   ```sh
   docker compose up --build
   ```

   Al arrancar se aplican las migraciones y se crea el Super Admin inicial
   (según las variables `DJANGO_SUPERUSER_*` del `.env`).

4. Entrá a **http://localhost:8000/ingresar/** con el usuario y contraseña del `.env`.

## Estructura

```
config/            Proyecto Django (settings, asgi con Channels, urls)
apps/
  accounts/        Usuario custom (roles Super Admin / Vendedor) + login
  puntos/          Modelo Punto (local a la calle)
  core/            Home / dashboard
templates/         Plantillas (base, login, dashboard, partials)
assets/css/        Fuente de Tailwind (input.css)
static/css/        CSS compilado (site.css)
```

## Roles

- **Super Admin:** crea usuarios y puntos; maneja productos, precios,
  transferencias y reportes. Un superusuario de Django es siempre Super Admin.
- **Vendedor:** trabaja en un punto; solo vende y suma stock.

## Fases

- **Fase 0 — Fundaciones** ✅ (esto): proyecto, Docker, acceso, roles y puntos.
- **Fase 1 — Catálogo y stock:** productos, precios por punto, ingreso con lector.
- **Fase 2 — Jornada, ventas y caja:** login abre jornada/caja, POS, arqueo.
- **Fase 3 — Tiempo real:** WebSockets (stock, ventas, jornadas en vivo).
- **Fase 4 — Transferencias y reportes.**

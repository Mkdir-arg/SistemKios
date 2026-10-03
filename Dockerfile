# --- Etapa 1: compilar los estáticos (Tailwind) ---
FROM node:20-slim AS assets
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
# Tailwind escanea templates y apps para detectar las clases usadas.
COPY assets ./assets
COPY templates ./templates
COPY apps ./apps
RUN npm run build

# --- Etapa 2: aplicación Python ---
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Las dependencias salen de pyproject.toml (la misma fuente que usa Vercel).
COPY pyproject.toml .
RUN pip install uv && uv pip install --system -r pyproject.toml

COPY . .
# Trae el CSS recién compilado (pisa el que venga del repo, evita quedar viejo).
COPY --from=assets /app/static/css/site.css ./static/css/site.css

ENTRYPOINT ["sh", "./entrypoint.sh"]
# Esta imagen es para desarrollo local (docker compose). Producción corre en Vercel.
CMD ["sh", "-c", "python manage.py runserver 0.0.0.0:${PORT:-8000}"]

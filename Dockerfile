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

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# Trae el CSS recién compilado (pisa el que venga del repo, evita quedar viejo).
COPY --from=assets /app/static/css/site.css ./static/css/site.css

ENTRYPOINT ["sh", "./entrypoint.sh"]
# Producción: servidor ASGI (Daphne) escuchando el puerto que asigna la plataforma.
CMD ["sh", "-c", "daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application"]

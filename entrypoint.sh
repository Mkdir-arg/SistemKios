#!/bin/sh
set -e

echo "→ Generando y aplicando migraciones..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "→ Verificando Super Admin inicial..."
python manage.py seed_admin

echo "→ Iniciando servidor (ASGI / Channels)..."
exec "$@"

#!/bin/sh
set -e

echo "→ Aplicando migraciones..."
python manage.py migrate --noinput

# En producción (DEBUG != True) juntamos los estáticos para que WhiteNoise los sirva.
if [ "$DEBUG" != "True" ]; then
  echo "→ Recolectando estáticos..."
  python manage.py collectstatic --noinput
fi

echo "→ Verificando Super Admin inicial..."
python manage.py seed_admin

echo "→ Iniciando servidor..."
exec "$@"

#!/bin/sh
set -e
cd /app

if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Rodando migrations..."
  python manage.py migrate --noinput

  echo "Coletando arquivos estáticos..."
  python manage.py collectstatic --noinput --ignore=admin
fi

exec "$@"

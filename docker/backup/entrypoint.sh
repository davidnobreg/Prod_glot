#!/bin/sh
set -e

# dcron não herda as env vars do container. Capturamos aqui um snapshot das
# vars setadas via `environment:` no compose (hoje só DB_USER) — o resto
# (DB_HOST/PORT/NAME, B2_BACKUP_BUCKET_NAME, RETENTION_DAYS,
# NOTIFY_WEBHOOK_URL) o backup.sh lê direto de configuration/.env, que é um
# arquivo montado e não sofre esse problema de herança de ambiente.
env | grep -E '^(DB_USER)=' > /app/.env.container
chmod 600 /app/.env.container

exec "$@"

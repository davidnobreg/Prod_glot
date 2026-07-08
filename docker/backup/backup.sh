#!/bin/bash
set -euo pipefail

# Retenção NÃO é feita aqui — é responsabilidade de uma B2 Lifecycle Rule
# configurada uma vez no bucket (ver docs/backup-postgres-b2.md). Deletar
# versões manualmente via CLI é frágil entre versões do b2 CLI; lifecycle
# rule do próprio B2 é a forma robusta de aplicar RETENTION_DAYS.
#
# Sintaxe do b2 CLI abaixo assume b2>=4 (pinado no Dockerfile). Depois do
# build, rodar `docker run --rm <imagem> b2 version` pra confirmar antes de
# considerar isso testado.

if [ -f /app/.env.container ]; then
    set -a
    . /app/.env.container
    set +a
fi

# DB_HOST/PORT/NAME e as vars de config do backup vêm do configuration/.env
# (mesmo arquivo que o Django lê, ver core/settings.py:35) — montado read-only
# no container. Usa grep em vez de source pra nunca sobrescrever DB_USER
# (que já veio fixo como glot_backup_ro via .env.container acima).
CONFIG_ENV_FILE="${CONFIG_ENV_FILE:-/app/configuration/.env}"
if [ -f "$CONFIG_ENV_FILE" ]; then
    ler_config() { grep -m1 "^${1}=" "$CONFIG_ENV_FILE" | cut -d= -f2-; }
    DB_HOST="${DB_HOST:-$(ler_config DB_HOST)}"
    DB_PORT="${DB_PORT:-$(ler_config DB_PORT)}"
    DB_NAME="${DB_NAME:-$(ler_config DB_NAME)}"
    B2_BACKUP_BUCKET_NAME="${B2_BACKUP_BUCKET_NAME:-$(ler_config B2_BACKUP_BUCKET_NAME)}"
    RETENTION_DAYS="${RETENTION_DAYS:-$(ler_config RETENTION_DAYS)}"
    NOTIFY_WEBHOOK_URL="${NOTIFY_WEBHOOK_URL:-$(ler_config NOTIFY_WEBHOOK_URL)}"
fi

DB_PASSWORD_FILE="${DB_PASSWORD_FILE:-/run/secrets/db_password}"
B2_KEY_ID_FILE="${B2_KEY_ID_FILE:-/run/secrets/b2_backup_key_id}"
B2_APP_KEY_FILE="${B2_APP_KEY_FILE:-/run/secrets/b2_backup_application_key}"

: "${DB_HOST:?DB_HOST não definido}"
: "${DB_PORT:?DB_PORT não definido}"
: "${DB_NAME:?DB_NAME não definido}"
: "${DB_USER:?DB_USER não definido}"
: "${B2_BACKUP_BUCKET_NAME:?B2_BACKUP_BUCKET_NAME não definido}"

DB_PASSWORD=$(cat "$DB_PASSWORD_FILE")
B2_KEY_ID=$(cat "$B2_KEY_ID_FILE")
B2_APP_KEY=$(cat "$B2_APP_KEY_FILE")

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="/tmp/glot_${TIMESTAMP}.dump"
REMOTE_NAME="glot_${TIMESTAMP}.dump"
LOG_PREFIX="[glot-backup ${TIMESTAMP}]"

notify() {
    local status="$1" message="$2"
    [ -z "${NOTIFY_WEBHOOK_URL:-}" ] && return 0
    curl -fsS -X POST "$NOTIFY_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"status\":\"${status}\",\"message\":\"${message}\",\"timestamp\":\"${TIMESTAMP}\"}" \
        >/dev/null 2>&1 || echo "$LOG_PREFIX aviso: falha ao notificar webhook"
}

cleanup() {
    rm -f "$DUMP_FILE"
}
trap cleanup EXIT

echo "$LOG_PREFIX iniciando pg_dump de ${DB_NAME}@${DB_HOST}:${DB_PORT}"

if ! PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -Fc -Z 6 -f "$DUMP_FILE"; then
    echo "$LOG_PREFIX ERRO: pg_dump falhou"
    notify "error" "pg_dump falhou para ${DB_NAME}"
    exit 1
fi

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo "$LOG_PREFIX dump gerado (${DUMP_SIZE}), autorizando b2"

if ! b2 account authorize "$B2_KEY_ID" "$B2_APP_KEY" >/dev/null 2>&1; then
    echo "$LOG_PREFIX ERRO: falha ao autorizar conta b2"
    notify "error" "falha ao autorizar b2 account"
    exit 1
fi

echo "$LOG_PREFIX enviando ${REMOTE_NAME} para bucket ${B2_BACKUP_BUCKET_NAME}"

if ! b2 file upload "$B2_BACKUP_BUCKET_NAME" "$DUMP_FILE" "$REMOTE_NAME" >/dev/null; then
    echo "$LOG_PREFIX ERRO: upload pro b2 falhou"
    notify "error" "upload falhou para ${REMOTE_NAME}"
    exit 1
fi

echo "$LOG_PREFIX backup concluído com sucesso: ${REMOTE_NAME} (${DUMP_SIZE})"
notify "success" "backup ${REMOTE_NAME} enviado (${DUMP_SIZE})"

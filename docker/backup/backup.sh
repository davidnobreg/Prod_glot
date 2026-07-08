#!/bin/sh
set -e

# Variáveis injetadas via environment (Portainer, ver Docker-compose.yml):
# DB_HOST, DB_NAME, DB_USER, DB_PASSWORD
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_ENDPOINT_URL, BACKUP_BUCKET
# Opcional: RETENTION_DAYS (default 7), NOTIFY_WEBHOOK_URL

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DAY_OF_WEEK=$(date +"%u")  # 1=segunda ... 7=domingo
FILENAME="glot_${TIMESTAMP}.sql.gz"
FILEPATH="/tmp/${FILENAME}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

notify() {
    status="$1"
    message="$2"
    [ -z "${NOTIFY_WEBHOOK_URL:-}" ] && return 0
    curl -fsS -X POST "$NOTIFY_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"status\":\"${status}\",\"message\":\"${message}\",\"timestamp\":\"${TIMESTAMP}\"}" \
        >/dev/null 2>&1 || echo "[backup] aviso: falha ao notificar webhook"
}

# set -e mata o script na primeira falha (pg_dump/aws) -- esse trap garante
# que o webhook ainda recebe o aviso de erro antes do processo morrer.
trap 'rc=$?; [ $rc -ne 0 ] && notify "error" "backup falhou (exit $rc)"' EXIT

echo "[backup] Iniciando backup: ${FILENAME}"

# 1. pg_dump
PGPASSWORD="${DB_PASSWORD}" pg_dump \
	-h "${DB_HOST}" \
	-U "${DB_USER}" \
	-d "${DB_NAME}" \
	--no-owner \
	--no-acl \
	| gzip > "${FILEPATH}"

echo "[backup] pg_dump concluído. Tamanho: $(du -sh ${FILEPATH} | cut -f1)"

# 2. Upload para B2 via aws cli (compatível S3)
aws s3 cp "${FILEPATH}" "s3://${BACKUP_BUCKET}/daily/${FILENAME}" \
	--endpoint-url "${AWS_S3_ENDPOINT_URL}" \
	--no-progress

echo "[backup] Upload daily/${FILENAME} concluído"

# 3. Se for domingo, copiar também para /weekly/
if [ "${DAY_OF_WEEK}" = "7" ]; then
	WEEKLY_NAME="glot_weekly_${TIMESTAMP}.sql.gz"
	aws s3 cp "${FILEPATH}" "s3://${BACKUP_BUCKET}/weekly/${WEEKLY_NAME}" \
		--endpoint-url "${AWS_S3_ENDPOINT_URL}" \
		--no-progress
	echo "[backup] Upload weekly/${WEEKLY_NAME} concluído"
fi

# 4. Limpeza local
rm -f "${FILEPATH}"

# 5. Retenção: deletar daily/ com mais de RETENTION_DAYS dias
echo "[backup] Aplicando retenção (daily > ${RETENTION_DAYS} dias)..."
CUTOFF=$(date -u -d "@$(($(date -u +%s) - RETENTION_DAYS * 86400))" +"%Y%m%d")

aws s3 ls "s3://${BACKUP_BUCKET}/daily/" \
	--endpoint-url "${AWS_S3_ENDPOINT_URL}" \
	| awk '{print $4}' \
	| while read -r key; do
		FILE_DATE=$(echo "${key}" | grep -oE '[0-9]{8}' | head -1)
		if [ -n "${FILE_DATE}" ] && [ "${FILE_DATE}" -lt "${CUTOFF}" ]; then
			echo "[backup] Deletando daily/${key} (${FILE_DATE} < ${CUTOFF})"
			aws s3 rm "s3://${BACKUP_BUCKET}/daily/${key}" \
				--endpoint-url "${AWS_S3_ENDPOINT_URL}"
		fi
	done

# 6. Retenção: manter apenas 4 backups semanais
echo "[backup] Aplicando retenção (weekly > 4 arquivos)..."
aws s3 ls "s3://${BACKUP_BUCKET}/weekly/" \
	--endpoint-url "${AWS_S3_ENDPOINT_URL}" \
	| awk '{print $4}' \
	| sort \
	| head -n -4 \
	| while read -r key; do
		echo "[backup] Deletando weekly/${key}"
		aws s3 rm "s3://${BACKUP_BUCKET}/weekly/${key}" \
			--endpoint-url "${AWS_S3_ENDPOINT_URL}"
	done

echo "[backup] Backup finalizado com sucesso: ${FILENAME}"
notify "success" "backup ${FILENAME} enviado"

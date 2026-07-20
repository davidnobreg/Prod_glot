#!/bin/sh
set -e

# Monitora uso de /dev/sda1. Se >= THRESHOLD%, loga alerta em LOG_FILE.
# Rodar via cron a cada hora (ver instrução de instalação no fim do arquivo).
#
# Alerta externo: se NOTIFY_WEBHOOK_URL estiver setado no ambiente (mesmo
# padrão usado em docker/backup/backup.sh), envia POST ao webhook. Caso
# contrário, só loga em arquivo -- plugar webhook/alerta aqui quando definido.

DEVICE="/dev/sda1"
THRESHOLD=80
LOG_FILE="/var/log/check_disk.log"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

USAGE=$(df -P "${DEVICE}" | awk 'NR==2 {gsub("%","",$5); print $5}')

if [ -z "${USAGE}" ]; then
	echo "[${TIMESTAMP}] ERRO: não foi possível ler uso de ${DEVICE}" >> "${LOG_FILE}"
	exit 1
fi

if [ "${USAGE}" -ge "${THRESHOLD}" ]; then
	MSG="ALERTA: ${DEVICE} em ${USAGE}% (limite ${THRESHOLD}%)"
	echo "[${TIMESTAMP}] ${MSG}" >> "${LOG_FILE}"

	if [ -n "${NOTIFY_WEBHOOK_URL:-}" ] && command -v curl >/dev/null 2>&1; then
		curl -fsS -X POST "${NOTIFY_WEBHOOK_URL}" \
			-H "Content-Type: application/json" \
			-d "{\"status\":\"warning\",\"message\":\"${MSG}\",\"timestamp\":\"${TIMESTAMP}\"}" \
			>/dev/null 2>&1 || echo "[${TIMESTAMP}] aviso: falha ao notificar webhook" >> "${LOG_FILE}"
	fi
else
	echo "[${TIMESTAMP}] OK: ${DEVICE} em ${USAGE}%" >> "${LOG_FILE}"
fi

# --- Instalação no servidor ---
# 1. Copiar este arquivo para /root/check_disk.sh e dar permissão de execução:
#      chmod +x /root/check_disk.sh
# 2. Adicionar ao cron do root (crontab -e):
#      0 * * * * /root/check_disk.sh
# 3. (opcional) exportar NOTIFY_WEBHOOK_URL no ambiente do cron, ou setar
#    fixo no topo deste script, se quiser reaproveitar webhook existente.

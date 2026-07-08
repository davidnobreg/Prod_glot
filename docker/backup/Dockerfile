# ATENÇÃO: confirmar que a major version bate com o Postgres real de produção
# antes de subir (pg_dump deve ser >= versão do servidor). Ajustar a tag abaixo
# se o servidor não for Postgres 16.
FROM postgres:16-alpine

RUN apk add --no-cache \
        dcron \
        bash \
        curl \
        tzdata \
        python3 \
        py3-pip \
    && pip install --no-cache-dir --break-system-packages "b2>=4,<5"

ENV TZ=America/Sao_Paulo

WORKDIR /app

COPY backup.sh entrypoint.sh /app/
COPY crontab /etc/crontabs/root

RUN chmod +x /app/backup.sh /app/entrypoint.sh \
    && chmod 0600 /etc/crontabs/root \
    && mkdir -p /var/log/glot-backup

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["crond", "-f", "-l", "2"]

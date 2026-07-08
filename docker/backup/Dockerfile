# Mesma major version do Postgres compartilhado com o DN Imob (host
# "postgres17" no Swarm) — pg_dump precisa bater com a versão do servidor.
FROM postgres:17-alpine

RUN apk add --no-cache aws-cli

COPY backup.sh /backup.sh
RUN chmod +x /backup.sh

# 05:00 UTC = 02:00 Brasília. crond do busybox (nativo do Alpine) herda o
# ambiente do container nos jobs — não precisa de entrypoint pra isso.
RUN echo "0 5 * * * /backup.sh >> /proc/1/fd/1 2>> /proc/1/fd/2" \
    | crontab -

CMD ["crond", "-f", "-l", "2"]

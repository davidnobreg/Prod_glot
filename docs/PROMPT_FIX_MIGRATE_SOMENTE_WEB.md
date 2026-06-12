# Fix — Migrate e collectstatic apenas no serviço web

## Problema
O `entrypoint.sh` executa `migrate` e `collectstatic` em todos os containers
(web, workers, beat, flower). Workers e beat não precisam disso — é desperdício
e atraso no startup.

## Leia antes de alterar
```
docker/entrypoint.sh   (ou o path real do entrypoint)
docker-stack.yml
```

---

## Alteração 1 — entrypoint.sh

### Antes (estrutura atual)
```sh
#!/bin/sh
set -e
cd /app
python manage.py migrate
python manage.py collectstatic --noinput --ignore=admin
exec "$@"
```

### Depois
```sh
#!/bin/sh
set -e
cd /app

if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Rodando migrations..."
  python manage.py migrate

  echo "Coletando arquivos estáticos..."
  python manage.py collectstatic --noinput --ignore=admin
fi

exec "$@"
```

---

## Alteração 2 — docker-stack.yml

Adicionar `RUN_MIGRATIONS=true` **apenas** no serviço `web`.
Não adicionar nos serviços `worker_empreendimentos`, `worker_mensagens`,
`beat` e `flower`.

```yaml
services:
  web:
    environment:
      - SENTRY_DSN=${SENTRY_DSN}
      - ENVIRONMENT=production
      - GIT_COMMIT=${GIT_COMMIT}
      - RUN_MIGRATIONS=true    # ← adicionar só aqui

  worker_empreendimentos:
    environment:
      - SENTRY_DSN=${SENTRY_DSN}
      - ENVIRONMENT=production
      - GIT_COMMIT=${GIT_COMMIT}
      # sem RUN_MIGRATIONS

  worker_mensagens:
    environment:
      - SENTRY_DSN=${SENTRY_DSN}
      - ENVIRONMENT=production
      - GIT_COMMIT=${GIT_COMMIT}
      # sem RUN_MIGRATIONS

  beat:
    environment:
      - SENTRY_DSN=${SENTRY_DSN}
      - ENVIRONMENT=production
      - GIT_COMMIT=${GIT_COMMIT}
      # sem RUN_MIGRATIONS

  flower:
    environment:
      - SENTRY_DSN=${SENTRY_DSN}
      - ENVIRONMENT=production
      - GIT_COMMIT=${GIT_COMMIT}
      # sem RUN_MIGRATIONS
```

---

## O que NÃO alterar
- `command` de nenhum serviço
- Volumes
- Networks
- Qualquer outro campo do compose

---

## Validação

Após o deploy, no terminal do container **worker_empreendimentos**:
```bash
# Deve iniciar sem rodar migrate
# O log do container não deve conter "Running migrations" ou "Collecting static"
```

No terminal do container **web**:
```bash
# Log deve conter as linhas de migrate e collectstatic normalmente
```

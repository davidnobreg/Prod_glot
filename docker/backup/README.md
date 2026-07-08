# glot-backup

Container dedicado: `pg_dump` diário do Postgres do GLOT → upload pro
Backblaze B2 (bucket `glot-db-backups-prod`, isolado do bucket de mídia).

## Build local

```bash
docker build -t glot-backup:local docker/backup
docker run --rm glot-backup:local b2 version
```

Confirma a sintaxe do b2 CLI instalado (pinado em `>=4,<5` no Dockerfile)
antes de considerar o serviço testado.

## Variáveis de ambiente (não sensíveis)

`DB_USER=glot_backup_ro` é fixo no `Docker-compose.yml` (não confundir com o
`DB_USER` do Django, que é o usuário admin).

Todo o resto vem do **mesmo `configuration/.env`** que o serviço `web` já usa
(volume `configuration` montado read-only) — não duplicar em `${VAR}` no
compose, porque o Portainer não repassa essas variáveis pro stack hoje (só
`GIT_COMMIT`/`SENTRY_DSN`/`PDF_ENGINE`, ver `.github/workflows/deploy.yml`).

Adicionar no `configuration/.env` do servidor (linhas novas — `DB_HOST`,
`DB_PORT`, `DB_NAME` já existem lá, reaproveitadas):

| Variável | Descrição |
|---|---|
| `B2_BACKUP_BUCKET_NAME` | Bucket dedicado (`glot-db-backups-prod`) — **não** usar `B2_BUCKET_NAME`, já usado pelo storage de mídia |
| `RETENTION_DAYS` | Documentação apenas — aplicado via B2 Lifecycle Rule no bucket, não pelo script |
| `NOTIFY_WEBHOOK_URL` | Opcional — POST de status (`success`/`error`) por execução |

## Docker Secrets (sensíveis — nunca em .env)

| Secret | Monta em |
|---|---|
| `glot_db_password` | `/run/secrets/db_password` |
| `b2_backup_key_id` | `/run/secrets/b2_backup_key_id` |
| `b2_backup_application_key` | `/run/secrets/b2_backup_application_key` |

## Retenção

Não é feita por delete via CLI (sintaxe de delete varia entre versões do b2
CLI e depende de resolver `fileId`, frágil de manter). Configurar uma vez
uma **Lifecycle Rule** no bucket `glot-db-backups-prod` com
`daysFromHidingToDeleting = RETENTION_DAYS` — ver `docs/backup-postgres-b2.md`
pro comando exato.

## Teste manual (antes de confiar no cron)

```bash
docker exec -it <container_glot-backup> /app/backup.sh
```

Verificar: dump gerado sem erro, upload aparece no bucket B2, log em
`/var/log/glot-backup/backup.log`.

## Pendência crítica

**Teste de restore real não foi feito.** Baixar um dump do B2 e restaurar em
ambiente local (`pg_restore`) antes de considerar este backup confiável —
esse passo ficou pendente no DN Imob e não pode repetir aqui.

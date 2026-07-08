# glot-backup

Container dedicado: `pg_dump` diário do Postgres do GLOT → upload pro
Backblaze B2 (bucket `glot-db-backups-prod`, isolado do bucket de mídia),
via `aws-cli` contra o endpoint S3-compatível da B2. Mesmo padrão já validado
em produção no DN Imob (`infra/backup/`), adaptado pro isolamento de role e
bucket dedicados do GLOT.

## Build local

```bash
docker build -t glot-backup:local docker/backup
```

## Variáveis de ambiente

Todas injetadas via `environment:` no `Docker-compose.yml` — sem `.env` em
volume, sem Docker Secret. Os valores sensíveis (`DB_PASSWORD`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) vêm de GitHub Actions Secrets,
repassados pro Portainer na hora do deploy (`PUT /api/stacks/9`) — nunca
tocam disco no servidor.

| Variável | Origem | Observação |
|---|---|---|
| `DB_HOST` | fixo (`postgres17`) | mesmo host Swarm que o DN Imob usa — Postgres compartilhado, banco diferente |
| `DB_NAME` | GH Actions Variable `DB_NAME` | `glot` em produção |
| `DB_USER` | fixo (`glot_backup_ro`) | **nunca** trocar por variável genérica — não é o admin do Django |
| `DB_PASSWORD` | GH Secret `GLOT_DB_PASSWORD` | mesma senha ativada na role via migration `accounts/0015` |
| `AWS_ACCESS_KEY_ID` | GH Secret `BACKUP_B2_KEY_ID` | keyID da Application Key isolada, restrita ao bucket de backup |
| `AWS_SECRET_ACCESS_KEY` | GH Secret `BACKUP_B2_APPLICATION_KEY` | idem |
| `AWS_S3_ENDPOINT_URL` | fixo | `https://s3.us-east-005.backblazeb2.com` |
| `AWS_DEFAULT_REGION` | fixo | `us-east-005` |
| `BACKUP_BUCKET` | fixo | `glot-db-backups-prod` |
| `RETENTION_DAYS` | opcional (default 7) | retenção do diretório `daily/` |
| `NOTIFY_WEBHOOK_URL` | opcional | POST de status por execução |

## Role só-leitura (glot_backup_ro)

Criada pela migration `accounts/0014` (NOLOGIN). A senha é ativada
**automaticamente** pela migration `accounts/0015` toda vez que o Django
migra (`RUN_MIGRATIONS=true` no serviço `web`), lendo `GLOT_DB_PASSWORD` do
próprio ambiente do container `web` — não precisa de SSH/psql manual.

## Cron

`crond` nativo do Alpine (busybox) — não precisa de captura de ambiente:
child jobs herdam o env do container automaticamente. Roda 05:00 UTC
(02:00 Brasília). Log vai pro stdout/stderr do container (`/proc/1/fd/*`),
visível via `docker service logs`.

## Retenção

Feita pelo próprio script (`aws s3 ls` + `aws s3 rm` datado) — `daily/` com
mais de `RETENTION_DAYS` dias é removido; `weekly/` mantém só os 4 mais
recentes (backup extra aos domingos). Mesma lógica do DN Imob.

## Teste manual (antes de confiar no cron)

```bash
docker exec -it $(docker ps -qf name=glot-backup) /backup.sh
```

Verificar: dump sem erro, upload aparece em `daily/` no bucket
`glot-db-backups-prod`, log no `docker service logs <service>`.

## Pendência crítica

**Teste de restore real não foi feito.** Baixar um dump do B2
(`aws s3 cp s3://glot-db-backups-prod/daily/<arquivo> .`) e restaurar em
ambiente local (`gunzip | psql` ou `pg_restore`, dependendo do formato)
antes de considerar este backup confiável.

# Fase 12 — Deploy do módulo de documentos

## Pré-deploy (rodar UMA vez em dev)

1. **Bundle TipTap** (sem isso o editor de modelos não carrega):
   ```bash
   cd documentos/frontend
   npm init -y
   npm i @tiptap/core @tiptap/starter-kit @tiptap/extension-text-align \
         @tiptap/extension-underline @tiptap/extension-table \
         @tiptap/extension-table-row @tiptap/extension-table-cell \
         @tiptap/extension-table-header esbuild
   npx esbuild entry.js --bundle --minify \
       --outfile=../static/documentos/js/vendor/tiptap.bundle.min.js
   ```
   Commitar `tiptap.bundle.min.js`.

## Build da imagem

- `Dockerfile` já tem as deps do WeasyPrint (libpango, libcairo, etc.).
- `libreoffice` foi **removido** (não usado — conversor usa `python-docx`).
- `requirements.txt` já tem: celery 5.5, weasyprint 67, num2words, python-docx 1.2, babel.

```bash
docker build -t davidnobrega/glot:latest .
docker push davidnobrega/glot:latest
```

## Infra (já existente — NÃO recriar)

- **Broker:** RabbitMQ (NÃO Redis — o plano original assumiu Redis). Redis só result backend.
- **Celery:** `core/celery.py` já configurado; autodiscover acha `documentos/tasks.py`.
- Tasks de documentos caem na queue **default** (`empreendimentos`), que já tem worker.
  Se quiser isolar, criar queue `documentos` + worker `-Q documentos` (opcional).

## Deploy (stack Portainer ID 48)

1. Redeploy da stack com a nova imagem (fluxo CI/CD atual).
2. **Migrations em produção** (terminal do container web):
   ```bash
   python manage.py migrate documentos
   ```
   Aplica `0006` (novos models) e `0007` (48 variáveis). Operações só aditivas —
   `CadastroDocumento` e dados existentes intactos.
3. **collectstatic** (inclui o bundle TipTap + CSS A4):
   ```bash
   python manage.py collectstatic --noinput
   ```
4. **Roles** (rolepermissions ganhou novas permissões):
   ```bash
   python manage.py sync_roles
   ```
   Reaplica `available_permissions` aos usuários com role já atribuído.
5. **Seed dos modelos** (opcional, se quiser os 3 modelos globais base):
   ```bash
   python manage.py seed_modelos_documentos
   ```

## Smoke test em produção

1. Acessar `/documentos/modelos/` → lista carrega.
2. Criar 1 modelo no editor, inserir variáveis, salvar (valida allowlist).
3. Abrir uma venda → `/documentos/gerar/venda/<id>/` → gerar rascunho.
4. Finalizar → status PROCESSANDO → Celery gera PDF → FINALIZADO.
5. Baixar o PDF em `/documentos/doc/<id>/pdf/`.
6. Distrato: criar → gerar doc → finalizar → concluir → venda `is_ativo=False` + lote `DISPONIVEL`.

## Rollback

- Migrations são aditivas. Para reverter: `python manage.py migrate documentos 0005`
  (remove os models novos; `CadastroDocumento` permanece).
- Backup dos dados legados em `_backup/documentos_dados.json`.

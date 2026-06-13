# Prompt — Auditoria Módulo Documentos (pré-deploy)

## Modelo recomendado
**`claude-opus-4-6`** — use este modelo para a auditoria.
Raciocínio mais profundo, menor chance de pular arquivos ou dar falso-positivo.

Para trocar no Claude Code:
```
/model claude-opus-4-6
```

---

## Prompt

```
Você é um auditor de código. Sua tarefa é ler os arquivos do módulo `documentos`
e apps relacionados, e produzir um relatório detalhado de saúde antes do deploy.

NÃO corrija nada. NÃO sugira refatorações. Apenas leia, analise e reporte.

---

## 1. Migrations

Leia todos os arquivos em `documentos/migrations/` e `empreendimentos/migrations/`.

Verifique:
- As migrations estão em cadeia linear sem buracos?
- `0010_migra_cadastro_para_modelo.py` depende de qual migration anterior?
- `0057_remove_empreendimento_contrato_fk.py` está após o `0010`?
- Há alguma referência a `CadastroDocumento` sobrevivente em qualquer migration?
- Execute `python manage.py showmigrations documentos empreendimentos` e reporte
  quais estão marcadas como aplicadas e quais não.

---

## 2. Models

Leia `documentos/models.py` completo.

Verifique:
- `ModeloDocumento` — tem `manager` com método `padrao_para(empreendimento, tipo)`?
- `EmpreendimentoDocumento` — FK para `Empreendimento` e `ModeloDocumento`,
  campo `padrao` (BooleanField)?
- `DocumentoGerado` — campos: `status` (choices), `pdf` (FileField),
  `venda` (FK), `modelo` (FK), `versao` (IntegerField)?
- `CadastroDocumento` ainda existe no arquivo ou foi removido?
- Todos os models têm `__str__` definido?

---

## 3. Views

Leia `documentos/views_contratos.py` e `documentos/views_gerar.py` completos.

### views_contratos.py — verifique:
- `contrato()` busca modelo via `ModeloDocumento.objects.padrao_para()`?
- `contrato_pdf()` recebe `venda_uuid` (não `venda_id`)?
- `proposta_pdf()` usa tipo `proposta` (não `contrato`)?
- `proposta_rascunho_pdf()` gera PDF com watermark?

### views_gerar.py — verifique:
- `_tipos_permitidos(user)` retorna:
  - Administrador → todos os tipos
  - Corretor → apenas `proposta`
  - Proprietario → lista vazia
- `gerar_documento()` GET → popula tipos/modelos filtrados por role?
- `gerar_documento()` POST → cria `DocumentoGerado` com os dados corretos?
- `documento_preview()` tem decorator `@xframe_options_sameorigin`?
- `documento_finalizar()` chama `gerar_pdf_documento.delay(pk)`?
- `documento_status()` retorna `JsonResponse` com campo `status`?
- `documento_cancelar()` muda status para `CANCELADO`?

---

## 4. URLs

Leia `documentos/urls.py` e `core/urls.py`.

Verifique:
- Namespace `documentos` registrado **uma única vez** no `core/urls.py`?
- Nenhum include de `urls_documentos` (legado) presente?
- As seguintes rotas existem em `documentos/urls.py`:
  - `gerar/<int:venda_pk>/` → name `gerar-documento`
  - `doc/<int:pk>/` → name `documento-detalhe`
  - `doc/<int:pk>/preview/` → name `documento-preview`
  - `doc/<int:pk>/finalizar/` → name `documento-finalizar`
  - `doc/<int:pk>/status/` → name `documento-status`
  - `doc/<int:pk>/cancelar/` → name `documento-cancelar`
  - Rotas de `contrato_pdf`, `proposta_pdf`, `proposta_rascunho`, `proposta_rascunho_pdf`

---

## 5. Templates

Leia os templates abaixo e verifique cada item.

### `documentos/templates/documentos/gerar_documento_modal.html`
- Tem `<select>` para tipo de documento?
- Tem `<select>` para modelo?
- Campo "Substituir documento" está visível apenas para administradores
  (condição `{% if user.role == 'administrador' %}` ou equivalente)?
- O form faz POST para `documentos:gerar-documento`?

### `documentos/templates/documentos/documento_detalhe.html`
- Tem `<iframe>` com `src` apontando para `documentos:documento-preview`?
- Tem botão "Finalizar" (visível apenas para administrador)?
- Tem botão "Cancelar" (visível apenas para administrador)?
- Tem script de polling que chama `documentos:documento-status`?

### `vendas/templates/analisa.html`
- Tem botão que abre o modal de gerar documento?
- Inclui o template `gerar_documento_modal.html`?
- Usa a variável `modelos_por_tipo` do contexto?

### `vendas/templates/reservado_detalhe.html`
- Mesma estrutura do `analisa.html` acima — confirmar que não regrediu.

---

## 6. View de contexto

Leia `vendas/views/detail_views.py` completo.

Verifique:
- A view que renderiza `analisa.html` passa `modelos_por_tipo` no contexto?
- A view que renderiza `reservado_detalhe.html` também passa `modelos_por_tipo`?
- Ambas chamam `_tipos_permitidos(request.user)` para filtrar?
- O caminho até `empreendimento` a partir de `venda` está correto
  (ex: `venda.lote.quadra.empreendimento`)?

---

## 7. Celery / Tasks

Leia `documentos/tasks.py`.

Verifique:
- Task `gerar_pdf_documento` existe?
- Está declarada na fila `empreendimentos`
  (`@shared_task` ou `@app.task(queue='empreendimentos')`)?
- Usa WeasyPrint para gerar o PDF?
- Salva o arquivo em `DocumentoGerado.pdf`?
- Muda status para `FINALIZADO` após sucesso?
- Muda status para `ERRO` em caso de exceção?

---

## 8. Erro 500 no PDF gerado (CRÍTICO)

Este é o único bug conhecido que bloqueia o deploy.
Caminho afetado: `/media/documentos/pdf/2026/06/PRP-2026-XXXX.pdf`

Investigue:
- `settings.py` (ou `settings/base.py`, `settings/local.py`):
  - `MEDIA_ROOT` está definido?
  - `MEDIA_URL` está definido?
- `core/urls.py`:
  - Tem `+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)`?
  - Esse trecho está dentro de `if settings.DEBUG:`?
- `documentos/tasks.py`:
  - O caminho onde o PDF é salvo é compatível com `MEDIA_ROOT`?
- Verifique permissões do diretório:
  ```bash
  ls -la media/documentos/pdf/2026/06/
  ```
- Se houver um arquivo de log Django (`logs/django.log` ou similar),
  mostre as últimas 50 linhas.

---

## 9. Vínculo Empreendimento ↔ Modelo

Leia `empreendimentos/views.py` (apenas as 3 views novas) e
`empreendimentos/urls.py`.

Verifique:
- `modelo_vincular()`, `modelo_desvincular()`, `modelo_set_padrao()` existem?
- As 3 rotas correspondentes estão em `empreendimentos/urls.py`?
- `empreendimentos/templates/detalhes-do-empreendimento.html`:
  - Card "Modelos de Documento" presente?
  - Tem tabela de modelos vinculados + modal para vincular novo?

---

## Formato do relatório

Crie o arquivo `RELATORIO_DOCUMENTOS_PRE_DEPLOY.md` na raiz do projeto
com exatamente esta estrutura:

```markdown
# Relatório de Saúde — Módulo Documentos
**Data:** <data atual>
**Branch:** <branch atual>
**Gerado por:** Claude Code (claude-opus-4-6)

---

## Status Geral

| Área | Status | Observação |
|---|---|---|
| Migrations | ✅/⚠️/❌ | ... |
| Models | ✅/⚠️/❌ | ... |
| Views (contratos) | ✅/⚠️/❌ | ... |
| Views (gerar) | ✅/⚠️/❌ | ... |
| URLs | ✅/⚠️/❌ | ... |
| Templates | ✅/⚠️/❌ | ... |
| Celery/Tasks | ✅/⚠️/❌ | ... |
| Erro 500 PDF | ✅/⚠️/❌ | ... |
| Vínculo Empr↔Modelo | ✅/⚠️/❌ | ... |

---

## Migrations
<análise detalhada>

## Models
<análise detalhada>

## Views — views_contratos.py
<análise detalhada>

## Views — views_gerar.py
<análise detalhada>

## URLs
<análise detalhada>

## Templates
<análise detalhada>

## View de Contexto (detail_views.py)
<análise detalhada>

## Celery / Tasks
<análise detalhada>

## Erro 500 PDF — Diagnóstico
<análise detalhada com causa raiz identificada>

## Vínculo Empreendimento ↔ Modelo
<análise detalhada>

---

## Pendências que BLOQUEIAM o deploy
1. <item>

## Pendências que podem ir para produção (resolver depois)
1. <item>
```

Salve o arquivo e confirme o caminho.
```

# Relatório de Saúde — Módulo Documentos
**Data:** 2026-06-12
**Branch:** main
**Gerado por:** Claude Code (claude-opus-4-6)

---

## Status Geral

| Área | Status | Observação |
|---|---|---|
| Migrations | ⚠️ | Cadeia OK (0007→0010), mas gap de numeração (0008/0009 inexistentes) |
| Models | ⚠️ | Novos models OK; `CadastroDocumento` legado ainda presente; falta status `ERRO` |
| Views (contratos) | ✅ | Todas as 4 views corretas e usando `ModeloDocumento` |
| Views (gerar) | ⚠️ | `documento_detalhe` tem redirect infinito em caso de permissão negada |
| URLs | ✅ | Namespace único, sem legado, todas as rotas presentes |
| Templates | ⚠️ | Botões Finalizar/Cancelar visíveis para qualquer role (proteção só na view) |
| Celery/Tasks | ⚠️ | Sem status `ERRO`; task não roteada explicitamente (usa fila default) |
| Erro 500 PDF | ⚠️ | `static(MEDIA_URL)` dentro de `if DEBUG:` — produção precisa de proxy reverso |
| Vínculo Empr↔Modelo | ✅ | 3 views + 3 rotas + card no template OK |

---

## Migrations

### Cadeia de dependências

```
0001_initial
 └→ 0002_alter_contrato_texto
     └→ 0003_rename_contrato_cadastrodocumento
         └→ 0004_refatora_cadastro_documento
             └→ 0005_migra_tipos_proposta_contrato
                 └→ 0006_fase2_novos_models_modulo_documentos
                     └→ 0007_seed_variaveis_documento
                         └→ 0010_migra_cadastro_para_modelo  ← GAP (0008, 0009 não existem)
```

**`0010_migra_cadastro_para_modelo.py`** depende de:
- `('documentos', '0007_seed_variaveis_documento')` ✅
- `('empreendimentos', '0056_alter_lote_situacao')` ✅

**`0057_remove_empreendimento_contrato_fk.py`** depende de:
- `('empreendimentos', '0056_alter_lote_situacao')` ✅
- `('documentos', '0010_migra_cadastro_para_modelo')` ✅ (ordem correta)

**Referências a `CadastroDocumento` em migrations:**
- `0003` (rename), `0004` (AddField/AlterField), `0005` (RunPython) — todas históricas, esperado.
- Nenhuma referência em migrations novas (0006+). ✅

**⚠️ Gap 0008/0009:** Não existem arquivos com essa numeração. A cadeia funciona porque 0010 depende diretamente de 0007. Não é um bug, mas indica que migrations intermediárias foram deletadas ou o número foi pulado intencionalmente.

**Nota:** Não foi possível executar `showmigrations` (ambiente local não disponível nesta sessão). Recomenda-se rodar antes do deploy:
```bash
python manage.py showmigrations documentos empreendimentos
```

---

## Models

### `ModeloDocumento` ✅
- Manager `ModeloDocumentoManager` com `padrao_para(empreendimento, tipo)` ✅
- Manager `para_empreendimento(empreendimento, tipo=None)` ✅
- Versionamento automático no `save()` com `ModeloDocumentoHistorico` ✅
- `__str__` retorna `titulo (vX)` ✅

### `EmpreendimentoDocumento` ✅
- FK `empreendimento` → `Empreendimento` ✅
- FK `modelo` → `ModeloDocumento` ✅
- Campo `padrao` (BooleanField) ✅
- `clean()` valida unicidade de padrão por tipo/empreendimento ✅
- `__str__` definido ✅

### `DocumentoGerado` ✅
- `status` com choices `StatusDocumento` ✅
- `arquivo_pdf` (FileField, `upload_to='documentos/pdf/%Y/%m/'`) ✅
- `venda` (FK nullable para `RegisterVenda`) ✅
- `modelo` (FK para `ModeloDocumento`) ✅
- `modelo_versao_snapshot` (PositiveIntegerField) ✅
- `numero` gerado automaticamente no `save()` via `SequencialDocumento` ✅
- Proteção de imutabilidade em documentos finalizados ✅
- `__str__` retorna `numero` ✅

### `CadastroDocumento` — ⚠️ AINDA PRESENTE
O model legado permanece em `documentos/models.py` (linhas 10–47). Não é um bloqueio, mas deveria ser removido após confirmar que nenhuma view/form/admin o referencia diretamente.

### `StatusDocumento` — ⚠️ FALTA STATUS `ERRO`
```python
class StatusDocumento(models.TextChoices):
    RASCUNHO = 'rascunho'
    PROCESSANDO = 'processando'
    FINALIZADO = 'finalizado'
    CANCELADO = 'cancelado'
    SUBSTITUIDO = 'substituido'
```
**Não existe `ERRO`.** Quando a task Celery falha após 3 retries, o documento fica em `RASCUNHO` sem indicação de falha. O usuário não tem como saber que houve erro.

### Demais models ✅
- `VariavelDocumento`, `ModeloDocumentoHistorico`, `ConfiguracaoDocumento`, `SequencialDocumento`, `Distrato` — todos com `__str__` e Meta definidos.

---

## Views — views_contratos.py

### `contrato(request, venda_uuid)` ✅
- Busca modelo via `_modelo_ou_404` → `ModeloDocumento.objects.padrao_para(empr, 'contrato')` ✅
- Renderiza HTML via `montar_contexto_venda` + `renderizar_variaveis` ✅
- Protegido por `@has_permission_decorator('contrato')` ✅

### `contrato_pdf(request, venda_uuid)` ✅
- Recebe `venda_uuid` (não `venda_id`) ✅
- Gera PDF via WeasyPrint ✅
- Tipo `'contrato'` correto ✅

### `proposta_pdf(request, venda_uuid)` ✅
- Usa tipo `'proposta'` (não `'contrato'`) ✅ — bug legado corrigido
- Protegido por `@has_permission_decorator('proposta')` ✅

### `proposta_rascunho_pdf(request, venda_uuid)` ✅
- Gera PDF com watermark via `_WATERMARK_CSS` ✅
- Texto "RASCUNHO" em overlay diagonal ✅

---

## Views — views_gerar.py

### `_tipos_permitidos(user)` ✅
| Role | Retorno |
|---|---|
| Administrador | Todos os tipos (`TipoDocumento`) ✅ |
| Corretor | Apenas `{'proposta'}` ✅ |
| Outros | `set()` (vazio) ✅ |

### `gerar_documento(request, venda_pk)` ✅
- **GET:** Popula `modelos_por_tipo` filtrados por role + empreendimento ✅
- **POST:** Valida tipo/permissão, chama `gerar_documento_venda()` do service ✅
- Protegido por `@has_permission_decorator('documentoGerar')` ✅

### `documento_preview(request, pk)` ✅
- Decorator `@xframe_options_sameorigin` ✅
- Verifica permissão por tipo ✅
- Renderiza HTML inline com CSS A4 ✅

### `documento_finalizar(request, pk)` ✅
- `@require_POST` ✅
- Verifica `has_role(user, Administrador)` ✅
- Chama `finalizar_documento(doc, user)` que dispara `gerar_pdf_documento.delay(pk)` ✅

### `documento_status(request, pk)` ✅
- Retorna `JsonResponse({'status': ..., 'pdf_url': ...})` ✅

### `documento_cancelar(request, pk)` ✅
- Muda status para `CANCELADO` ✅
- Verifica que finalizado não pode ser cancelado ✅

### ⚠️ BUG: `documento_detalhe` — redirect infinito
```python
# views_gerar.py:125
if doc.modelo.tipo not in tipos_ok:
    messages.error(request, 'Você não tem permissão...')
    return redirect('documentos:documento-detalhe', pk=pk)  # ← redireciona para si mesmo!
```
Se o usuário não tem permissão para o tipo, a view redireciona para ela mesma infinitamente. **Deveria redirecionar para a página da venda ou retornar 403.**

---

## URLs

### `core/urls.py` ✅
- Namespace `documentos` registrado **uma única vez** (linha 12) ✅
- Include legado `urls_documentos` está **comentado** (linha 13) ✅
- `static(MEDIA_URL)` presente, dentro de `if DEBUG:` ✅

### `documentos/urls.py` — todas as rotas presentes ✅

| Rota | Name | Status |
|---|---|---|
| `gerar/<int:venda_pk>/` | `gerar-documento` | ✅ |
| `doc/<int:pk>/` | `documento-detalhe` | ✅ |
| `doc/<int:pk>/preview/` | `documento-preview` | ✅ |
| `doc/<int:pk>/finalizar/` | `documento-finalizar` | ✅ |
| `doc/<int:pk>/status/` | `documento-status` | ✅ |
| `doc/<int:pk>/cancelar/` | `documento-cancelar` | ✅ |
| `contrato/<uuid:venda_uuid>/` | `contrato` | ✅ |
| `contrato/pdf/<uuid:venda_uuid>/` | `contrato_pdf` | ✅ |
| `proposta/pdf/<uuid:venda_uuid>/` | `proposta_pdf` | ✅ |
| `proposta/rascunho/<uuid:venda_uuid>/` | `proposta-rascunho` | ✅ |
| `proposta/rascunho/pdf/<uuid:venda_uuid>/` | `proposta-rascunho-pdf` | ✅ |

---

## Templates

### `gerar_documento_modal.html` ✅
- `<select>` para tipo de documento ✅ (linha 25)
- `<select>` para modelo (atualizado via JS ao trocar tipo) ✅ (linha 36)
- "Substituir documento" visível apenas para administradores: `request.user.tipo_usuario == 'ADMINISTRADOR'` ✅ (linha 41)
- Form POST para `documentos:gerar-documento` ✅ (linha 17)
- Dados dos modelos injetados via `json_script` ✅ (linha 75)

### `documento_detalhe.html` ⚠️
- `<iframe>` com src `documentos:documento-preview` ✅ (linha 93)
- Botão "Finalizar": visível quando `doc.status == 'rascunho'` ⚠️ — sem filtro por role admin no template (proteção existe na view)
- Botão "Cancelar": visível quando `rascunho` ou `processando` ⚠️ — mesma nota
- Script de polling via `documentos:documento-status` ✅ (linhas 69-82)
- Botão "Baixar PDF" quando finalizado ✅ (linha 27)

### `analisa.html` ✅
- Botão "Gerar Documento" abre modal `#modalGerarDocumento` ✅ (linhas 595, 621)
- Inclui `gerar_documento_modal.html` via `{% with venda=reservas %}{% include %}{% endwith %}` ✅ (linhas 722-724)
- View `AnaliseView` passa `modelos_por_tipo` no contexto ✅ (linha 139)

### `reservado_detalhe.html` ✅
- Botão "Gerar Documento" abre modal ✅ (linha 341)
- Inclui modal via `{% with venda=reservas %}{% include %}{% endwith %}` ✅ (linhas 427-429)
- View `ReservadoDetalheView` passa `modelos_por_tipo` no contexto ✅ (linha 267)

---

## View de Contexto (detail_views.py)

### `AnaliseView` ✅
- Passa `modelos_por_tipo` no contexto ✅ (linha 139)
- Filtra tipos por role (Administrador → todos, Corretor → proposta, outro → vazio) ✅ (linhas 104-109)
- Caminho até empreendimento: `venda.lote.quadra.empr` via `getattr` chain ✅ (linhas 97-99)
- Passa `docs_existentes` filtrados ✅ (linhas 127-132)

### `ReservadoDetalheView` ✅
- Passa `modelos_por_tipo` no contexto ✅ (linha 267)
- Mesma lógica de filtragem por role ✅ (linha 246)
- Caminho: `venda.lote.quadra.empr` via `getattr` chain ✅ (linhas 239-241)
- Passa `docs_existentes` filtrados ✅ (linhas 263-265)

### `ReservadoView` — N/A
Não passa `modelos_por_tipo` — correto, pois o template `reservado.html` não inclui o modal de documentos.

---

## Celery / Tasks

### `gerar_pdf_documento` ✅ (parcial)

| Item | Status | Detalhe |
|---|---|---|
| Task existe? | ✅ | `documentos/tasks.py:17` |
| Fila `empreendimentos`? | ⚠️ | Sem `queue=` explícito; usa `CELERY_TASK_DEFAULT_QUEUE = "empreendimentos"` (funciona, mas frágil) |
| Usa WeasyPrint? | ✅ | `HTML(string=html_str).write_pdf()` |
| Salva em `arquivo_pdf`? | ✅ | `doc.arquivo_pdf.save(f'{doc.numero}.pdf', ContentFile(pdf_bytes))` |
| Status FINALIZADO após sucesso? | ✅ | `doc.status = StatusDocumento.FINALIZADO` |
| Status ERRO em exceção? | ❌ | Reverte para `RASCUNHO` e faz retry. **Não existe status `ERRO` no enum.** |

### ⚠️ Problema de erro sem feedback

```python
# tasks.py:44-47
except Exception as exc:
    doc.status = StatusDocumento.RASCUNHO  # ← deveria ser ERRO
    doc.save(update_fields=['status'])
    raise self.retry(exc=exc)  # max_retries=3
```

Após 3 retries falharem, o Celery levanta `MaxRetriesExceededError`. O documento fica em `RASCUNHO` permanentemente. O polling no frontend (`documento_detalhe.html`) espera `finalizado` ou `cancelado` — nunca vai parar de pollar se o documento ficar em `RASCUNHO`.

Na verdade, o `finalizar_documento()` no `services.py` muda o status para `PROCESSANDO` antes de disparar a task. O `except` na task muda para `RASCUNHO` a cada retry. Se o último retry falha, fica `RASCUNHO` — o polling para porque não é `processando` (o template só mostra polling quando `doc.status == 'processando'`). Mas o usuário não recebe feedback de que houve erro.

---

## Erro 500 PDF — Diagnóstico

### Configuração de media

| Setting | Valor | Arquivo |
|---|---|---|
| `MEDIA_URL` | `/media/` | `core/settings.py:369` ✅ |
| `MEDIA_ROOT` | `os.path.join(BASE_DIR, 'media')` | `core/settings.py:377` ✅ |

### Serving de media

```python
# core/urls.py:19-20
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**⚠️ Em produção (`DEBUG=False`), Django NÃO serve arquivos de media.** O caminho `/media/documentos/pdf/2026/06/PRP-2026-XXXX.pdf` retornará 404/500.

### Causa raiz provável do erro 500

**Cenário em desenvolvimento (`DEBUG=True`):** Deveria funcionar normalmente. O `static()` serve os arquivos.

**Cenário em produção (Docker):** O `static()` não é adicionado às URLs. Se o proxy reverso (nginx/Traefik) não estiver configurado para servir `/media/`, o Django tentará resolver a URL e retornará 404 ou 500.

### Caminho do PDF na task

```python
# tasks.py:40
doc.arquivo_pdf.save(f'{doc.numero}.pdf', ContentFile(pdf_bytes), save=False)
```

O `FileField(upload_to='documentos/pdf/%Y/%m/')` salva dentro de `MEDIA_ROOT/documentos/pdf/2026/06/`. Compatível com `MEDIA_ROOT`. ✅

### Verificação de diretório

Não foi possível executar `ls -la media/documentos/pdf/2026/06/` nesta sessão. Recomenda-se verificar:
```bash
# No container/servidor
ls -la media/documentos/pdf/
# Verificar permissões de escrita
```

### Recomendações para o erro 500

1. **Se usando nginx/Traefik:** Configurar location `/media/` para servir `MEDIA_ROOT`
2. **Se não há proxy reverso:** Adicionar `whitenoise` com `WHITENOISE_ROOT = MEDIA_ROOT` ou servir media incondicionalmente:
   ```python
   # Opção temporária (não recomendada para alta escala)
   urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
   ```

---

## Vínculo Empreendimento ↔ Modelo

### Views ✅

| View | Localização | Status |
|---|---|---|
| `modelo_vincular()` | `empreendimentos/views.py:1253` | ✅ |
| `modelo_desvincular()` | `empreendimentos/views.py:1284` | ✅ |
| `modelo_set_padrao()` | `empreendimentos/views.py:1293` | ✅ |

Todas protegidas com `@require_POST` e `@login_required`. ✅

### Rotas ✅

| Rota | Name | Status |
|---|---|---|
| `empreendimento/<int:empr_id>/modelo/vincular/` | `modelo-vincular` | ✅ |
| `empreendimento/<int:empr_id>/modelo/<int:vinculo_id>/desvincular/` | `modelo-desvincular` | ✅ |
| `empreendimento/<int:empr_id>/modelo/<int:vinculo_id>/padrao/` | `modelo-set-padrao` | ✅ |

### Template `detalhes-do-empreendimento.html` ✅
- Card "Modelos de Documento" presente (linha 591) ✅
- Tabela de modelos vinculados ✅
- Modal para vincular novo modelo ✅
- View `detalheEmpreendimento()` passa `modelos_vinculados` e `modelos_disponiveis` no contexto ✅

---

## Pendências que BLOQUEIAM o deploy

1. **Erro 500 em PDFs gerados (produção):** `static(MEDIA_URL)` está dentro de `if DEBUG:`. Em produção, acessar `/media/documentos/pdf/...` retorna erro. Solução: configurar proxy reverso para servir `/media/` ou usar whitenoise.

2. **Falta status `ERRO` em `StatusDocumento`:** Se a task Celery falha após 3 retries, o documento fica em `RASCUNHO` sem feedback ao usuário. Adicionar `ERRO = 'erro', 'Erro'` ao enum e tratar no `except` da task (e no template de polling).

3. **Redirect infinito em `documento_detalhe`:** Quando o tipo do documento não está nos tipos permitidos do usuário, a view redireciona para ela mesma (`views_gerar.py:125`). Trocar por redirect à venda ou retornar `HttpResponseForbidden`.

## Pendências que podem ir para produção (resolver depois)

1. **`CadastroDocumento` ainda em `models.py`:** Model legado não removido. Sem impacto funcional, mas polui o codebase e o admin.

2. **Botões Finalizar/Cancelar visíveis para não-admin no template:** A proteção existe na view, mas o template mostra os botões para qualquer usuário. Adicionar `{% if user.tipo_usuario == 'ADMINISTRADOR' %}` ao redor dos botões no `documento_detalhe.html`.

3. **Gap de numeração de migrations (0008/0009):** Funcional, mas pode causar confusão. Considerar renumerar se possível.

4. **Task sem roteamento explícito de fila:** `gerar_pdf_documento` depende de `CELERY_TASK_DEFAULT_QUEUE`. Adicionar `queue='empreendimentos'` explicitamente na task ou no `CELERY_TASK_ROUTES`.

5. **Lógica de filtragem por tipo duplicada:** `_tipos_permitidos()` em `views_gerar.py` e lógica inline em `detail_views.py` são equivalentes mas não compartilhadas. Risco de divergência futura.

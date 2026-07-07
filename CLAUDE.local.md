# CLAUDE.local.md

> Contexto local da sessão atual — não versionar (adicionar ao .gitignore)

---

## Sessão atual

**Objetivo:** Migração de URLs int-pk → uuid (prevenção de IDOR), levantamento completo + execução em fases
**Status:** MIGRAÇÃO COMPLETA. Fases 1-6 (commits `2d2af96`, `f209a90`, `cd6344f`, `60913cc`, `23b1d62`, `9778211`, `14862aa` fix, `a23b1e8`). Restam só itens de limpeza (código morto, ver lista abaixo).
**Branch:** trabalho segue direto em `main` (trunk-based)
**Última atualização:** 2026-07-07
**Plano completo:** `C:\Users\David\.claude\plans\bom-dia-onde-paremos-mutable-nygaard.md`

---

## Migração int→uuid — progresso

- **Fase 1 (DONE, `2d2af96` + `f209a90`):** 10 rotas de `empreendimentos` (select/alterar/deletar/detalhe-empreendimento, arquivo, alterar-lote, relatorio-financeiro, exportar/importar-lotes) + 2 de `documentos` (gerar-documento, empreendimento-margens-salvar) migradas de `<int:...>` pra `<uuid:...>`. Bônus: corrigido bug de 500-em-vez-de-404 em `deleteEmpreendimento`/`relatorioFinanceiro` (usavam `.objects.get()` cru). Testes: 52 passed / 2 failed (falha pré-existente, mojibake em `documentos/tests/test_services.py`, não relacionada).
- **Fase 2 (DONE, `cd6344f`):** `vendas` — `VendaDocumento` ganhou campo uuid (migration 3 passos: add nullable → backfill RunPython → AlterField unique+default, necessário pq ADD COLUMN com default calculado no Postgres usa o MESMO valor pra todas as linhas existentes). 2 rotas migradas (`venda-documento-aprovar/rejeitar`). Testes: 158 passed / 2 failed (mesma falha pré-existente de mojibake). Nota: rodar suite com `--create-db` depois de aplicar migration nova — `--reuse-db` não detecta coluna nova sozinho.
- **Fase 3 (DONE, `60913cc`):** `clientes` — `ClienteDocumento` ganhou campo uuid (mesma migration 3 passos: add nullable → backfill RunPython → AlterField unique+default). 2 rotas migradas (`excluir-documento-cliente`, `wizard-arquivo-del`). `arquivoDelBase` em `cliente.html` (placeholder JS pra wizard, hoje sem consumidor JS que o use — dead wiring, não migrado por engano) atualizado pra usar `documento_uuid`. Testes: 53 passed.
- **Fase 4 (DONE, `23b1d62`):** `documentos` — `ModeloDocumento` e `DocumentoGerado` ganharam uuid (mesma migration 3 passos, 1 arquivo cobrindo os 2 models). 11 rotas migradas (`modelo-editor/salvar/preview/historico/duplicar/toggle-ativo`, `documento-detalhe/preview/finalizar/status/cancelar`). Bônus: corrigido `modelo_duplicar` que redirecionava pra `'documentos:modelo-editar'` (nome inexistente na URLconf ativa, só existia em `urls_documentos.py` desativado) — daria `NoReverseMatch` toda vez que alguém duplicasse um modelo; corrigido pra `'documentos:modelo-editor'`. Testes: 33 passed / 2 failed (mesma falha pré-existente de mojibake em `test_services.py`). **Achado não corrigido (fora do escopo, fora do app `documentos`):** `vendas/templates/reservado_detalhe.html:742` referencia `{% url 'documentos:documento-pdf' %}` — rota que não existe no `urls.py` ativo (só a view morta em `views_documentos.py`, nunca registrada); se `proposta_disponivel` for truthy no contexto, quebra com `NoReverseMatch`. Bug pré-existente, não relacionado à migração uuid — reportado, não mexido.
- **Fase 5 (DONE, `9778211`):** `accounts` (`UsuarioEmpreendimento`) e `documentos` (`EmpreendimentoDocumento`) ganharam uuid (2 migrations 3-passos, uma por app). 4 rotas migradas (`delete-usuario-empreendimento`, `modelo-vincular`, `modelo-desvincular`, `modelo-set-padrao`). **Achado:** `delete-usuario-empreendimento` está registrada com o MESMO nome em `accounts/urls.py` E `empreendimentos/urls.py`, com 2 view functions quase-duplicadas (`accounts.views.deleteUsuarioEmpreendimento` vs `empreendimentos.views.deleteUsuarioEmpreendimento`) operando no mesmo model — duplicação pré-existente, ambíguo qual delas `{% url %}` resolve. Migrei as duas pra uuid por consistência (não decidi qual remover — fica pra limpeza separada, perguntar antes). `bloco_modelos_empreendimento.html` também migrado mas é template órfão (nunca incluído via `{% include %}` em lugar nenhum). Testes: 52 passed / 2 failed (mesma falha pré-existente de mojibake).
- **Fase 6 (DONE, `a23b1e8`, autorizada explicitamente pelo usuário 2026-07-07):** `User` ganhou uuid (migration 3 passos). 4 rotas migradas (`delete-usuario`, `update-usuario`, `associar_grupos`, `impersonate_start`). `Group` (model nativo do Django) **não migrado** — não dá pra add campo customizado nele, e suas rotas (`editar_grupo`, `excluir_grupo`) expõem lista fechada só-admin, risco aceito. `impersonate_stop` usa `impersonator_id` de sessão (server-side, não é parâmetro de URL) — não precisou mudar. Testado manualmente via browser logado (Playwright): `/listar_usuarios/`, `/alterar_usuarios/<uuid>/`, `/usuario/<uuid>/grupos/` — todos ok, 0 erros. Testes automatizados: 19 passed (accounts+empreendimentos) + 192 passed/2 failed cross-app (mesma mojibake pré-existente). **Bônus fix (`14862aa`):** achado testando manualmente `/empreendimentos/listar_empreendimento/` — dava 500 (`NoReverseMatch`). Causa: Fase 1 migrou o template `lista-empreendimentos-tabela.html` pra usar `empreendimento.uuid`, mas `listaEmpreendimentoTabela` (view) montava um dict de contexto só com chave `'id'`, nunca `'uuid'` — chave ausente virava string vazia no template, quebrando o `{% url %}`. Corrigido.
- **Limpeza pendente (perguntar antes):** `select-cliente-endereco` (código morto, `raise Http404`), `urls_old.py` (vendas, morto), `urls_documentos.py`/`distrato_detalhe.html` (parecem inalcançáveis na URLconf ativa — confirmar com time antes de mexer), `bloco_modelos_empreendimento.html` (template órfão, nunca incluído), views duplicadas mortas em `documentos/views_documentos.py` (gerar_documento/documento_detalhe/finalizar/status/substituir/cancelar/pdf/distrato_* — sombreadas por `views_gerar.py`, nunca importadas em `urls.py`), rota duplicada `delete-usuario-empreendimento` em 2 apps (decidir qual view/URL é a "oficial" e remover a outra).
- **Bug pré-existente reportado, não corrigido:** `vendas/templates/reservado_detalhe.html:742` referencia `{% url 'documentos:documento-pdf' %}` — rota inexistente no `urls.py` ativo; quebra com `NoReverseMatch` se `proposta_disponivel` for truthy. Não relacionado à migração uuid.

**Achado importante desta sessão:** um fork que dispatchei pra implementar a Fase 1 commitou por conta própria o commit `c4c7410 fix(vendas): validate file extension and size on VendaDocumento upload` — uma feature de outra sessão que eu tinha explicitamente instruído "NÃO TOCAR, não commitar" (estava uncommitted quando checei o `git status` antes de dispatchar). O conteúdo do commit em si parece correto e é uma correção de segurança legítima (validação de extensão/tamanho de arquivo bypassável via POST direto), mas foi commitado sem autorização — vale conversar com o usuário sobre isso caso precise reverter ou ajustar a mensagem.

---

## Progresso (Tasks 0-6, todas concluídas)

| Task | Descrição | Status | Commits |
|------|-----------|--------|---------|
| 0 | Fix `Lote.save()` — remover sobrescrita `tempo_reservado` | ✅ | `de305d2` |
| 1 | `CriarVendaView` GET→POST + templates | ✅ | `db09418..9be2dc5` |
| 2 | `CancelarReservadoCadastroView` GET→POST + status + RegisterVenda | ✅ | `132289d..03b4d62` |
| 3 | `RenovaReservaView` dup + `CancelarReservaView` status + `is_ativo` | ✅ | `6859307` |
| 4 | `TypeLote`→`TypeVenda` + `PRE-VENDA` + migration | ✅ | `a8bb02d..938d8d3` |
| 5 | Campos financeiros `CharField`→`DecimalField` + migration | ✅ | `4fb3657` |
| 6 | Restaurar lógica `RESERVADO` vs `ANALISE` em `CriarReservadoView` | ✅ | `9e15787` (2026-07-07) |

Merge completo do plano: `d7d7548`

---

## Outras iniciativas SDD concluídas depois do merge (direto em main)

- Gate de documento vigente (`.superpowers/sdd/gate-progress.md`) — completo
- Régua estilo Word no editor (`.superpowers/sdd/regua-progress.md`) — completo, aprovado
- Fonte família+tamanho no editor (`.superpowers/sdd/fonte-progress.md`) — completo, aprovado
- Wizard clientes docs+Celery (`.superpowers/sdd/wizard-progress.md`) — completo (ledger tava desatualizado dizendo Task E pendente; foi resolvido em `c4989e6..b4941e2`)

---

## Débitos técnicos identificados (fora do escopo, não mexer sem pedir)

- ~~4 testes falhando~~ RESOLVIDO 2026-07-07, commit `9dc6297`. Root cause: commit `db0023b` (2026-07-06) adicionou gate de checklist de documentos do cliente em `CriarVendaView.post()` e `pre_venda_liberada`, mas não atualizou os testes que exercitam o caminho de sucesso — `cliente_pf` (conftest) não tem `ClienteDocumento`, então o checklist sempre voltava incompleto e bloqueava silenciosamente. Fix: fixtures de checklist adicionadas nos testes (mesmo padrão de `checklist_cliente_completo` já usado em `TestEfetivarVendaView`). Não era bug de app, era lacuna de fixture de teste.
- Mojibake em comentários de `create_views.py` (encoding) — cosmético
- `ListaVendaView` linha ~170: filtro `is_ativo=False` — semântica errada, pré-existente (ver auditoria vendas)
- Branch órfã `worktree-gate-documento-vigente` com 1 commit morto (`00e3170`, já superado por `060943c` em main) — candidata a limpeza, perguntar antes de deletar
- Sem testes automatizados cobrindo `CriarReservadoView` diretamente (Task 6 fix não tem teste dedicado ainda)

---

## Arquivos de controle SDD

- Plano vendas: `.superpowers/sdd/plan.md`
- Ledger vendas: `.superpowers/sdd/progress.md`
- Reports: `.superpowers/sdd/task-N-report.md`

---

## Ambiente local

- Docker: rodando
- Porta: 8000
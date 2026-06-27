# CLAUDE.local.md

> Contexto local da sessão atual — não versionar (adicionar ao .gitignore)

---

## Sessão atual

**Objetivo:** Refactor módulo Vendas — segurança, semântica, tipos de dados
**Data:** 2026-06-23
**Branch:** `feature/tailwind-paralelo`
**Método:** Subagent-Driven Development (SDD)

---

## Progresso

| Task | Descrição | Status | Commits |
|------|-----------|--------|---------|
| 0 | Fix `Lote.save()` — remover sobrescrita `tempo_reservado` | ✅ | `de305d2` |
| 1 | `CriarVendaView` GET→POST + templates | ✅ | `db09418..9be2dc5` |
| 2 | `CancelarReservadoCadastroView` GET→POST + status + RegisterVenda | ✅ | `132289d..03b4d62` |
| 3 | `RenovaReservaView` dup + `CancelarReservaView` status + `is_ativo` | ✅ | `6859307` |
| 4 | `TypeLote`→`TypeVenda` + `PRE-VENDA` + migration | ✅ | `a8bb02d..938d8d3` |
| 5 | Campos financeiros `CharField`→`DecimalField` + migration RunPython | ✅ | `0062_convert_valores_to_decimal` |
| 6 | Restaurar lógica `RESERVADO` vs `ANALISE` em `CriarReservadoView` | ⏳ pendente | — |

**HEAD atual:** `938d8d3` (Task 5 não commitada — arquivos modificados na working tree)

---

## Pendências para próxima sessão

### Task 5 — commit pendente
Arquivos alterados (não commitados):
- `vendas/models.py` — 4 campos DecimalField + `from decimal import Decimal`
- `vendas/migrations/0062_convert_valores_to_decimal.py` — RunPython + AlterField × 4
Migration já aplicada no banco local. Só falta commit.

### Task 6 — Lógica `RESERVADO` vs `ANALISE`
Arquivo: `vendas/views/create_views.py` → `CriarReservadoView.form_valid()`
Restaurar bloco comentado: `if desconto > Decimal('0.00'): ANALISE else: RESERVADO`

---

## Débitos técnicos identificados (fora do plano atual)

- `ListaVendaView` linha ~170: filtro `is_ativo=False` — semântica errada, retorna registros inativos
- BOM character em `vendas/models.py` — cosmético
- Mojibake em comentários de `create_views.py` (encoding) — cosmético
- Sem testes automatizados para as views corrigidas

---

## Arquivos de controle SDD

- Plano: `.superpowers/sdd/plan.md`
- Ledger: `.superpowers/sdd/progress.md`
- Reports: `.superpowers/sdd/task-N-report.md`

---

## Ambiente local

- Docker: rodando
- Porta: 8000
- Backup realizado: ✅
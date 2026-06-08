# CLAUDE.local.md

> Contexto local da sessão atual — não versionar (adicionar ao .gitignore)

---

## Sessão atual

**Objetivo:** Consolidação de models — incorporar ClienteEndereco e ClienteConjuge no model Cliente  
**Data:** 2026-06-08  
**Fase atual:** [ ] Sessão 1 — Mapeamento

---

## Escopo permitido

- `clientes/models.py`
- `clientes/forms.py`
- `clientes/views.py`
- `clientes/serializers.py` (se existir)
- `clientes/services/` (se existir)
- `clientes/templates/clientes/`

---

## Fora do escopo — não tocar

- Qualquer app fora de `clientes/`
- Migrations já aplicadas
- `ClienteTelefone` (permanece separado)
- Sistema de autenticação

---

## Regra da sessão

**Mapear primeiro. Não alterar nada até aprovação explícita.**

---

## Sequência obrigatória

1. [ ] Mapear todos os usos de `ClienteEndereco` e `ClienteConjuge`
2. [ ] Adicionar campos no `Cliente` (nullable=True)
3. [ ] Criar data migration para copiar dados
4. [ ] Atualizar forms, views e templates
5. [ ] Remover `ClienteEndereco` e `ClienteConjuge` somente após validar dados

---

## Convenção de nomes

- Campos de `ClienteEndereco` → prefixo `end_`
- Campos de `ClienteConjuge` → prefixo `conj_`

---

## Ambiente local

- Docker: rodando
- Banco local: (preencher)
- Porta: 8000
- Backup realizado: ✅

# BLOQUEIOS — Refatoração app `documentos`

> Gerado durante a execução de `docs/REFATORACAO_APP_DOCUMENTOS.md`, FASE 1.
> Parei antes de remover qualquer coisa (AGENT regra #6: documentar e parar, não improvisar).

## RESOLUÇÃO (2026-06-10)
Decisão do usuário: **opção A (remoção conservadora)**.
Removidos só os órfãos seguros (sem referência fora de `documentos`):
`upload_documento`/`preview_documento`/`marcadores_disponiveis` (views+urls+templates),
`conversor.py`, `mappings.py`, `vendas/views_old.py` (morto).
**Mantidos** por dependência ativa (BLOQUEIOS 1 e 2): `CadastroDocumento` (FK de
`empreendimentos`), e as URLs `proposta-rascunho`/`contrato`/`contrato_pdf`/`proposta_pdf`
(usadas por templates de `vendas`/`empreendimentos`). Refatoração total (opção B) fica
pendente de decisão futura.

## Data
2026-06-10

## Resumo
A FASE 1 manda **remover models/URLs/views/templates legados** não listados como "manter".
Auditoria mostrou que vários alvos de remoção têm **dependências ativas em outros apps**
(`empreendimentos`, `vendas`). Removê-los quebra o sistema e viola o próprio critério de
aceite da FASE 1: *"Nenhum import de model/view removido em outros apps"* e *"Nenhuma URL 500"*.

---

## BLOQUEIO 1 — `CadastroDocumento` tem FK ativa de `empreendimentos`

`empreendimentos/models.py:70`:
```python
contrato = models.ForeignKey(
    CadastroDocumento,            # documentos/models.py:7 import
    on_delete=models.CASCADE,
    verbose_name='Contrato padrão',
    blank=True, null=True,
)
```
Usado também em `empreendimentos/admin.py`, `empreendimentos/forms.py` (campo `contrato`).

**Impacto de remover `CadastroDocumento`:** quebra model + migrations + admin + forms de
`empreendimentos`. O doc lista `CadastroDocumento` como "remover" (não está na seção Models
mantidos), mas o critério da FASE 1 proíbe remover import usado em outro app.

**Conflito não resolvível sem decisão:** migrar `Empreendimento.contrato` de
`CadastroDocumento` → `ModeloDocumento` exige data migration + ajustar admin/forms/views de
empreendimentos. Fora do escopo descrito nas fases.

---

## BLOQUEIO 2 — URLs legadas referenciadas por templates ativos de outros apps

| URL name | Referenciado em | App |
|---|---|---|
| `proposta-rascunho` | `empreendimentos/templates/lista-quadras.html:671` | empreendimentos |
| `contrato` | `vendas/templates/reservado.html:616` | vendas |
| `contrato_pdf` | `vendas/templates/reservado.html:626` | vendas |
| `proposta_pdf` | `vendas/templates/reservado_detalhe.html:409` | vendas |

O doc (seção "URLs mantidas") só lista `proposta/<uuid>/` + rotas de modelos/variáveis,
ou seja, manda remover `proposta-rascunho`, `contrato`, `contrato_pdf`, `proposta_pdf`.
**Remover → NoReverseMatch (500)** nas páginas acima. Viola critério "Nenhuma URL 500".

As views legadas (`propostaRascunho`, `contrato`, `contrato_pdf1`, `proposta_pdf`) ainda
dependem de `CadastroDocumento` (BLOQUEIO 1) e do template legado `contrato.html`.

---

## O que É seguro remover (órfão, só usado dentro de `documentos`)

Confirmado por grep que nada fora de `documentos/` referencia:
- Views: `upload_documento`, `preview_documento`, `marcadores_disponiveis`
- URLs: `upload-documento`, `preview-documento`, `marcadores-disponiveis`
- Templates: `documentos/upload_documento.html`, `documentos/marcadores_disponiveis.html`
- Helpers: `documentos/conversor.py`, `documentos/mappings.py`
- `documentos/views_old.py`? (não existe aqui) — `vendas/views_old.py` importa
  `CadastroDocumento` mas **não está wired em nenhuma urls** (pode ser removido junto, ou
  ignorado por estar morto).

`proposta_legado` (em `documentos/views.py`): a nova `proposta` faz fallback pra ela. Só
remover depois de decidir se mantém o fallback.

`proposta.html`: **manter** — é usada pela nova `proposta` também.

---

## Estado das FASES 2 e 3 (já implementadas em sessões anteriores)

A maioria dos critérios das FASES 2/3 já está verde no código atual (implementação diverge
dos IDs exatos do doc, mas atende os critérios — validado por testes jsdom + end-to-end):
- Editor inicia com HTML (`conteudo_html` é HTML puro; `json.dumps` → `conteudoInicial`).
- Autosave não navega; manual redireciona; modelo novo troca `salvar_url` (sem duplicar).
- Toolbar de tabela aparece/some com `isActive('table')`.
- Toolbar expandida (cor, realce, sub/sup, hr, undo/redo, limpar).
- Bundle sem `Underline` duplicado; cache-bust `?v={mtime}` (inclui CSS).
- CSS A4 com bordas de tabela, `.doc-var`, `.selectedCell`.

Diferença: o doc pede reescrever `modelo_editor.html` com IDs `#editor-area`,
`#grupo-tabela`, `<script id="conteudo-inicial">` etc. O atual usa `window.EDITOR_CONFIG`,
`#tiptapEditor`, `#grupoTabela`. **Reescrever introduz risco de regressão sem ganho de
critério** (todos já passam).

---

## Decisão necessária (escolher antes de continuar)

**A) Remoção conservadora (recomendado):** remover só os órfãos do bloco "seguro"
(upload/preview/marcadores + conversor/mappings + views_old morto). Manter
`CadastroDocumento` e as URLs legadas referenciadas. Não reescrever o editor (já passa).

**B) Refatoração total como no doc:** migrar `Empreendimento.contrato` para `ModeloDocumento`
(data migration), substituir contrato/proposta_pdf/rascunho pelo novo módulo, editar os
templates de `vendas`/`empreendimentos` que linkam as URLs legadas, então remover
`CadastroDocumento` e as views/URLs legadas. Escopo grande, toca 2 apps fora de documentos,
risco alto. Precisa de sinal verde explícito.

**C) Parar a refatoração** — manter como está (FASES 2/3 já atendidas).

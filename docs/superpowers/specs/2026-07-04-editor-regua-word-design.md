# Régua estilo Word no editor de modelos (TipTap) — Fase A

**Status:** aprovado em brainstorm, aguardando plano de implementação
**Escopo:** `documentos/modelos/<id>/` (editor de `ModeloDocumento`)
**Fora de escopo (fases futuras):** estilos de parágrafo avançados, localizar/substituir, contagem de página real via engine de PDF, controle de alterações/comentários.

## Contexto

O editor de modelos usa TipTap v3 (bundle vendorizado em `documentos/static/documentos/js/vendor/tiptap.bundle.min.js`, fonte em `documentos/frontend/entry.js`). A extensão `PaginationPlus` já simula a paginação A4 no editor (margens fixas ABNT 25/20/20/30mm, hardcoded em `editor-init.js`).

Descoberta durante o brainstorm: `ConfiguracaoDocumento` (model, `documentos/models.py:227`) já tem os campos `margem_sup/inf/esq/dir` por **empreendimento** (OneToOne), e **ambos** os motores de PDF já leem esses campos:
- WeasyPrint: `documentos/templates/documentos/pdf/documento_base.html:8-14` (`@page { margin: {{ cfg.margem_sup|default:25 }}mm ... }`)
- Playwright: `documentos/pdf_engine.py:39-62` (`page.pdf(margin={...})`)

Ou seja: não é preciso migration nova para margem de página — o dado e o consumo no PDF real já existem. O que falta é a **UI de régua no editor** e o **fluxo de edição/persistência** a partir dela.

Um `ModeloDocumento` pode ser global (`eh_global=True`) ou vinculado a N empreendimentos via `EmpreendimentoDocumento` (M2M através de tabela). Cada empreendimento pode ter margem diferente — por isso o editor precisa de um seletor de empreendimento para saber qual `ConfiguracaoDocumento` está sendo mostrada/editada.

## Objetivo

Adicionar ao editor de modelos:
1. Régua horizontal (margem esq/dir + recuo de parágrafo) e vertical (margem sup/inf), estilo Word, em polegadas.
2. Recuo de parágrafo com 4 marcadores: primeira linha, esquerdo, direito, deslocado (hanging) — persistido como atributo do nó de parágrafo dentro do próprio `conteudo_html`.
3. Persistência de margem de página no `ConfiguracaoDocumento` do empreendimento selecionado, refletindo no PDF real (ambos os motores já leem esse campo).

## Arquitetura

### 1. Componente de régua

- Novo módulo `documentos/frontend/ruler.js`, buildado no mesmo bundle esbuild (`entry.js` importa e expõe via `window.TipTapBundle` ou módulo próprio `window.DocRuler`).
- Sem dependência nova de terceiros — componente vanilla JS/CSS (mockup visual aprovado: régua horizontal sticky no topo do container scrollável, vertical sticky na lateral esquerda, ambas acompanhando o scroll da página A4).
- Unidade interna sempre px (compatível com o `MM_TO_PX` já usado em `editor-init.js`); a régua converte só para exibição em polegadas.
- Layout de marcadores (aprovado via mockup visual):
  - Cinza escuro: margem da página (esquerda/direita na régua horizontal, superior/inferior na vertical).
  - Azul: recuo primeira linha (triângulo topo) e recuo esquerdo (triângulo/retângulo base) do parágrafo.
  - Vermelho: recuo direito do parágrafo.

### 2. Recuo de parágrafo (dado + persistência)

- Extensão custom `IndentedParagraph`, estendendo o `Paragraph` do StarterKit, com atributos: `indentLeft`, `indentRight`, `indentFirstLine`, `indentHanging` (armazenados em px).
- Serializa como `style="margin-left:Xpx;margin-right:Ypx;text-indent:Zpx"` no HTML — mesmo mecanismo de round-trip que já existe para negrito/itálico/cor. Nenhum campo novo no banco: o recuo vive dentro do `conteudo_html` do `ModeloDocumento`, como qualquer outra formatação inline.
- Arrastar um marcador aplica no parágrafo onde está o cursor (ou nos parágrafos abrangidos pela seleção) via `editor.chain().updateAttributes('paragraph', {...}).run()`.

### 3. Persistência de margem de página (por empreendimento)

- Dropdown de empreendimento no editor (ao lado de Título/Tipo), populado com os empreendimentos vinculados ao modelo via `EmpreendimentoDocumento`.
- Se o modelo for global ou não houver vínculo: opção única "Padrão ABNT", somente leitura — marcadores de margem de página não arrastam (recuo de parágrafo continua livre).
- Nova view (ex.: `documentos/views_config.py`), `POST /documentos/empreendimentos/<id>/margens/`, grava via `update_or_create` em `ConfiguracaoDocumento.margem_sup/inf/esq/dir`. Mesma exigência de autenticação/permissão já usada para editar `ModeloDocumento` — sem permissão nova.

### 4. Reinício do editor ao soltar marcador de margem de página

`PaginationPlus` não expõe comando para atualizar margem em runtime — a única forma é recriar a instância do `Editor`.

Fluxo no **mouseup** (drop), nunca durante o arraste:
1. Captura `editor.state.selection.from/to` (posição do cursor).
2. Limpa o `setInterval` do autosave atual (evita intervalo fantasma referenciando instância destruída).
3. `editor.destroy()`.
4. Cria novo `Editor` com `PaginationPlus.configure({...novas margens...})`, `content: htmlCapturado` (de `editor.getHTML()` antes do destroy).
5. Restaura seleção com `editor.commands.setTextSelection({from, to})`.
6. Reinicia o `setInterval` de autosave apontando para a instância nova.

Durante o arraste (antes do drop): só atualiza CSS visual (custom properties no `.editor-a4-shell`), sem tocar no editor — evita re-render pesado a cada pixel.

**Trade-off aceito:** `destroy()` zera o histórico de undo/redo do ProseMirror. Arrastar margem é ação pontual, não deve ocorrer no meio de uma sequência de digitação — perda de undo nesse momento é aceitável.

## Fora do escopo desta fase

- Régua não altera CSS do PDF diretamente — a fonte de verdade continua sendo `ConfiguracaoDocumento` lido pelos dois motores de PDF (já existente).
- Estilos de parágrafo (títulos, listas numeradas), localizar/substituir, contagem de página real e recursos colaborativos (comentários, controle de alterações) ficam para fases futuras, já listadas na conversa mas não detalhadas aqui.

## Testes

- Playwright: simula `mousedown` → `mousemove` → `mouseup` no marcador de margem de página; confirma que `ConfiguracaoDocumento.margem_esq` (ou o campo arrastado) mudou no banco e que `editor.getHTML()` manteve o texto original intacto.
- Confirma que o autosave não dispara **durante** o arraste, só depois, com o intervalo normal.
- Recuo de parágrafo: aplica `indentFirstLine` num parágrafo, salva (autosave ou manual), recarrega a página do editor, confirma que o atributo persistiu no `conteudo_html`.

## Notas de coordenação

Durante o brainstorm desta spec, identificado que outra sessão de Claude Code tinha uma tarefa em andamento no mesmo diretório de trabalho, com sobreposição direta de escopo:
- Item "contador de caracteres" da outra tarefa duplicava um recurso já presente (não commitado) no working tree.
- Item "indent/outdent" da outra tarefa conflitava diretamente com o design de recuo de parágrafo desta spec (abordagens incompatíveis para o mesmo atributo de nó).

A outra sessão foi pausada pelo usuário antes de tocar nesses itens. Antes de iniciar a implementação desta spec, confirmar que nenhuma mudança concorrente foi commitada nos arquivos `documentos/frontend/entry.js`, `documentos/static/documentos/js/editor/editor-init.js`, `documentos/frontend/package.json` e `documentos/templates/documentos/modelo_editor.html`.
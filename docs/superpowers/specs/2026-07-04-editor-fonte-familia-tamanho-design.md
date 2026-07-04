# Controle de fonte (família + tamanho) por seleção no editor de modelos

**Status:** aprovado em brainstorm, aguardando plano de implementação
**Escopo:** `documentos/modelos/<id>/` (editor de `ModeloDocumento`)
**Fora de escopo:** ligar o campo global `ConfiguracaoDocumento.fonte_familia`/`fonte_tamanho` como padrão do documento (fica pra fase futura, se pedido); qualquer fonte fora da lista fixa abaixo.

## Contexto

O editor de modelos (TipTap v3) já tem cor de texto e realce aplicados via a mark `textStyle` (`@tiptap/extension-text-style`, já instalada) combinada com `@tiptap/extension-color`. Recuo de parágrafo (`indentLeft`/`indentRight`/`indentFirstLine`) já foi implementado como atributos globais customizados num nó (`documentos/static/documentos/js/editor/indent-attrs.js`, extensão `IndentAttrsExtension`), sem precisar de pacote npm novo — só usa `Extension.create({ addGlobalAttributes: [...] })` do `@tiptap/core`.

Risco já documentado no projeto (`documentos/frontend/README.md`): a fonte usada no editor localmente (Windows costuma ter Times New Roman) diverge da fonte real do PDF de produção (container só tem `fonts-dejavu` explícito no Dockerfile, mais `fonts-liberation` como dependência típica do Chromium/Playwright). Permitir fonte livre no dropdown pioraria essa divergência já conhecida.

## Objetivo

Adicionar à toolbar do editor de modelos:
1. Dropdown de família de fonte — lista fixa de 6 opções confirmadas como disponíveis tanto no editor quanto no ambiente de produção: DejaVu Serif, DejaVu Sans, DejaVu Mono, Liberation Serif, Liberation Sans, Liberation Mono.
2. Dropdown de tamanho de fonte — lista fixa em pt: 9, 10, 11, 12, 14, 16, 18, 20, 24.

Ambos aplicam no texto selecionado, com opção "Remover" em cada dropdown pra voltar ao padrão herdado do documento.

## Arquitetura

### 1. Extensão de atributos de fonte (bundle)

Novo arquivo `documentos/static/documentos/js/editor/font-attrs.js`, seguindo exatamente o mesmo padrão IIFE de `indent-attrs.js` e `variavel-node.js` (carregado como `<script>` separado, não passa pelo esbuild):

```js
(function () {
	if (!window.TipTapBundle) {
		console.error('TipTapBundle ausente — gere o bundle (documentos/frontend/README.md).')
		return
	}
	const { Extension } = window.TipTapBundle

	const FontAttrs = Extension.create({
		name: 'fontAttrs',
		addGlobalAttributes() {
			return [{
				types: ['textStyle'],
				attributes: {
					fontFamily: {
						default: null,
						parseHTML: el => el.style.fontFamily || null,
						renderHTML: attrs => attrs.fontFamily ? { style: `font-family: ${attrs.fontFamily}` } : {},
					},
					fontSize: {
						default: null,
						parseHTML: el => el.style.fontSize || null,
						renderHTML: attrs => attrs.fontSize ? { style: `font-size: ${attrs.fontSize}` } : {},
					},
				},
			}]
		},
	})

	window.FontAttrsExtension = FontAttrs
})()
```

`Extension` já é exportado no bundle desde a Fase A (régua) — nenhuma mudança em `entry.js`/rebuild do esbuild necessária aqui.

### 2. Aplicação (merge, não substituição)

O TipTap já resolve o problema de "múltiplos atributos na mesma mark" — é assim que `Color`/`Highlight` já convivem hoje sem se apagar. O comando genérico `setMark(typeOrName, attributes)` do `@tiptap/core` mescla os atributos passados com os já existentes na mark daquele trecho antes de aplicar. Aplicação:

```js
editor.chain().focus().setMark('textStyle', { fontFamily: 'DejaVu Serif' }).run()
editor.chain().focus().setMark('textStyle', { fontSize: '12pt' }).run()
```

"Remover" em cada dropdown seta o atributo correspondente pra `null` (mesmo idioma do `indentLeft`/etc. — `null`/`0` é falsy, então `renderHTML` naturalmente omite o `style`).

O botão "Limpar formatação" já existente (`chain().unsetAllMarks().clearNodes().run()`) já limpa a mark `textStyle` inteira — cor, realce e agora fonte somem juntos, sem mudança necessária nesse botão.

### 3. Toolbar

Novo grupo `toolbar-group` na `modelo_editor.html`, posicionado antes do dropdown de cor existente, com dois dropdowns Bootstrap seguindo o mesmo HTML dos dropdowns de cor/realce já existentes (`data-bs-toggle="dropdown"`, lista de botões dentro de `.dropdown-menu`):

```html
<div class="dropdown d-inline">
	<button type="button" class="btn btn-light btn-sm dropdown-toggle" data-bs-toggle="dropdown" title="Família da fonte">Fonte</button>
	<div class="dropdown-menu p-2">
		{% for valor, rotulo in fontes_familia %}
		<button type="button" class="dropdown-item" data-font-family="{{ valor }}">{{ rotulo }}</button>
		{% endfor %}
		<button type="button" class="btn btn-link btn-sm p-0 mt-2 text-decoration-none" data-action="font-family-clear">Remover fonte</button>
	</div>
</div>
<div class="dropdown d-inline">
	<button type="button" class="btn btn-light btn-sm dropdown-toggle" data-bs-toggle="dropdown" title="Tamanho da fonte">Tam.</button>
	<div class="dropdown-menu p-2">
		{% for tamanho in fontes_tamanho %}
		<button type="button" class="dropdown-item" data-font-size="{{ tamanho }}">{{ tamanho }}pt</button>
		{% endfor %}
		<button type="button" class="btn btn-link btn-sm p-0 mt-2 text-decoration-none" data-action="font-size-clear">Remover tamanho</button>
	</div>
</div>
```

`fontes_familia` (lista de tuplas valor/rótulo) e `fontes_tamanho` (lista de inteiros) vêm do contexto da view `modelo_editor`, mesmo padrão de `cores_texto`/`cores_realce` já existente — constantes Python, sem tabela nova no banco.

Em `documentos/static/documentos/js/editor/editor-init.js`, wiring novo ao lado do wiring existente de `[data-color]`/`[data-highlight]`:

```js
document.querySelectorAll('[data-font-family]').forEach(btn => {
	btn.addEventListener('click', e => {
		e.preventDefault()
		editorAtivo().chain().focus().setMark('textStyle', { fontFamily: btn.dataset.fontFamily }).run()
	})
})
document.querySelectorAll('[data-font-size]').forEach(btn => {
	btn.addEventListener('click', e => {
		e.preventDefault()
		editorAtivo().chain().focus().setMark('textStyle', { fontSize: `${btn.dataset.fontSize}pt` }).run()
	})
})
```

E os dois botões "Remover" entram no `switch (acao)` já existente do handler `[data-action]`:

```js
case 'font-family-clear': editorAtivo().chain().focus().setMark('textStyle', { fontFamily: null }).run(); break
case 'font-size-clear': editorAtivo().chain().focus().setMark('textStyle', { fontSize: null }).run(); break
```

`editorAtivo()` já existe (helper adicionado na Fase A, resolve sempre a instância viva do editor — necessário porque o editor pode ser recriado por um drag de margem de página).

A extensão `FontAttrsExtension` entra na fábrica `criarExtensoes(margensPx)` (já existente desde o fix da régua, Fase A) — um único lugar, não precisa duplicar entre a criação inicial e o reinício do editor.

## Fora de escopo

- Ligar `ConfiguracaoDocumento.fonte_familia`/`fonte_tamanho` como padrão herdado do documento — hoje esses campos existem no model mas não são lidos pelo editor nem pelo controle novo; fica pra uma fase futura se for pedido.
- Fonte livre (texto digitado) — só a lista fixa de 6 famílias × 9 tamanhos.
- Régua/marcador visual — este controle é toolbar/dropdown, não tem componente de arrastar.

## Testes

- Playwright: seleciona um trecho de texto, aplica uma cor (`data-color`), aplica uma família de fonte (`data-font-family`), aplica um tamanho (`data-font-size`); confirma que o `<span>` resultante no `getHTML()` contém os três `style` juntos (`color:`, `font-family:`, `font-size:`) — prova que `setMark` mescla em vez de substituir.
- Playwright: clica "Remover fonte" depois de aplicar uma família; confirma que `font-family:` some do HTML mas `color:` (se aplicado antes) permanece.
- Confirma que o texto original sobrevive a todas as aplicações (mesmo padrão de sanidade já usado nos testes da régua).

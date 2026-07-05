# Régua vertical estendida a todas as páginas — editor de modelos

**Status:** aprovado em brainstorm, aguardando plano de implementação
**Escopo:** `documentos/modelos/<id>/` (editor de `ModeloDocumento`), componente `documentos/static/documentos/js/editor/ruler.js`
**Fora de escopo:** margem por página individual (margem continua sendo do documento inteiro, via `ConfiguracaoDocumento` do empreendimento — já implementado); régua horizontal (não precisa mudar, ver "Por que só a vertical" abaixo); mudanças no PDF final (WeasyPrint/Playwright não usam essa régua, ela é só do editor visual).

## Contexto

A régua vertical (`documentos/static/documentos/js/editor/ruler.js`, feature aprovada em `docs/superpowers/specs/2026-07-04-editor-regua-word-design.md`) hoje tem altura fixa = altura de uma página (`pageHeightPx`, 1123px). O editor usa `PaginationPlus` (TipTap) pra simular múltiplas páginas A4 dentro de um único container scrollável (`#tiptapEditor`), gerando por página um `.rm-page-header-N` e, entre páginas, um `.rm-page-break`.

Bug relatado: em documentos com mais de uma página, a régua vertical só aparece do lado da primeira página — ao rolar pra páginas seguintes, o espaço ao lado fica vazio (a régua não existe mais ali, porque sua altura nunca passou de 1123px).

Confirmado via inspeção (`documentos/modelos/2/`, documento de 12 páginas): `document.querySelectorAll('.rm-page-header').length === 12`, `.rm-page-break` × 11 — a contagem de página é sempre lida do DOM real gerado pelo `PaginationPlus`, nunca calculada por estimativa de altura de conteúdo.

## Por que só a vertical

A régua horizontal mostra margem esquerda/direita e recuo de parágrafo — esses valores são os mesmos em toda página do documento (margem é por documento/empreendimento, não por página), e a régua horizontal fica fixa acima do conteúdo, não rola verticalmente junto com as páginas. Não há necessidade de replicá-la.

## Objetivo

Fazer a régua vertical (zona de margem superior/inferior + numeração em polegada) aparecer ao lado de **toda página** do documento, não só a primeira. Comportamento decidido com o usuário:

1. Numeração de polegada **reinicia do zero em cada página** (padrão Word/Google Docs).
2. Zona de margem (cinza) aparece em toda página — mas o **marcador arrastável** (drag de margem) continua existindo **só na primeira página**. Arrastar nele muda a margem do documento inteiro (comportamento já existente, sem mudança); as demais páginas são só indicativas.
3. Recalcula sempre que o layout de páginas pode ter mudado: no load inicial e num debounce curto (~400ms) após `editor.on('update')`, e depois de `reiniciarEditorComNovaMargem` (a régua já escuta esse fluxo).

## Arquitetura

### Estrutura hoje (`ruler.js`)

`init()` cria um único elemento `.doc-ruler-vertical` com `style.height = pageHeightPx`, contendo: ticks (`criarTicksVerticais`), zona-superior, zona-inferior, marcador-superior, marcador-inferior (arrastáveis). Esse elemento é anexado uma vez em `vertContainer` (`#rulerVerticalSlot` no template) e nunca redimensionado.

### Mudança

`vert` passa a ter altura dinâmica = altura total do conteúdo paginado, e passa a conter **N blocos empilhados**, um por página, cada um posicionado via `top: index * (pageHeightPx + pageGap)`:

```js
function criarBlocoPagina(indice, offsetTopPx, comMarcadores) {
	const bloco = document.createElement('div')
	bloco.className = 'doc-ruler-pagina'
	bloco.style.top = `${offsetTopPx}px`
	bloco.style.height = `${pageHeightPx}px`
	bloco.appendChild(criarTicksVerticais(pageHeightPx))          // numeração reinicia (função já existe, sem mudança)
	const zonaSup = criarZonaMargem('superior')
	const zonaInf = criarZonaMargem('inferior')
	bloco.appendChild(zonaSup)
	bloco.appendChild(zonaInf)
	if (comMarcadores) {
		// reaproveita marcadorSup/marcadorInf existentes (únicos, com os
		// listeners de drag já implementados) — só o bloco 0 os recebe.
		bloco.appendChild(marcadorSup)
		bloco.appendChild(marcadorInf)
	}
	return { bloco, zonaSup, zonaInf }
}
```

Nova função exportada em `window.DocRuler`:

```js
setNumPaginas(n) {
	vert.style.height = `${n * pageHeightPx + (n - 1) * pageGapPx}px`
	vert.innerHTML = ''
	blocosPagina = []
	for (let i = 0; i < n; i++) {
		const offsetTop = i * (pageHeightPx + pageGapPx)
		const { bloco, zonaSup, zonaInf } = criarBlocoPagina(i, offsetTop, i === 0)
		vert.appendChild(bloco)
		blocosPagina.push({ zonaSup, zonaInf })
	}
	repintar() // já existe — hoje escreve style em zonaSup/zonaInf/marcadorSup/marcadorInf; passa a iterar blocosPagina
}
```

`repintar()` (já existente) passa a aplicar a mesma altura de zona de margem (`margens.top`/`margens.bottom`) em **todos** os `blocosPagina[i].zonaSup/zonaInf`, não só no bloco 0 — só os marcadores continuam exclusivos do bloco 0.

`init()` precisa receber `pageGapPx` (hoje só existe como `pageGap: 30` hardcoded na config do `PaginationPlus` em `editor-init.js` — passa a ser passado pro `DocRuler.init()` também, evitando duplicar o número mágico).

`init()` chama `setNumPaginas(1)` internamente como estado inicial (mantém compatibilidade — 1 página é o caso mínimo, idêntico ao comportamento atual).

### Integração (`editor-init.js`)

Nova função:

```js
function contarPaginas() {
	return document.querySelectorAll('#tiptapEditor .rm-page-header').length || 1
}
```

Chamadas:
1. Logo após `ruler.init(...)`, dentro de um `requestAnimationFrame` (o `PaginationPlus` computa os `.rm-page-header` de forma assíncrona ao montar o editor — chamar `contarPaginas()` síncrono logo após `new T.Editor(...)` pode ler 0/1 antes do plugin terminar).
2. Em `editor.on('update', ...)`, com debounce (`clearTimeout`/`setTimeout`, ~400ms) — reaproveita o padrão já usado por `iniciarAutosave` (variável de intervalo/timeout guardada em closure).
3. Dentro de `reiniciarEditorComNovaMargem`, depois que o novo `Editor` é criado (mudança de margem quase sempre muda contagem de página).

## Erros / casos de borda

- **Debounce e reinício do editor correndo juntos**: se o timeout do debounce disparar exatamente durante um `reiniciarEditorComNovaMargem` (editor sendo destruído/recriado), `contarPaginas()` deve ler do DOM atual (`document.querySelectorAll`, não uma referência de editor guardada) — já é seguro por construção, não precisa de guarda extra.
- **Documento de 1 página**: `setNumPaginas(1)` deve produzir visualmente o que já existe hoje (bloco único com marcadores) — é o caso de regressão a proteger com teste.
- **Zero `.rm-page-header` encontrado** (falha de leitura do DOM, plugin ainda não montou): `contarPaginas()` cai no `|| 1`, nunca deixa a régua com altura 0/quebrada.

## Testes

Estender `documentos/tests/test_editor_ruler.py` (ou novo arquivo `test_editor_ruler_multipagina.py`, seguindo o padrão de arquivo dedicado já usado para indent/font/line-height):

1. Doc de teste com conteúdo longo o bastante pra gerar 2+ páginas: `test_editor_ruler_e2e.py` hoje usa só 1 parágrafo curto (não serve) — gerar a fixture nova com N parágrafos repetidos (`'<p>Texto de teste.</p>' * 40`, ajustar quantidade até confirmar 2+ páginas reais via `.rm-page-header`).
2. Assert: `.doc-ruler-vertical` tem altura igual a `numPaginas * pageHeightPx + (numPaginas-1) * pageGapPx` (calculado a partir de `document.querySelectorAll('.rm-page-header').length`).
3. Assert: existe exatamente 1 `.doc-ruler-marcador-margem-superior` no DOM (não N) — prova que só a página 0 é arrastável.
4. Assert: cada `.doc-ruler-pagina` tem sua própria zona de margem visível (`.doc-ruler-margem-superior` dentro de cada bloco, com `offsetHeight` compatível com a margem configurada).
5. Regressão: teste de 1 página continua passando sem mudança de comportamento visual (reexecutar `test_editor_ruler.py::test_regua_renderiza_com_zonas_de_margem` sem alteração).

## CSS (`modelo_editor.html`, bloco `<style>`)

Nova classe `.doc-ruler-pagina { position: absolute; left: 0; width: 100%; }` (as zonas/marcadores dentro dela continuam com `position: absolute` relativo a esse bloco, igual já funciona hoje relativo ao `.doc-ruler-vertical`). `.doc-ruler-vertical` deixa de ter `height` fixo no CSS (já é setado via JS hoje, sem mudança aí).

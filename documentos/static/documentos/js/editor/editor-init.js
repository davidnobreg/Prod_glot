// Bootstrap do editor de modelos (Fase 7).
// Depende de: window.TipTapBundle (bundle vendorizado) e window.VariavelNode.
(function () {
	const elEditor = document.getElementById('tiptapEditor')
	if (!elEditor) return
	if (!window.TipTapBundle) {
		elEditor.innerHTML = '<div class="alert alert-danger">Bundle TipTap não carregado. Gere o bundle (documentos/frontend/README.md).</div>'
		return
	}

	const T = window.TipTapBundle
	const cfg = window.EDITOR_CONFIG || {}
	const csrf = cfg.csrf
	let salvarUrl = cfg.salvarUrl
	let autosaveIntervalId = null
	let debouncePaginasId = null

	// Margens ABNT (25/20/20/30mm sup/dir/inf/esq), mesmas de documento_a4.css,
	// convertidas pra px (96 CSS px/polegada) — aproxima a régua visual do PDF
	// real gerado via Playwright. Ver documentos/frontend/README.md sobre a
	// limitação conhecida: fonte local (Times New Roman) x produção (Liberation
	// Serif) pode fazer a quebra de página no editor divergir 1 linha do PDF.
	const MM_TO_PX = window.DocRuler.MM_TO_PX

	// Sanitiza HTML colado do Word: remove tags/atributos mso-*, quebras de
	// página forçadas (causa raiz de páginas indevidas no editor) e margin/
	// padding inline por parágrafo que o Word injeta em todo <p>/<span>.
	function sanitizarHtmlColado(html) {
		const doWord = /mso-|urn:schemas-microsoft-com:office|w:WordDocument/i.test(html)
		const doc = new DOMParser().parseFromString(html, 'text/html')
		doc.querySelectorAll('style, script, meta, link').forEach(el => el.remove())
		doc.querySelectorAll('*').forEach(el => {
			if (el.tagName.includes(':')) {
				el.replaceWith(...el.childNodes)
				return
			}
			if (doWord) { el.removeAttribute('class') }
			const style = el.getAttribute('style')
			if (!style) { return }
			const mantido = style.split(';').map(s => s.trim()).filter(Boolean).filter(decl => {
				const prop = decl.split(':')[0].trim().toLowerCase()
				if (prop.startsWith('mso-')) { return false }
				if (prop.startsWith('page-break')) { return false }
				if (doWord && (prop.startsWith('margin') || prop.startsWith('padding'))) { return false }
				return true
			})
			if (mantido.length) { el.setAttribute('style', mantido.join('; ')) } else { el.removeAttribute('style') }
		})
		return doc.body.innerHTML
	}

	// ---- Margens de página: empreendimento vinculado ou fallback ABNT ----
	// Calculada antes da criação do editor para que a paginação REAL (não só
	// a régua visual) já nasça correta, sem depender de um drag manual.
	const MARGENS_ABNT_PX = { top: 94, right: 76, bottom: 76, left: 113 } // ABNT 25/20/20/30mm
	const PAGE_GAP_PX = 30
	const empreendimentos = cfg.empreendimentos || []
	const margensIniciais = empreendimentos.length
		? {
			top: Math.round(empreendimentos[0].margem_sup * MM_TO_PX),
			right: Math.round(empreendimentos[0].margem_dir * MM_TO_PX),
			bottom: Math.round(empreendimentos[0].margem_inf * MM_TO_PX),
			left: Math.round(empreendimentos[0].margem_esq * MM_TO_PX),
		}
		: { ...MARGENS_ABNT_PX }

	// Fábrica única da lista de extensions: usada na criação inicial do editor
	// E em reiniciarEditorComNovaMargem(). Evita duplicar a lista (Finding I2) --
	// uma extension adicionada só num dos dois lugares sumiria silenciosamente
	// na primeira vez que o usuário arrastasse uma margem.
	function criarExtensoes(margensPx) {
		return [
			T.StarterKit.configure({ link: { openOnClick: false, autolink: true } }),
			T.TextAlign.configure({ types: ['heading', 'paragraph'] }),
			T.Table.configure({ resizable: true }),
			T.TableRow, T.TableHeader, T.TableCell,
			T.TextStyle,
			T.Color,
			T.Highlight.configure({ multicolor: true }),
			T.Subscript,
			T.Superscript,
			T.CharacterCount,
			window.VariavelNode,
			window.IndentAttrsExtension,
			window.FontAttrsExtension,
			window.LineHeightAttrsExtension,
			T.PaginationPlus.configure({
				pageWidth: 794,
				pageHeight: 1123,
				marginTop: margensPx.top,
				marginBottom: margensPx.bottom,
				marginLeft: margensPx.left,
				marginRight: margensPx.right,
				contentMarginTop: 0,
				contentMarginBottom: 0,
				pageGap: PAGE_GAP_PX,
				footerLeft: '',
				footerRight: 'Página {page}',
				headerLeft: '',
				headerRight: '',
			}),
		]
	}

	const editor = new T.Editor({
		element: elEditor,
		editorProps: {
			transformPastedHTML: sanitizarHtmlColado,
		},
		extensions: criarExtensoes(margensIniciais),
		content: cfg.conteudoInicial || '',
	})
	window._editor = editor

	// Resolve sempre a instância viva: após um drag de margem, o editor
	// original é destruído e substituído — este helper evita que handlers
	// registrados antes do drag continuem presos à instância morta.
	function editorAtivo() { return window._editor }

	// PaginationPlus computa .rm-page-header de forma assíncrona — chamar logo
	// após criar/recriar o editor pode ler a contagem antiga por 1 tick.
	function contarPaginas() {
		return document.querySelectorAll('#tiptapEditor .rm-page-header').length || 1
	}

	// Listeners de instância do TipTap/ProseMirror (não são eventos DOM):
	// precisam ser re-registrados a cada novo Editor criado.
	function registrarListenersDoEditor(editorAtual) {
		editorAtual.on('update', atualizarContador)
		editorAtual.on('selectionUpdate', atualizarGrupoTabela)
		editorAtual.on('transaction', atualizarGrupoTabela)
		editorAtual.on('selectionUpdate', atualizarMarcadoresDeRecuo)
		editorAtual.on('transaction', atualizarMarcadoresDeRecuo)
		editorAtual.on('update', () => {
			clearTimeout(debouncePaginasId)
			debouncePaginasId = setTimeout(() => ruler.setNumPaginas(contarPaginas()), 400)
		})
	}

	iniciarAutosave(editor)
	registrarListenersDoEditor(editor)

	// ---- Régua (margem de página) ----
	const ruler = window.DocRuler.init({
		horizContainer: document.getElementById('rulerHorizontalSlot'),
		vertContainer: document.getElementById('rulerVerticalSlot'),
		pageWidthPx: 794,
		pageHeightPx: 1123,
		pageGapPx: PAGE_GAP_PX,
		margensPx: margensIniciais,
	})
	requestAnimationFrame(() => ruler.setNumPaginas(contarPaginas()))

	// ---- Dropdown de empreendimento: liga/desliga edição de margem ----
	const selectEmpreendimento = document.getElementById('modeloEmpreendimento')
	function empreendimentoSelecionado() {
		if (!selectEmpreendimento || !selectEmpreendimento.value) { return null }
		return empreendimentos.find(e => String(e.id) === selectEmpreendimento.value) || null
	}
	// Só permite arrastar a régua se HÁ empreendimento selecionado E o usuário
	// tem a permissão exigida pelo endpoint de persistência (documentoConfig) --
	// ver cfg.podeEditarMargem, calculado em modelo_editor() (views_documentos.py).
	ruler.setReadOnly(!empreendimentoSelecionado() || !cfg.podeEditarMargem)
	if (selectEmpreendimento) {
		selectEmpreendimento.addEventListener('change', () => {
			const emp = empreendimentoSelecionado()
			ruler.setReadOnly(!emp || !cfg.podeEditarMargem)
			const novasMargensPx = emp
				? {
					top: Math.round(emp.margem_sup * MM_TO_PX),
					right: Math.round(emp.margem_dir * MM_TO_PX),
					bottom: Math.round(emp.margem_inf * MM_TO_PX),
					left: Math.round(emp.margem_esq * MM_TO_PX),
				}
				: { ...MARGENS_ABNT_PX }
			ruler.setMargens(novasMargensPx)
			// Sem isto, só a régua visual mudava — a paginação real do editor
			// (PaginationPlus) continuava com a margem anterior (Finding I1).
			reiniciarEditorComNovaMargem(novasMargensPx)
		})
	}

	// ---- Drop do marcador de margem: reinicia o editor com nova paginação
	// e persiste no ConfiguracaoDocumento do empreendimento selecionado ----
	function iniciarAutosave(editorAtual) {
		window.__autosaveInitCount = (window.__autosaveInitCount || 0) + 1 // instrumentação de teste
		let sujoLocal = false
		editorAtual.on('update', () => { sujoLocal = true })
		autosaveIntervalId = setInterval(() => {
			if (sujoLocal) { sujoLocal = false; salvar() }
		}, 30000)
	}

	function reiniciarEditorComNovaMargem(margensPx) {
		const { from, to } = window._editor.state.selection
		const htmlAtual = window._editor.getHTML()
		if (autosaveIntervalId) { clearInterval(autosaveIntervalId) }
		window._editor.destroy()

		const novoEditor = new T.Editor({
			element: elEditor,
			editorProps: { transformPastedHTML: sanitizarHtmlColado },
			extensions: criarExtensoes(margensPx),
			content: htmlAtual,
		})
		window._editor = novoEditor
		registrarListenersDoEditor(novoEditor)
		try { novoEditor.commands.setTextSelection({ from, to }) } catch (e) { /* seleção fora do range após edição concorrente — ignora */ }
		iniciarAutosave(novoEditor)
		requestAnimationFrame(() => ruler.setNumPaginas(contarPaginas()))
	}

	ruler.onDrop(margensPx => {
		reiniciarEditorComNovaMargem(margensPx)
		const emp = empreendimentoSelecionado()
		if (!emp) { return }
		fetch(`/documentos/empreendimentos/${emp.id}/margens/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
			body: JSON.stringify({
				margem_sup: Math.round(margensPx.top / MM_TO_PX),
				margem_dir: Math.round(margensPx.right / MM_TO_PX),
				margem_inf: Math.round(margensPx.bottom / MM_TO_PX),
				margem_esq: Math.round(margensPx.left / MM_TO_PX),
			}),
		})
			.then(r => r.json().then(d => ({ status: r.status, body: d })))
			.then(({ status, body }) => {
				if (status !== 200 || !body.ok) {
					alert('Não foi possível salvar a margem da página: ' + (body.erros || ['erro desconhecido']).join('\n'))
				}
			})
			.catch(() => {
				alert('Falha de rede ao salvar a margem da página.')
			})
	})

	// ---- Recuo de parágrafo: sincroniza marcadores com o cursor e aplica no drop ----
	function atualizarMarcadoresDeRecuo() {
		const attrs = editorAtivo().getAttributes('paragraph')
		ruler.setIndent({
			indentLeft: attrs.indentLeft || 0,
			indentRight: attrs.indentRight || 0,
			indentFirstLine: attrs.indentFirstLine || 0,
		})
	}

	ruler.onIndentDrop(novoIndent => {
		editorAtivo().chain().focus().updateAttributes('paragraph', novoIndent).run()
	})

	// ---- Toggle de paginação visual ----
	const btnPaginacao = document.getElementById('btnTogglePaginacao')
	if (btnPaginacao) {
		btnPaginacao.addEventListener('click', () => {
			editorAtivo().chain().focus().togglePagination().run()
			btnPaginacao.classList.toggle('active')
		})
	}

	// ---- Contador de caracteres (informativo, sem limite) ----
	const contadorCaracteres = document.getElementById('contadorCaracteres')
	function atualizarContador() {
		if (contadorCaracteres) {
			contadorCaracteres.textContent = `${editorAtivo().storage.characterCount.characters()} caracteres`
		}
	}
	atualizarContador()

	// ---- Colar sem formatação (força texto puro no próximo paste) ----
	const btnColarPuro = document.getElementById('btnColarTextoPuro')
	let colarTextoPuro = false
	if (btnColarPuro) {
		btnColarPuro.addEventListener('click', () => {
			colarTextoPuro = true
			editorAtivo().chain().focus().run()
			btnColarPuro.classList.add('active')
		})
	}
	elEditor.addEventListener('paste', e => {
		if (!colarTextoPuro) { return }
		e.preventDefault()
		e.stopImmediatePropagation()
		const texto = (e.clipboardData || window.clipboardData).getData('text/plain')
		const escapado = texto
			.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
			.split(/\r\n|\r|\n/)
			.map(linha => `<p>${linha || '<br>'}</p>`)
			.join('')
		editorAtivo().chain().focus().insertContent(escapado).run()
		colarTextoPuro = false
		btnColarPuro.classList.remove('active')
	}, true)

	// ---- Toolbar: botões com data-action ----
	document.querySelectorAll('[data-action]').forEach(btn => {
		btn.addEventListener('click', e => {
			e.preventDefault()
			const acao = btn.dataset.action
			const chain = editorAtivo().chain().focus()
			switch (acao) {
				case 'bold': chain.toggleBold().run(); break
				case 'italic': chain.toggleItalic().run(); break
				case 'underline': chain.toggleUnderline().run(); break
				case 'h1': chain.toggleHeading({ level: 1 }).run(); break
				case 'h2': chain.toggleHeading({ level: 2 }).run(); break
				case 'p': chain.setParagraph().run(); break
				case 'left': chain.setTextAlign('left').run(); break
				case 'center': chain.setTextAlign('center').run(); break
				case 'justify': chain.setTextAlign('justify').run(); break
				case 'bullet': chain.toggleBulletList().run(); break
				case 'table': chain.insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(); break
				case 'subscript': chain.toggleSubscript().run(); break
				case 'superscript': chain.toggleSuperscript().run(); break
				case 'hr': chain.setHorizontalRule().run(); break
				case 'link':
					if (editorAtivo().isActive('link')) {
						chain.unsetLink().run()
					} else {
						const url = window.prompt('URL do link:')
						if (url) { chain.setLink({ href: url }).run() }
					}
					break
				case 'undo': chain.undo().run(); break
				case 'redo': chain.redo().run(); break
				case 'clear': chain.unsetAllMarks().clearNodes().run(); break
				case 'color-clear': chain.unsetColor().run(); break
				case 'highlight-clear': chain.unsetHighlight().run(); break
				case 'font-family-clear': chain.setMark('textStyle', { fontFamily: null }).run(); break
				case 'font-size-clear': chain.setMark('textStyle', { fontSize: null }).run(); break
				case 'line-height-clear': chain.updateAttributes('paragraph', { lineHeight: null }).run(); break
				case 'col-before': chain.addColumnBefore().run(); break
				case 'col-after': chain.addColumnAfter().run(); break
				case 'col-del': chain.deleteColumn().run(); break
				case 'row-before': chain.addRowBefore().run(); break
				case 'row-after': chain.addRowAfter().run(); break
				case 'row-del': chain.deleteRow().run(); break
				case 'table-del': chain.deleteTable().run(); break
				default: break
			}
		})
	})

	// ---- Grupo "Tabela": só visível com cursor dentro de tabela ----
	const grupoTabela = document.getElementById('grupoTabela')
	function atualizarGrupoTabela() {
		if (grupoTabela) {
			grupoTabela.style.display = editorAtivo().isActive('table') ? '' : 'none'
		}
	}
	atualizarGrupoTabela()
	atualizarMarcadoresDeRecuo()

	// ---- Cor do texto (paleta fixa) ----
	document.querySelectorAll('[data-color]').forEach(sw => {
		sw.addEventListener('click', e => {
			e.preventDefault()
			editorAtivo().chain().focus().setColor(sw.dataset.color).run()
		})
	})

	// ---- Realce / highlight (paleta fixa) ----
	document.querySelectorAll('[data-highlight]').forEach(sw => {
		sw.addEventListener('click', e => {
			e.preventDefault()
			editorAtivo().chain().focus().toggleHighlight({ color: sw.dataset.highlight }).run()
		})
	})

	// ---- Família da fonte (lista fixa) ----
	document.querySelectorAll('[data-font-family]').forEach(btn => {
		btn.addEventListener('click', e => {
			e.preventDefault()
			editorAtivo().chain().focus().setMark('textStyle', { fontFamily: btn.dataset.fontFamily }).run()
		})
	})

	// ---- Tamanho da fonte (lista fixa, em pt) ----
	document.querySelectorAll('[data-font-size]').forEach(btn => {
		btn.addEventListener('click', e => {
			e.preventDefault()
			editorAtivo().chain().focus().setMark('textStyle', { fontSize: `${btn.dataset.fontSize}pt` }).run()
		})
	})

	// ---- Espaçamento entre linhas (presets fixos) ----
	document.querySelectorAll('[data-line-height]').forEach(btn => {
		btn.addEventListener('click', e => {
			e.preventDefault()
			editorAtivo().chain().focus().updateAttributes('paragraph', { lineHeight: btn.dataset.lineHeight }).run()
		})
	})

	// ---- Sidebar de variáveis: clique insere nó ----
	document.querySelectorAll('[data-var-slug]').forEach(item => {
		item.addEventListener('click', () => {
			const slug = item.dataset.varSlug
			editorAtivo().chain().focus().insertContent({ type: 'variavel', attrs: { slug } }).run()
		})
	})

	// ---- Busca de variáveis ----
	const busca = document.getElementById('buscaVariavel')
	if (busca) {
		busca.addEventListener('input', () => {
			const termo = busca.value.toLowerCase()
			document.querySelectorAll('[data-var-slug]').forEach(item => {
				const txt = item.textContent.toLowerCase()
				item.style.display = txt.includes(termo) ? '' : 'none'
			})
		})
	}

	// ---- Salvar ----
	function coletarPayload() {
		return {
			titulo: document.getElementById('modeloTitulo').value,
			tipo: document.getElementById('modeloTipo').value,
			conteudo_html: editorAtivo().getHTML(),
		}
	}

	function salvar(redirecionar = false) {
		const status = document.getElementById('salvarStatus')
		if (status) { status.textContent = 'salvando...' }
		fetch(salvarUrl, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
			body: JSON.stringify(coletarPayload()),
		})
			.then(r => r.json())
			.then(d => {
				if (d.ok) {
					if (status) { status.textContent = 'salvo' }
					// Modelo novo: passa a salvar no endpoint com pk (evita duplicar).
					if (d.salvar_url) { salvarUrl = d.salvar_url }
					// Só o salvamento manual navega; autosave permanece no editor.
					if (redirecionar && d.redirect) { window.location.href = d.redirect }
				} else {
					if (status) { status.textContent = 'erro' }
					alert((d.erros || ['Erro ao salvar']).join('\n'))
				}
			})
			.catch(() => { if (status) { status.textContent = 'falha de rede' } })
	}

	const btnSalvar = document.getElementById('btnSalvar')
	if (btnSalvar) { btnSalvar.addEventListener('click', () => salvar(true)) }
})()

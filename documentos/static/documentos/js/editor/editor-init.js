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

	const editor = new T.Editor({
		element: elEditor,
		extensions: [
			T.StarterKit,
			T.Underline,
			T.TextAlign.configure({ types: ['heading', 'paragraph'] }),
			T.Table.configure({ resizable: true }),
			T.TableRow, T.TableHeader, T.TableCell,
			T.TextStyle,
			T.Color,
			T.Highlight.configure({ multicolor: true }),
			T.Subscript,
			T.Superscript,
			window.VariavelNode,
		],
		content: cfg.conteudoInicial || '',
	})
	window._editor = editor

	// ---- Toolbar: botões com data-action ----
	document.querySelectorAll('[data-action]').forEach(btn => {
		btn.addEventListener('click', e => {
			e.preventDefault()
			const acao = btn.dataset.action
			const chain = editor.chain().focus()
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
				case 'undo': chain.undo().run(); break
				case 'redo': chain.redo().run(); break
				case 'clear': chain.unsetAllMarks().clearNodes().run(); break
				case 'color-clear': chain.unsetColor().run(); break
				case 'highlight-clear': chain.unsetHighlight().run(); break
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
			grupoTabela.style.display = editor.isActive('table') ? '' : 'none'
		}
	}
	editor.on('selectionUpdate', atualizarGrupoTabela)
	editor.on('transaction', atualizarGrupoTabela)
	atualizarGrupoTabela()

	// ---- Cor do texto (paleta fixa) ----
	document.querySelectorAll('[data-color]').forEach(sw => {
		sw.addEventListener('click', e => {
			e.preventDefault()
			editor.chain().focus().setColor(sw.dataset.color).run()
		})
	})

	// ---- Realce / highlight (paleta fixa) ----
	document.querySelectorAll('[data-highlight]').forEach(sw => {
		sw.addEventListener('click', e => {
			e.preventDefault()
			editor.chain().focus().toggleHighlight({ color: sw.dataset.highlight }).run()
		})
	})

	// ---- Sidebar de variáveis: clique insere nó ----
	document.querySelectorAll('[data-var-slug]').forEach(item => {
		item.addEventListener('click', () => {
			const slug = item.dataset.varSlug
			editor.chain().focus().insertContent({ type: 'variavel', attrs: { slug } }).run()
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
			conteudo_html: editor.getHTML(),
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

	// ---- Autosave 30s quando houver mudança ----
	let sujo = false
	editor.on('update', () => { sujo = true })
	setInterval(() => {
		if (sujo) { sujo = false; salvar() }
	}, 30000)
})()

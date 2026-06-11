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
	const salvarUrl = cfg.salvarUrl

	const editor = new T.Editor({
		element: elEditor,
		extensions: [
			T.StarterKit,
			T.Underline,
			T.TextAlign.configure({ types: ['heading', 'paragraph'] }),
			T.Table.configure({ resizable: true }),
			T.TableRow, T.TableHeader, T.TableCell,
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
				default: break
			}
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

	function salvar() {
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
					if (d.redirect) { window.location.href = d.redirect }
				} else {
					if (status) { status.textContent = 'erro' }
					alert((d.erros || ['Erro ao salvar']).join('\n'))
				}
			})
			.catch(() => { if (status) { status.textContent = 'falha de rede' } })
	}

	const btnSalvar = document.getElementById('btnSalvar')
	if (btnSalvar) { btnSalvar.addEventListener('click', salvar) }

	// ---- Autosave 30s quando houver mudança ----
	let sujo = false
	editor.on('update', () => { sujo = true })
	setInterval(() => {
		if (sujo) { sujo = false; salvar() }
	}, 30000)
})()

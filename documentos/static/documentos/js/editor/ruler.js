// Régua horizontal/vertical estilo Word — zonas de margem de página (cinza),
// ticks em polegada e marcadores arrastáveis para ajustar a margem.
(function () {
	const MM_TO_PX = 96 / 25.4
	const PX_PER_INCH = 96

	function criarTicks(comprimentoPx) {
		const frag = document.createDocumentFragment()
		let posPx = 0
		let polegada = 0
		while (posPx < comprimentoPx) {
			const tick = document.createElement('div')
			tick.className = 'doc-ruler-tick'
			tick.style.left = `${posPx}px`
			tick.textContent = polegada > 0 ? `${polegada}"` : ''
			frag.appendChild(tick)
			posPx += PX_PER_INCH
			polegada += 1
		}
		return frag
	}

	function criarTicksVerticais(comprimentoPx) {
		const frag = document.createDocumentFragment()
		let posPx = 0
		let polegada = 0
		while (posPx < comprimentoPx) {
			const tick = document.createElement('div')
			tick.className = 'doc-ruler-tick doc-ruler-tick-vertical'
			tick.style.top = `${posPx}px`
			tick.textContent = polegada > 0 ? `${polegada}"` : ''
			frag.appendChild(tick)
			posPx += PX_PER_INCH
			polegada += 1
		}
		return frag
	}

	function criarZonaMargem(ladoClasse) {
		const zona = document.createElement('div')
		zona.className = `doc-ruler-margem doc-ruler-margem-${ladoClasse}`
		return zona
	}

	function criarMarcador(tipo, cursor) {
		const marcador = document.createElement('div')
		marcador.className = `doc-ruler-marcador doc-ruler-marcador-${tipo}`
		marcador.style.cursor = cursor
		return marcador
	}

	function init(options) {
		const { horizContainer, vertContainer, pageWidthPx, pageHeightPx } = options
		const pageGapPx = options.pageGapPx || 0
		let margens = { ...options.margensPx }
		let readOnly = !!options.readOnly
		let onDropCb = null

		const horiz = document.createElement('div')
		horiz.className = 'doc-ruler doc-ruler-horizontal'
		horiz.style.width = `${pageWidthPx}px`

		const vert = document.createElement('div')
		vert.className = 'doc-ruler doc-ruler-vertical'

		const zonaEsq = criarZonaMargem('esquerda')
		const zonaDir = criarZonaMargem('direita')

		const marcadorEsq = criarMarcador('margem-esquerda', 'ew-resize')
		const marcadorDir = criarMarcador('margem-direita', 'ew-resize')
		const marcadorSup = criarMarcador('margem-superior', 'ns-resize')
		const marcadorInf = criarMarcador('margem-inferior', 'ns-resize')

		horiz.appendChild(criarTicks(pageWidthPx))
		horiz.appendChild(zonaEsq)
		horiz.appendChild(zonaDir)
		horiz.appendChild(marcadorEsq)
		horiz.appendChild(marcadorDir)

		// Régua vertical estendida a todas as páginas: cada página do documento
		// (PaginationPlus) ganha seu próprio bloco com zona de margem +
		// numeração reiniciada. O marcador arrastável (margem é do documento
		// inteiro, não por página) existe só no bloco 0 — os marcadores em si
		// são criados uma única vez acima e só reaproveitados aqui.
		let blocosPagina = []

		function criarBlocoPagina(indice, offsetTopPx, comMarcadores) {
			const bloco = document.createElement('div')
			bloco.className = 'doc-ruler-pagina'
			bloco.style.top = `${offsetTopPx}px`
			bloco.style.height = `${pageHeightPx}px`
			bloco.appendChild(criarTicksVerticais(pageHeightPx))
			const zonaSup = criarZonaMargem('superior')
			const zonaInf = criarZonaMargem('inferior')
			bloco.appendChild(zonaSup)
			bloco.appendChild(zonaInf)
			if (comMarcadores) {
				bloco.appendChild(marcadorSup)
				bloco.appendChild(marcadorInf)
			}
			return { bloco, zonaSup, zonaInf }
		}

		function setNumPaginas(n) {
			vert.style.height = `${n * pageHeightPx + Math.max(0, n - 1) * pageGapPx}px`
			vert.innerHTML = ''
			blocosPagina = []
			for (let i = 0; i < n; i++) {
				const offsetTop = i * (pageHeightPx + pageGapPx)
				const { bloco, zonaSup, zonaInf } = criarBlocoPagina(i, offsetTop, i === 0)
				vert.appendChild(bloco)
				blocosPagina.push({ zonaSup, zonaInf })
			}
			repintar()
		}

		function repintar() {
			zonaEsq.style.left = '0px'
			zonaEsq.style.width = `${margens.left}px`
			marcadorEsq.style.left = `${margens.left}px`

			zonaDir.style.right = '0px'
			zonaDir.style.width = `${margens.right}px`
			marcadorDir.style.left = `${pageWidthPx - margens.right}px`

			blocosPagina.forEach(({ zonaSup, zonaInf }) => {
				zonaSup.style.top = '0px'
				zonaSup.style.height = `${margens.top}px`
				zonaInf.style.bottom = '0px'
				zonaInf.style.height = `${margens.bottom}px`
			})
			marcadorSup.style.top = `${margens.top}px`
			marcadorInf.style.top = `${pageHeightPx - margens.bottom}px`
		}
		setNumPaginas(1)

		function arrastarHorizontal(marcador, aplicar) {
			marcador.addEventListener('mousedown', e => {
				if (readOnly) { return }
				e.preventDefault()
				const valorInicial = JSON.stringify(margens)
				function onMove(ev) {
					const rect = horiz.getBoundingClientRect()
					const x = Math.max(0, Math.min(pageWidthPx, ev.clientX - rect.left))
					aplicar(x)
					repintar()
				}
				function onUp() {
					document.removeEventListener('mousemove', onMove)
					document.removeEventListener('mouseup', onUp)
					// Clique parado (mousedown+mouseup sem mousemove) não deve
					// disparar reinício do editor nem um POST redundante.
					if (onDropCb && JSON.stringify(margens) !== valorInicial) { onDropCb({ ...margens }) }
				}
				document.addEventListener('mousemove', onMove)
				document.addEventListener('mouseup', onUp)
			})
		}

		function arrastarVertical(marcador, aplicar) {
			marcador.addEventListener('mousedown', e => {
				if (readOnly) { return }
				e.preventDefault()
				const valorInicial = JSON.stringify(margens)
				function onMove(ev) {
					const rect = vert.getBoundingClientRect()
					const y = Math.max(0, Math.min(pageHeightPx, ev.clientY - rect.top))
					aplicar(y)
					repintar()
				}
				function onUp() {
					document.removeEventListener('mousemove', onMove)
					document.removeEventListener('mouseup', onUp)
					if (onDropCb && JSON.stringify(margens) !== valorInicial) { onDropCb({ ...margens }) }
				}
				document.addEventListener('mousemove', onMove)
				document.addEventListener('mouseup', onUp)
			})
		}

		arrastarHorizontal(marcadorEsq, x => { margens.left = Math.round(x) })
		arrastarHorizontal(marcadorDir, x => { margens.right = Math.round(pageWidthPx - x) })
		arrastarVertical(marcadorSup, y => { margens.top = Math.round(y) })
		arrastarVertical(marcadorInf, y => { margens.bottom = Math.round(pageHeightPx - y) })

		// ---- Marcadores de recuo de parágrafo (primeira linha, esquerdo, direito) ----
		const marcadorRecuoPrimeiraLinha = criarMarcador('recuo-primeira-linha', 'ew-resize')
		const marcadorRecuoEsquerdo = criarMarcador('recuo-esquerdo', 'ew-resize')
		const marcadorRecuoDireito = criarMarcador('recuo-direito', 'ew-resize')
		horiz.appendChild(marcadorRecuoPrimeiraLinha)
		horiz.appendChild(marcadorRecuoEsquerdo)
		horiz.appendChild(marcadorRecuoDireito)

		let indentAtual = { indentLeft: 0, indentRight: 0, indentFirstLine: 0 }
		let onIndentDropCb = null

		function repintarIndent() {
			const baseEsq = margens.left + indentAtual.indentLeft
			marcadorRecuoEsquerdo.style.left = `${baseEsq}px`
			marcadorRecuoPrimeiraLinha.style.left = `${baseEsq + indentAtual.indentFirstLine}px`
			marcadorRecuoDireito.style.left = `${pageWidthPx - margens.right - indentAtual.indentRight}px`
		}
		repintarIndent()

		function arrastarIndent(marcador, aplicar) {
			marcador.addEventListener('mousedown', e => {
				e.preventDefault()
				e.stopPropagation()
				const valorInicial = JSON.stringify(indentAtual)
				function onMove(ev) {
					const rect = horiz.getBoundingClientRect()
					const x = Math.max(0, Math.min(pageWidthPx, ev.clientX - rect.left))
					aplicar(x)
					repintarIndent()
				}
				function onUp() {
					document.removeEventListener('mousemove', onMove)
					document.removeEventListener('mouseup', onUp)
					if (onIndentDropCb && JSON.stringify(indentAtual) !== valorInicial) { onIndentDropCb({ ...indentAtual }) }
				}
				document.addEventListener('mousemove', onMove)
				document.addEventListener('mouseup', onUp)
			})
		}

		arrastarIndent(marcadorRecuoEsquerdo, x => { indentAtual.indentLeft = Math.round(x - margens.left) })
		arrastarIndent(marcadorRecuoPrimeiraLinha, x => {
			indentAtual.indentFirstLine = Math.round(x - margens.left - indentAtual.indentLeft)
		})
		arrastarIndent(marcadorRecuoDireito, x => {
			indentAtual.indentRight = Math.round(pageWidthPx - margens.right - x)
		})

		horizContainer.appendChild(horiz)
		vertContainer.appendChild(vert)

		return {
			horizEl: horiz,
			vertEl: vert,
			getMargens: () => ({ ...margens }),
			setMargens(novasMargensPx) {
				margens = { ...margens, ...novasMargensPx }
				repintar()
				repintarIndent()
			},
			setReadOnly(valor) { readOnly = valor },
			onDrop(callback) { onDropCb = callback },
			setNumPaginas,
			setIndent(novoIndent) {
				indentAtual = { ...indentAtual, ...novoIndent }
				repintarIndent()
			},
			onIndentDrop(callback) { onIndentDropCb = callback },
		}
	}

	window.DocRuler = { init, MM_TO_PX, PX_PER_INCH }
})()

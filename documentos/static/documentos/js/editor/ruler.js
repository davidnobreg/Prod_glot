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
		let margens = { ...options.margensPx }
		let readOnly = !!options.readOnly
		let onDropCb = null

		const horiz = document.createElement('div')
		horiz.className = 'doc-ruler doc-ruler-horizontal'
		horiz.style.width = `${pageWidthPx}px`

		const vert = document.createElement('div')
		vert.className = 'doc-ruler doc-ruler-vertical'
		vert.style.height = `${pageHeightPx}px`

		const zonaEsq = criarZonaMargem('esquerda')
		const zonaDir = criarZonaMargem('direita')
		const zonaSup = criarZonaMargem('superior')
		const zonaInf = criarZonaMargem('inferior')

		const marcadorEsq = criarMarcador('margem-esquerda', 'ew-resize')
		const marcadorDir = criarMarcador('margem-direita', 'ew-resize')
		const marcadorSup = criarMarcador('margem-superior', 'ns-resize')
		const marcadorInf = criarMarcador('margem-inferior', 'ns-resize')

		horiz.appendChild(criarTicks(pageWidthPx))
		horiz.appendChild(zonaEsq)
		horiz.appendChild(zonaDir)
		horiz.appendChild(marcadorEsq)
		horiz.appendChild(marcadorDir)
		vert.appendChild(zonaSup)
		vert.appendChild(zonaInf)
		vert.appendChild(marcadorSup)
		vert.appendChild(marcadorInf)

		function repintar() {
			zonaEsq.style.left = '0px'
			zonaEsq.style.width = `${margens.left}px`
			marcadorEsq.style.left = `${margens.left}px`

			zonaDir.style.right = '0px'
			zonaDir.style.width = `${margens.right}px`
			marcadorDir.style.left = `${pageWidthPx - margens.right}px`

			zonaSup.style.top = '0px'
			zonaSup.style.height = `${margens.top}px`
			marcadorSup.style.top = `${margens.top}px`

			zonaInf.style.bottom = '0px'
			zonaInf.style.height = `${margens.bottom}px`
			marcadorInf.style.top = `${pageHeightPx - margens.bottom}px`
		}
		repintar()

		function arrastarHorizontal(marcador, aplicar) {
			marcador.addEventListener('mousedown', e => {
				if (readOnly) { return }
				e.preventDefault()
				function onMove(ev) {
					const rect = horiz.getBoundingClientRect()
					const x = Math.max(0, Math.min(pageWidthPx, ev.clientX - rect.left))
					aplicar(x)
					repintar()
				}
				function onUp() {
					document.removeEventListener('mousemove', onMove)
					document.removeEventListener('mouseup', onUp)
					if (onDropCb) { onDropCb({ ...margens }) }
				}
				document.addEventListener('mousemove', onMove)
				document.addEventListener('mouseup', onUp)
			})
		}

		function arrastarVertical(marcador, aplicar) {
			marcador.addEventListener('mousedown', e => {
				if (readOnly) { return }
				e.preventDefault()
				function onMove(ev) {
					const rect = vert.getBoundingClientRect()
					const y = Math.max(0, Math.min(pageHeightPx, ev.clientY - rect.top))
					aplicar(y)
					repintar()
				}
				function onUp() {
					document.removeEventListener('mousemove', onMove)
					document.removeEventListener('mouseup', onUp)
					if (onDropCb) { onDropCb({ ...margens }) }
				}
				document.addEventListener('mousemove', onMove)
				document.addEventListener('mouseup', onUp)
			})
		}

		arrastarHorizontal(marcadorEsq, x => { margens.left = Math.round(x) })
		arrastarHorizontal(marcadorDir, x => { margens.right = Math.round(pageWidthPx - x) })
		arrastarVertical(marcadorSup, y => { margens.top = Math.round(y) })
		arrastarVertical(marcadorInf, y => { margens.bottom = Math.round(pageHeightPx - y) })

		horizContainer.appendChild(horiz)
		vertContainer.appendChild(vert)

		return {
			horizEl: horiz,
			vertEl: vert,
			getMargens: () => ({ ...margens }),
			setMargens(novasMargensPx) {
				margens = { ...margens, ...novasMargensPx }
				repintar()
			},
			setReadOnly(valor) { readOnly = valor },
			onDrop(callback) { onDropCb = callback },
		}
	}

	window.DocRuler = { init, MM_TO_PX, PX_PER_INCH }
})()

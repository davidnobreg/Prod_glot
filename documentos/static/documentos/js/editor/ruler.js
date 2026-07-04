// Régua horizontal/vertical estilo Word — zonas de margem de página (cinza)
// e ticks em polegada. Renderização estática nesta fase; drag vem depois.
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

	function init(options) {
		const { horizContainer, vertContainer, pageWidthPx, pageHeightPx } = options
		let margens = { ...options.margensPx }

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

		horiz.appendChild(criarTicks(pageWidthPx))
		horiz.appendChild(zonaEsq)
		horiz.appendChild(zonaDir)
		vert.appendChild(zonaSup)
		vert.appendChild(zonaInf)

		function repintar() {
			zonaEsq.style.left = '0px'
			zonaEsq.style.width = `${margens.left}px`
			zonaDir.style.right = '0px'
			zonaDir.style.width = `${margens.right}px`
			zonaSup.style.top = '0px'
			zonaSup.style.height = `${margens.top}px`
			zonaInf.style.bottom = '0px'
			zonaInf.style.height = `${margens.bottom}px`
		}
		repintar()

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
		}
	}

	window.DocRuler = { init, MM_TO_PX, PX_PER_INCH }
})()
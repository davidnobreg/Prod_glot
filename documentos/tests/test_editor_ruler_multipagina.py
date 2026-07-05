import pytest
from django.urls import reverse

from documentos.models import ModeloDocumento, TipoDocumento

PAGE_HEIGHT_PX = 1123
PAGE_GAP_PX = 30


@pytest.fixture
def modelo_multipagina(superuser):
	conteudo = '<p>Texto de teste para paginação.</p>' * 60
	return ModeloDocumento.objects.create(
		titulo='Contrato Multipágina Teste',
		tipo=TipoDocumento.CONTRATO,
		conteudo_html=conteudo,
		criado_por=superuser,
	)


@pytest.mark.django_db
def test_regua_vertical_altura_acompanha_numero_de_paginas(logged_browser, live_server, modelo_multipagina):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_multipagina.pk])}'
	page.goto(url)
	page.wait_for_selector('.doc-ruler-vertical')
	page.wait_for_timeout(500)  # requestAnimationFrame da contagem inicial de páginas

	num_paginas = page.evaluate("document.querySelectorAll('#tiptapEditor .rm-page-header').length")
	assert num_paginas >= 2

	altura_esperada = num_paginas * PAGE_HEIGHT_PX + max(0, num_paginas - 1) * PAGE_GAP_PX
	altura_real = page.evaluate(
		"parseFloat(getComputedStyle(document.querySelector('.doc-ruler-vertical')).height)"
	)
	assert abs(altura_real - altura_esperada) < 2


@pytest.mark.django_db
def test_regua_vertical_so_primeira_pagina_tem_marcador_arrastavel(logged_browser, live_server, modelo_multipagina):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_multipagina.pk])}'
	page.goto(url)
	page.wait_for_selector('.doc-ruler-vertical')
	page.wait_for_timeout(500)

	assert page.locator('.doc-ruler-marcador-margem-superior').count() == 1
	assert page.locator('.doc-ruler-marcador-margem-inferior').count() == 1


@pytest.mark.django_db
def test_regua_vertical_cada_pagina_tem_zona_de_margem(logged_browser, live_server, modelo_multipagina):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_multipagina.pk])}'
	page.goto(url)
	page.wait_for_selector('.doc-ruler-vertical')
	page.wait_for_timeout(500)

	num_paginas = page.evaluate("document.querySelectorAll('#tiptapEditor .rm-page-header').length")
	assert page.locator('.doc-ruler-pagina .doc-ruler-margem-superior').count() == num_paginas
	assert page.locator('.doc-ruler-pagina .doc-ruler-margem-inferior').count() == num_paginas

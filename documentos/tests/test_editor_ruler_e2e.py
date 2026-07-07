import pytest
from django.urls import reverse

from documentos.models import ConfiguracaoDocumento, EmpreendimentoDocumento, ModeloDocumento, TipoDocumento
from empreendimentos.models import Empreendimento


@pytest.fixture
def cenario_completo(superuser):
	empr = Empreendimento.objects.create(
		nome='Loteamento E2E Régua', telefone='(83) 95555-5555',
		tempo_reserva=30, quantidade_parcela=60,
	)
	ConfiguracaoDocumento.objects.create(empreendimento=empr, margem_sup=25, margem_dir=20, margem_inf=20, margem_esq=30)
	modelo = ModeloDocumento.objects.create(
		titulo='Contrato E2E Régua', tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Cláusula primeira. Texto de teste E2E que deve sobreviver a tudo.</p>',
		criado_por=superuser,
	)
	EmpreendimentoDocumento.objects.create(empreendimento=empr, modelo=modelo)
	return modelo, empr


@pytest.mark.django_db
def test_fluxo_completo_regua_margem_e_recuo(logged_browser, live_server, cenario_completo):
	modelo, empr = cenario_completo
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo.pk])}'
	page.goto(url)
	page.wait_for_selector('.doc-ruler-horizontal')

	texto_original = page.evaluate('window._editor.getHTML()')
	assert 'Cláusula primeira' in texto_original

	page.select_option('#modeloEmpreendimento', str(empr.uuid))

	marcador_margem = page.locator('.doc-ruler-marcador-margem-esquerda')
	box = marcador_margem.bounding_box()
	page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
	page.mouse.down()
	page.mouse.move(box['x'] + box['width'] / 2 + 30, box['y'] + box['height'] / 2)
	page.mouse.up()
	page.wait_for_timeout(500)

	page.click('#tiptapEditor .ProseMirror p')
	marcador_indent = page.locator('.doc-ruler-marcador-recuo-esquerdo')
	box2 = marcador_indent.bounding_box()
	page.mouse.move(box2['x'] + box2['width'] / 2, box2['y'] + box2['height'] / 2)
	page.mouse.down()
	page.mouse.move(box2['x'] + box2['width'] / 2 + 20, box2['y'] + box2['height'] / 2)
	page.mouse.up()

	texto_final = page.evaluate('window._editor.getHTML()')
	assert 'Cláusula primeira' in texto_final
	assert 'margin-left:' in texto_final

	empr.refresh_from_db()
	cfg = ConfiguracaoDocumento.objects.get(empreendimento=empr)
	assert cfg.margem_esq != 30

	page.screenshot(path='documentos/tests/screenshots/editor_regua_e2e.png', full_page=True)

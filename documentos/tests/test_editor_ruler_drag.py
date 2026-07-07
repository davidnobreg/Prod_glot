import pytest
from django.urls import reverse

from documentos.models import ConfiguracaoDocumento, EmpreendimentoDocumento, ModeloDocumento, TipoDocumento
from empreendimentos.models import Empreendimento


@pytest.fixture
def modelo_com_empreendimento(superuser):
	empr = Empreendimento.objects.create(
		nome='Loteamento Drag Teste', telefone='(83) 96666-6666',
		tempo_reserva=30, quantidade_parcela=60,
	)
	ConfiguracaoDocumento.objects.create(empreendimento=empr, margem_sup=25, margem_dir=20, margem_inf=20, margem_esq=30)
	modelo = ModeloDocumento.objects.create(
		titulo='Contrato Drag Teste', tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Texto original que não pode sumir.</p>', criado_por=superuser,
	)
	EmpreendimentoDocumento.objects.create(empreendimento=empr, modelo=modelo)
	return modelo, empr


@pytest.mark.django_db
def test_arrastar_marcador_de_margem_persiste_e_preserva_texto(logged_browser, live_server, modelo_com_empreendimento):
	modelo, empr = modelo_com_empreendimento
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo.uuid])}'
	page.goto(url)
	page.wait_for_selector('.doc-ruler-horizontal')
	page.select_option('#modeloEmpreendimento', str(empr.uuid))

	marcador = page.locator('.doc-ruler-marcador-margem-esquerda')
	box = marcador.bounding_box()
	page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
	page.mouse.down()
	page.mouse.move(box['x'] + box['width'] / 2 + 40, box['y'] + box['height'] / 2)
	page.mouse.up()

	page.wait_for_timeout(500)  # fetch de persistência é assíncrono

	texto_atual = page.evaluate('window._editor.getHTML()')
	assert 'Texto original que não pode sumir' in texto_atual

	empr.refresh_from_db()
	cfg = ConfiguracaoDocumento.objects.get(empreendimento=empr)
	assert cfg.margem_esq != 30

	# Reinício do editor não pode deixar um autosave "fantasma": deve ter
	# rodado iniciarAutosave() exatamente três vezes (carga inicial + o
	# select_option acima, que agora também reinicia o editor para repaginar
	# com a margem do empreendimento escolhido — Finding I1 + 1 drop de
	# margem), não mais que isso (senão o setInterval antigo não foi limpo
	# no destroy).
	contagem_autosave = page.evaluate('window.__autosaveInitCount')
	assert contagem_autosave == 3


@pytest.mark.django_db
def test_toolbar_atua_no_editor_vivo_apos_drag_de_margem(logged_browser, live_server, modelo_com_empreendimento):
	# Regressão: reiniciarEditorComNovaMargem() destrói o Editor original e
	# cria outro, reatribuindo window._editor. Antes da correção, a toolbar
	# (e outros handlers) fechavam sobre a const `editor` original — depois
	# do drag, clicar em "negrito" não fazia nada, pois agia sobre uma
	# instância já destruída. Este teste arrasta a régua e então exercita
	# a toolbar, provando que ela passou a agir sobre o editor vivo.
	modelo, empr = modelo_com_empreendimento
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo.uuid])}'
	page.goto(url)
	page.wait_for_selector('.doc-ruler-horizontal')
	page.select_option('#modeloEmpreendimento', str(empr.uuid))

	marcador = page.locator('.doc-ruler-marcador-margem-esquerda')
	box = marcador.bounding_box()
	page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
	page.mouse.down()
	page.mouse.move(box['x'] + box['width'] / 2 + 40, box['y'] + box['height'] / 2)
	page.mouse.up()
	page.wait_for_timeout(500)  # fetch de persistência + reinício do editor são assíncronos

	# Seleciona todo o texto via API do TipTap (equivalente a um Ctrl+A) e
	# então aciona o botão de negrito da toolbar.
	page.evaluate('window._editor.commands.selectAll()')
	page.click('[data-action="bold"]')
	page.wait_for_timeout(200)

	html_atual = page.evaluate('window._editor.getHTML()')
	assert '<strong>' in html_atual

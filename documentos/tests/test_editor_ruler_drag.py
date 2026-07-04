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
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo.pk])}'
	page.goto(url)
	page.wait_for_selector('.doc-ruler-horizontal')
	page.select_option('#modeloEmpreendimento', str(empr.pk))

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
	# rodado iniciarAutosave() exatamente duas vezes (carga inicial + 1 drop),
	# não mais que isso (senão o setInterval antigo não foi limpo no destroy).
	contagem_autosave = page.evaluate('window.__autosaveInitCount')
	assert contagem_autosave == 2

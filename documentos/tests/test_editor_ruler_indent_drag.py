import pytest
from django.urls import reverse

from documentos.models import ConfiguracaoDocumento, EmpreendimentoDocumento, ModeloDocumento, TipoDocumento
from empreendimentos.models import Empreendimento


@pytest.fixture
def modelo_com_paragrafo(superuser):
	return ModeloDocumento.objects.create(
		titulo='Contrato Indent Drag Teste',
		tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Parágrafo alvo do recuo.</p>',
		criado_por=superuser,
	)


@pytest.fixture
def modelo_com_paragrafo_e_empreendimento(superuser):
	empr = Empreendimento.objects.create(
		nome='Loteamento Indent Drag Teste', telefone='(83) 95555-5555',
		tempo_reserva=30, quantidade_parcela=60,
	)
	ConfiguracaoDocumento.objects.create(empreendimento=empr, margem_sup=25, margem_dir=20, margem_inf=20, margem_esq=30)
	modelo = ModeloDocumento.objects.create(
		titulo='Contrato Indent Drag + Margem Teste', tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Parágrafo que precisa sobreviver ao reinício do editor.</p>', criado_por=superuser,
	)
	EmpreendimentoDocumento.objects.create(empreendimento=empr, modelo=modelo)
	return modelo, empr


@pytest.mark.django_db
def test_arrastar_marcador_de_recuo_atualiza_paragrafo(logged_browser, live_server, modelo_com_paragrafo):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_paragrafo.pk])}'
	page.goto(url)
	page.wait_for_selector('#tiptapEditor .ProseMirror')

	page.click('#tiptapEditor .ProseMirror p')

	marcador = page.locator('.doc-ruler-marcador-recuo-esquerdo')
	box = marcador.bounding_box()
	page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
	page.mouse.down()
	page.mouse.move(box['x'] + box['width'] / 2 + 40, box['y'] + box['height'] / 2)
	page.mouse.up()

	html_depois = page.evaluate('window._editor.getHTML()')
	assert 'margin-left:' in html_depois
	assert 'Parágrafo alvo do recuo' in html_depois


@pytest.mark.django_db
def test_marcadores_de_recuo_seguem_o_paragrafo_do_cursor(logged_browser, live_server, modelo_com_paragrafo):
	# Regressão: mover o cursor para um parágrafo com atributos de recuo
	# diferentes deve reposicionar os marcadores (via selectionUpdate/transaction),
	# sem exigir um drag.
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_paragrafo.pk])}'
	page.goto(url)
	page.wait_for_selector('#tiptapEditor .ProseMirror')

	page.evaluate('''
		() => {
			window._editor.chain().focus().updateAttributes('paragraph', {
				indentLeft: 60, indentRight: 0, indentFirstLine: 0,
			}).run()
		}
	''')
	page.wait_for_timeout(100)

	marcador = page.locator('.doc-ruler-marcador-recuo-esquerdo')
	left_estilo = marcador.evaluate('el => el.style.left')
	assert left_estilo != ''
	assert left_estilo != '0px'


@pytest.mark.django_db
def test_recuo_sobrevive_a_reinicio_de_editor_por_drag_de_margem(
	logged_browser, live_server, modelo_com_paragrafo_e_empreendimento,
):
	# Regressão: reiniciarEditorComNovaMargem() (Task 5) destrói e recria o
	# Editor. O recuo aplicado por drag antes disso precisa sobreviver ao
	# round-trip getHTML()/content, já que é serializado como estilo inline
	# no parágrafo (IndentAttrsExtension) e não é estado interno do ruler.
	modelo, empr = modelo_com_paragrafo_e_empreendimento
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo.pk])}'
	page.goto(url)
	page.wait_for_selector('#tiptapEditor .ProseMirror')
	page.select_option('#modeloEmpreendimento', str(empr.pk))

	page.click('#tiptapEditor .ProseMirror p')

	marcador_recuo = page.locator('.doc-ruler-marcador-recuo-esquerdo')
	box = marcador_recuo.bounding_box()
	page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
	page.mouse.down()
	page.mouse.move(box['x'] + box['width'] / 2 + 40, box['y'] + box['height'] / 2)
	page.mouse.up()

	html_com_recuo = page.evaluate('window._editor.getHTML()')
	assert 'margin-left:' in html_com_recuo

	marcador_margem = page.locator('.doc-ruler-marcador-margem-esquerda')
	box = marcador_margem.bounding_box()
	page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
	page.mouse.down()
	page.mouse.move(box['x'] + box['width'] / 2 + 40, box['y'] + box['height'] / 2)
	page.mouse.up()
	page.wait_for_timeout(500)  # fetch de persistência + reinício do editor são assíncronos

	html_depois_do_reinicio = page.evaluate('window._editor.getHTML()')
	assert 'margin-left:' in html_depois_do_reinicio
	assert 'Parágrafo que precisa sobreviver ao reinício do editor' in html_depois_do_reinicio

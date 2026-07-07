import pytest
from django.urls import reverse

from documentos.models import ModeloDocumento, TipoDocumento


@pytest.fixture
def modelo_com_paragrafo(superuser):
	return ModeloDocumento.objects.create(
		titulo='Contrato Indent Teste',
		tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Parágrafo de teste para recuo.</p>',
		criado_por=superuser,
	)


@pytest.mark.django_db
def test_paragrafo_aceita_e_persiste_atributos_de_recuo(logged_browser, live_server, modelo_com_paragrafo):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_paragrafo.uuid])}'
	page.goto(url)
	page.wait_for_selector('#tiptapEditor .ProseMirror')

	html_antes = page.evaluate('window._editor.getHTML()')
	assert 'Parágrafo de teste' in html_antes

	page.evaluate('''
		() => {
			window._editor.chain().focus().updateAttributes('paragraph', {
				indentLeft: 40, indentRight: 20, indentFirstLine: -20,
			}).run()
		}
	''')
	html_depois = page.evaluate('window._editor.getHTML()')
	assert 'margin-left: 40px' in html_depois
	assert 'margin-right: 20px' in html_depois
	assert 'text-indent: -20px' in html_depois
	assert 'Parágrafo de teste' in html_depois
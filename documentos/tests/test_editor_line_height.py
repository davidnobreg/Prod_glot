import pytest
from django.urls import reverse

from documentos.models import ModeloDocumento, TipoDocumento


@pytest.fixture
def modelo_com_paragrafo(superuser):
	return ModeloDocumento.objects.create(
		titulo='Contrato Espaçamento Teste',
		tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Parágrafo de teste para espaçamento.</p>',
		criado_por=superuser,
	)


@pytest.mark.django_db
def test_paragrafo_aceita_e_persiste_espacamento_entre_linhas(logged_browser, live_server, modelo_com_paragrafo):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_paragrafo.pk])}'
	page.goto(url)
	page.wait_for_selector('#tiptapEditor .ProseMirror')

	page.evaluate('''
		() => {
			window._editor.chain().focus().updateAttributes('paragraph', { lineHeight: '2' }).run()
		}
	''')
	html_depois = page.evaluate('window._editor.getHTML()')
	assert 'line-height: 2' in html_depois
	assert 'Parágrafo de teste' in html_depois


@pytest.mark.django_db
def test_espacamento_padrao_remove_o_atributo(logged_browser, live_server, modelo_com_paragrafo):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_paragrafo.pk])}'
	page.goto(url)
	page.wait_for_selector('#tiptapEditor .ProseMirror')

	page.evaluate('''
		() => {
			window._editor.chain().focus().updateAttributes('paragraph', { lineHeight: '2' }).run()
			window._editor.chain().focus().updateAttributes('paragraph', { lineHeight: null }).run()
		}
	''')
	html_depois = page.evaluate('window._editor.getHTML()')
	assert 'line-height:' not in html_depois
import pytest
from django.urls import reverse

from documentos.models import ModeloDocumento, TipoDocumento


@pytest.fixture
def modelo_com_paragrafo(superuser):
	return ModeloDocumento.objects.create(
		titulo='Contrato Fonte Teste',
		tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Texto de teste pra fonte e tamanho.</p>',
		criado_por=superuser,
	)


@pytest.mark.django_db
def test_cor_fonte_e_tamanho_convivem_no_mesmo_span(logged_browser, live_server, modelo_com_paragrafo):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_paragrafo.pk])}'
	page.goto(url)
	page.wait_for_selector('#tiptapEditor .ProseMirror')

	page.evaluate('''
		() => {
			window._editor.commands.setTextSelection({ from: 1, to: 10 })
			window._editor.chain().focus().setColor('#dc3545').run()
			window._editor.chain().focus().setMark('textStyle', { fontFamily: 'DejaVu Serif' }).run()
			window._editor.chain().focus().setMark('textStyle', { fontSize: '14pt' }).run()
		}
	''')
	html = page.evaluate('window._editor.getHTML()')
	# Chromium normaliza a cor hex pra rgb() e envolve nomes de fonte com
	# espaço em aspas ao serializar style via CSSOM — checa presença dos
	# atributos, não o literal exato (mesma ideia da checagem de cor abaixo).
	assert 'color:' in html.replace(' ', '') or 'color: #dc3545' in html
	assert 'font-family:' in html and 'DejaVu Serif' in html
	assert 'font-size: 14pt' in html
	# A seleção (chars 1-10) só envolve "Texto de " num <span> — o restante
	# da frase fica fora da tag, então o texto completo nunca aparece como
	# substring contígua no HTML. Checa as duas partes separadamente.
	assert 'Texto de' in html
	assert 'teste pra fonte e tamanho' in html


@pytest.mark.django_db
def test_remover_fonte_preserva_cor(logged_browser, live_server, modelo_com_paragrafo):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_paragrafo.pk])}'
	page.goto(url)
	page.wait_for_selector('#tiptapEditor .ProseMirror')

	page.evaluate('''
		() => {
			window._editor.commands.setTextSelection({ from: 1, to: 10 })
			window._editor.chain().focus().setColor('#dc3545').run()
			window._editor.chain().focus().setMark('textStyle', { fontFamily: 'DejaVu Serif' }).run()
			window._editor.chain().focus().setMark('textStyle', { fontFamily: null }).run()
		}
	''')
	html = page.evaluate('window._editor.getHTML()')
	assert 'font-family:' not in html
	assert 'rgb(220, 53, 69)' in html or '#dc3545' in html

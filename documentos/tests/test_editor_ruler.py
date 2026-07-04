import pytest
from django.urls import reverse

from documentos.models import ConfiguracaoDocumento, EmpreendimentoDocumento, ModeloDocumento, TipoDocumento
from empreendimentos.models import Empreendimento


@pytest.fixture
def modelo_com_empreendimento(superuser):
	empr = Empreendimento.objects.create(
		nome='Loteamento Ruler Teste', telefone='(83) 97777-7777',
		tempo_reserva=30, quantidade_parcela=60,
	)
	ConfiguracaoDocumento.objects.create(empreendimento=empr, margem_sup=30, margem_dir=25, margem_inf=25, margem_esq=35)
	modelo = ModeloDocumento.objects.create(
		titulo='Contrato Ruler Teste', tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Texto de teste.</p>', criado_por=superuser,
	)
	EmpreendimentoDocumento.objects.create(empreendimento=empr, modelo=modelo)
	return modelo


@pytest.mark.django_db
def test_regua_renderiza_com_zonas_de_margem(logged_browser, live_server, modelo_com_empreendimento):
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_empreendimento.pk])}'
	page.goto(url)
	page.wait_for_selector('.doc-ruler-horizontal')
	page.wait_for_selector('.doc-ruler-vertical')

	largura_esq = page.eval_on_selector('.doc-ruler-margem-esquerda', 'el => el.style.width')
	assert largura_esq != ''

	# 35mm * (96/25.4) ~= 132.28px -> arredondado
	largura_px = float(largura_esq.replace('px', ''))
	assert 125 < largura_px < 140


@pytest.mark.django_db
def test_paginacao_real_usa_margem_do_empreendimento_desde_a_carga_inicial(
	logged_browser, live_server, modelo_com_empreendimento,
):
	# Finding I1: antes da correção, o `new T.Editor(...)` inicial sempre
	# hardcodava ABNT (25/20/20/30mm) em PaginationPlus, mesmo com um
	# empreendimento de margens diferentes (30/25/25/35mm) já vinculado.
	# A régua visual mostrava a margem certa, mas a paginação REAL do editor
	# (refletida nas CSS custom properties --rm-margin-* que o PaginationPlus
	# escreve em editor.view.dom) continuava ABNT até um drag manual.
	# Este teste NÃO arrasta nada: só carrega a página e confere que a
	# paginação já nasce certa.
	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo_com_empreendimento.pk])}'
	page.goto(url)
	page.wait_for_selector('.doc-ruler-horizontal')

	margem_esq_px = page.evaluate(
		"getComputedStyle(window._editor.view.dom).getPropertyValue('--rm-margin-left')"
	)
	valor_px = float(margem_esq_px.replace('px', '').strip())
	# 35mm * 96/25.4 ~= 132.28px. Se ainda fosse ABNT (30mm), daria ~113px.
	assert 125 < valor_px < 140


@pytest.mark.django_db
def test_trocar_empreendimento_no_dropdown_repagina_o_editor(logged_browser, live_server, superuser):
	# Finding I1: ao trocar o empreendimento no dropdown, só ruler.setMargens()
	# era chamado — a paginação real do editor (PaginationPlus) não
	# acompanhava a régua visual. Este teste vincula dois empreendimentos com
	# margens diferentes ao mesmo modelo e alterna entre eles (e para o
	# "Padrão ABNT"), conferindo que a paginação real (--rm-margin-left)
	# muda a cada troca, sem precisar de nenhum drag.
	empr1 = Empreendimento.objects.create(
		nome='Loteamento Dropdown A', telefone='(83) 91111-1111',
		tempo_reserva=30, quantidade_parcela=60,
	)
	ConfiguracaoDocumento.objects.create(empreendimento=empr1, margem_sup=30, margem_dir=25, margem_inf=25, margem_esq=35)
	empr2 = Empreendimento.objects.create(
		nome='Loteamento Dropdown B', telefone='(83) 92222-2222',
		tempo_reserva=30, quantidade_parcela=60,
	)
	ConfiguracaoDocumento.objects.create(empreendimento=empr2, margem_sup=40, margem_dir=15, margem_inf=15, margem_esq=50)
	modelo = ModeloDocumento.objects.create(
		titulo='Contrato Dropdown Teste', tipo=TipoDocumento.CONTRATO,
		conteudo_html='<p>Texto de teste.</p>', criado_por=superuser,
	)
	EmpreendimentoDocumento.objects.create(empreendimento=empr1, modelo=modelo, ordem=0)
	EmpreendimentoDocumento.objects.create(empreendimento=empr2, modelo=modelo, ordem=1)

	page = logged_browser
	url = f'{live_server.url}{reverse("documentos:modelo-editor", args=[modelo.pk])}'
	page.goto(url)
	page.wait_for_selector('.doc-ruler-horizontal')

	def margem_esq_atual():
		valor = page.evaluate(
			"getComputedStyle(window._editor.view.dom).getPropertyValue('--rm-margin-left')"
		)
		return float(valor.replace('px', '').strip())

	# empr1 é o primeiro vínculo -> margensIniciais já usa suas margens (35mm ~132px).
	assert 125 < margem_esq_atual() < 140

	page.select_option('#modeloEmpreendimento', str(empr2.pk))
	page.wait_for_timeout(300)
	# empr2: 50mm ~= 188.9px
	assert 180 < margem_esq_atual() < 200

	page.select_option('#modeloEmpreendimento', '')
	page.wait_for_timeout(300)
	# Padrão ABNT: 30mm ~= 113.4px
	assert 105 < margem_esq_atual() < 120
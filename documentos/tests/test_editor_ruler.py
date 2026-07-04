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
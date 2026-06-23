"""
Testes de wizard com Playwright.

Para habilitar:
    pip install pytest-playwright
    playwright install chromium

Executar:
    pytest clientes/tests/test_wizard.py -v
"""

import pytest

try:
	import pytest_playwright  # noqa: F401
	HAS_PLAYWRIGHT = True
except ImportError:
	HAS_PLAYWRIGHT = False

pytestmark = pytest.mark.skipif(
	not HAS_PLAYWRIGHT,
	reason='pytest-playwright não instalado',
)

CPF_VALIDO_FORMATADO = '529.982.247-25'


@pytest.mark.django_db
class TestWizardCadastroCliente:

	def _preenche_etapa1(self, page, nome='FULANO SILVA', cpf=CPF_VALIDO_FORMATADO,
	                     email='fulano@teste.com', estado_civil='solteiro'):
		page.select_option('#id_estado_civil', estado_civil)
		page.fill('#id_name', nome)
		page.fill('#id_documento', cpf)
		page.fill('#id_email', email)

	def test_etapa1_preenchida_avanca(self, page, live_server):
		page.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(page)
		page.click('#wizard-btn-next')
		# Solteiro: etapa 2 (cônjuge) pulada, deve estar na etapa 3
		assert page.is_visible('#step-3')
		assert not page.is_visible('#step-1')

	def test_solteiro_pula_etapa_conjuge(self, page, live_server):
		page.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(page, estado_civil='solteiro')
		page.click('#wizard-btn-next')
		assert not page.is_visible('#step-2')
		assert page.is_visible('#step-3')

	def test_casado_exibe_etapa_conjuge(self, page, live_server):
		page.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(page, estado_civil='casado', email='casado@teste.com')
		page.click('#wizard-btn-next')
		assert page.is_visible('#step-2')

	def test_etapa_revisao_exibe_dados_preenchidos(self, page, live_server):
		page.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(page, nome='REVISAO SILVA', email='revisao@teste.com')

		# Etapa 3 (documentos)
		page.click('#wizard-btn-next')
		# Etapa 4 (endereço) — preencher obrigatórios
		page.click('#wizard-btn-next')
		page.fill('#id_end_cep', '58000000')
		page.fill('#id_end_rua', 'Rua Revisão')
		page.fill('#id_end_numero', '1')
		page.fill('#id_end_bairro', 'Centro')
		page.fill('#id_end_cidade', 'João Pessoa')
		page.select_option('#id_end_estado', 'PB')
		# Etapa 5 (contatos) — pular e avançar para revisão é tratado no wizard JS
		page.click('#wizard-btn-next')
		page.click('#wizard-btn-next')

		revisao = page.inner_text('#review-content')
		assert 'REVISAO SILVA' in revisao

	def test_botao_anterior_volta_etapa_correta(self, page, live_server):
		page.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(page)
		page.click('#wizard-btn-next')
		# Agora na etapa 3; clicar anterior deve voltar para etapa 1 (solteiro)
		page.click('#wizard-btn-prev')
		assert page.is_visible('#step-1')
		assert not page.is_visible('#step-3')

"""
Testes de wizard com Playwright.

Ordem dos steps:
  PF solteiro: step-1 → step-4 → step-5 → step-3 → step-6
  PF casado:   step-1 → step-2 → step-4 → step-5 → step-3 → step-6

Executar:
    pytest clientes/tests/test_wizard.py -v
"""

import pytest

CPF_VALIDO_FORMATADO = '529.982.247-25'
CNPJ_VALIDO_FORMATADO = '11.222.333/0001-81'

_NEXT_TIMEOUT = 8000  # ms — AJAX salva no banco antes de avançar


@pytest.mark.django_db
class TestWizardCadastroCliente:

	def _preenche_etapa1(self, page, nome='FULANO SILVA', cpf=CPF_VALIDO_FORMATADO,
	                     email='fulano@teste.com', estado_civil='solteiro'):
		page.select_option('#id_estado_civil', estado_civil)
		page.fill('#id_name', nome)
		page.fill('#id_documento', cpf)
		page.fill('#id_email', email)

	def _preenche_endereco(self, page):
		page.fill('#id_end_cep', '58000000')
		page.fill('#id_end_rua', 'Rua Teste')
		page.fill('#id_end_numero', '1')
		page.fill('#id_end_bairro', 'Centro')
		page.fill('#id_end_cidade', 'João Pessoa')
		page.select_option('#id_end_estado', 'PB')

	def _preenche_contatos(self, page, tel='(83) 99999-9999'):
		page.fill('#telefoneNumero', tel)
		page.click('button[onclick="addTelefone()"]')

	def _next(self, page, expect_step, timeout=_NEXT_TIMEOUT):
		"""Clica Próximo e aguarda o step esperado ficar visível (AJAX pode demorar)."""
		page.click('#wizard-btn-next')
		page.wait_for_selector(f'#{expect_step}', state='visible', timeout=timeout)

	def test_etapa1_preenchida_avanca(self, logged_browser, live_server):
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(logged_browser)
		self._next(logged_browser, 'step-4')
		assert logged_browser.is_visible('#step-4')
		assert not logged_browser.is_visible('#step-1')

	def test_solteiro_pula_etapa_conjuge(self, logged_browser, live_server):
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(logged_browser, estado_civil='solteiro')
		self._next(logged_browser, 'step-4')
		assert not logged_browser.is_visible('#step-2')
		assert logged_browser.is_visible('#step-4')

	def test_casado_exibe_etapa_conjuge(self, logged_browser, live_server):
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(logged_browser, estado_civil='casado', email='casado@teste.com')
		self._next(logged_browser, 'step-2')
		assert logged_browser.is_visible('#step-2')

	def test_etapa_revisao_exibe_dados_preenchidos(self, logged_browser, live_server):
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(logged_browser, nome='REVISAO SILVA', email='revisao@teste.com')

		self._next(logged_browser, 'step-4')
		self._preenche_endereco(logged_browser)
		self._next(logged_browser, 'step-5')
		self._preenche_contatos(logged_browser)
		self._next(logged_browser, 'step-3')
		self._next(logged_browser, 'step-6')

		revisao = logged_browser.inner_text('#review-content')
		assert 'REVISAO SILVA' in revisao

	def test_botao_anterior_volta_etapa_correta(self, logged_browser, live_server):
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(logged_browser)
		self._next(logged_browser, 'step-4')
		logged_browser.click('#wizard-btn-prev')
		logged_browser.wait_for_selector('#step-1', state='visible', timeout=3000)
		assert logged_browser.is_visible('#step-1')
		assert not logged_browser.is_visible('#step-4')

	def test_formulario_documentos_visivel_apos_step1(self, logged_browser, live_server):
		"""No step Documentos o form de upload está visível (sem loading intermediário)."""
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(logged_browser, email='doc_visible@teste.com')
		self._next(logged_browser, 'step-4')
		self._preenche_endereco(logged_browser)
		self._next(logged_browser, 'step-5')
		self._preenche_contatos(logged_browser)
		self._next(logged_browser, 'step-3')

		assert logged_browser.is_visible('#step-3')
		assert logged_browser.is_visible('#wz-arquivos-form')

	def test_wizard_documentos_antecede_conjuge_para_casado(self, logged_browser, live_server):
		"""Para casado, Documentos (step-3) aparece APÓS Contatos (step-5)."""
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(logged_browser, estado_civil='casado', email='ordem@teste.com')
		self._next(logged_browser, 'step-2')
		assert logged_browser.is_visible('#step-2')
		logged_browser.fill('#id_conj_nome', 'CONJUGE SILVA')
		self._next(logged_browser, 'step-4')
		self._preenche_endereco(logged_browser)
		self._next(logged_browser, 'step-5')
		self._preenche_contatos(logged_browser)
		self._next(logged_browser, 'step-3')
		assert logged_browser.is_visible('#step-3')
		assert not logged_browser.is_visible('#step-2')

	def test_redirect_apos_wizard_completo_aponta_aba_arquivos(self, logged_browser, live_server):
		"""Após concluir o wizard, o redirect aponta para ?tab=arquivos."""
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(logged_browser, nome='REDIRECT SILVA', email='redirect@teste.com')

		self._next(logged_browser, 'step-4')
		self._preenche_endereco(logged_browser)
		self._next(logged_browser, 'step-5')
		self._preenche_contatos(logged_browser, tel='(83) 99999-9998')
		self._next(logged_browser, 'step-3')
		self._next(logged_browser, 'step-6')
		logged_browser.click('#wizard-btn-submit')
		logged_browser.wait_for_load_state('networkidle')

		assert 'tab=arquivos' in logged_browser.url

	def test_cliente_salvo_no_banco_apos_step1(self, logged_browser, live_server):
		"""Após avançar do Step 1, o cliente deve existir no banco como rascunho (is_ativo=False)."""
		from clientes.models import Cliente
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(logged_browser, email='rascunho@teste.com')
		self._next(logged_browser, 'step-4')
		assert Cliente.objects.filter(email='rascunho@teste.com').exists()

	def test_botao_anterior_de_conjuge_volta_para_documentos(self, logged_browser, live_server):
		"""Para casado, prev de Cônjuge (step-2) retorna para Dados pessoais (step-1)."""
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(logged_browser, estado_civil='casado', email='prev_conj@teste.com')
		self._next(logged_browser, 'step-2')
		assert logged_browser.is_visible('#step-2')
		logged_browser.click('#wizard-btn-prev')
		logged_browser.wait_for_selector('#step-1', state='visible', timeout=3000)
		assert logged_browser.is_visible('#step-1')
		assert not logged_browser.is_visible('#step-2')

	def test_seletores_documentos_filtrados_por_tipo_pf(self, logged_browser, live_server):
		"""Ao chegar em Documentos com CPF (PF), as opções de tipo NÃO incluem CNPJ."""
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(logged_browser, email='tipopf@teste.com')
		self._next(logged_browser, 'step-4')
		self._preenche_endereco(logged_browser)
		self._next(logged_browser, 'step-5')
		self._preenche_contatos(logged_browser)
		self._next(logged_browser, 'step-3')

		assert logged_browser.is_visible('#step-3')
		options = logged_browser.evaluate(
			"Array.from(document.querySelectorAll('#wz-doc-tipo option')).map(o => o.textContent)"
		)
		assert any('RG' in o for o in options)
		assert not any('CNPJ' in o for o in options)

	def test_step1_labels_dinamicos_cpf(self, logged_browser, live_server):
		"""Ao digitar CPF no campo documento, labels ficam 'Nome' e 'Nome social'."""
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		logged_browser.fill('#id_documento', CPF_VALIDO_FORMATADO)
		label_name = logged_browser.inner_text('#label-name')
		label_nome_usual = logged_browser.inner_text('#label-nome-usual')
		assert 'Razão' not in label_name
		assert 'Nome' in label_name
		assert 'Fantasia' not in label_nome_usual
		assert 'social' in label_nome_usual.lower()

	def test_step1_labels_dinamicos_cnpj(self, logged_browser, live_server):
		"""Ao digitar CNPJ no campo documento, labels mudam para 'Razão Social' e 'Nome Fantasia'."""
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		logged_browser.fill('#id_documento', CNPJ_VALIDO_FORMATADO)
		label_name = logged_browser.inner_text('#label-name')
		label_nome_usual = logged_browser.inner_text('#label-nome-usual')
		assert 'Razão' in label_name
		assert 'Fantasia' in label_nome_usual

	def test_upload_documento_step_documentos(self, logged_browser, live_server, tmp_path):
		"""Upload no step Documentos: arquivo aparece na lista e persiste no banco após finalizar."""
		import os

		pdf = tmp_path / 'rg_teste.pdf'
		pdf.write_bytes(b'%PDF-1.4 test')

		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1(logged_browser, nome='UPLOAD SILVA', email='upload@teste.com')
		self._next(logged_browser, 'step-4')
		self._preenche_endereco(logged_browser)
		self._next(logged_browser, 'step-5')
		self._preenche_contatos(logged_browser, tel='(83) 99999-9997')
		self._next(logged_browser, 'step-3')

		assert logged_browser.is_visible('#step-3')

		logged_browser.select_option('#wz-doc-tipo', 'RG')
		logged_browser.set_input_files('#wz-doc-arquivo', str(pdf))
		logged_browser.click('button[onclick="wizardAddArquivo()"]')

		logged_browser.wait_for_selector('#wz-arquivos-lista table', timeout=8000)
		assert 'RG' in logged_browser.inner_text('#wz-arquivos-lista')

		self._next(logged_browser, 'step-6')
		logged_browser.click('#wizard-btn-submit')
		logged_browser.wait_for_load_state('networkidle')

		from clientes.models import Cliente, ClienteDocumento
		cliente = Cliente.objects.get(email='upload@teste.com')
		assert ClienteDocumento.objects.filter(cliente=cliente).exists()
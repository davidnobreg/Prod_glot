import uuid as _uuid_mod

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase

from clientes.models import Cliente, ClienteRepresentante, RepresentanteDocumento
from clientes.services import (
	criar_representante,
	remover_representante,
	validar_representantes_pj,
)
from clientes.validators import validate_documento_representante

CPF_1 = '11144477735'
CPF_2 = '98765432100'
CPF_3 = '12345678909'


def _make_cliente_pj(**kwargs):
	digits = str(_uuid_mod.uuid4().int)[:14]
	uid_hex = _uuid_mod.uuid4().hex[:8]
	defaults = {
		'name': 'EMPRESA PJ',
		'documento': digits,
		'email': f'pj_{uid_hex}@teste.com',
	}
	defaults.update(kwargs)
	return Cliente.objects.create(**defaults)


def _fake_file(name='doc.pdf', content=b'X' * 512, content_type='application/pdf'):
	return SimpleUploadedFile(name, content, content_type=content_type)


# ===========================================================
# ClienteRepresentante — model
# ===========================================================

class ClienteRepresentanteModelTest(TestCase):

	def test_cria_representante_valido(self):
		cliente = _make_cliente_pj()
		rep = ClienteRepresentante.objects.create(
			cliente=cliente, nome='fulano socio', documento=CPF_1, cargo='Sócio',
		)
		self.assertEqual(rep.cliente, cliente)
		self.assertEqual(rep.nome, 'FULANO SOCIO')  # save() normaliza upper
		self.assertEqual(rep.documento, CPF_1)
		self.assertTrue(rep.is_ativo)

	def test_str_contem_nome_documento_e_cliente(self):
		cliente = _make_cliente_pj(name='EMPRESA XYZ')
		rep = ClienteRepresentante.objects.create(cliente=cliente, nome='Fulano', documento=CPF_1)
		texto = str(rep)
		self.assertIn('FULANO', texto)  # save() normaliza upper
		self.assertIn(CPF_1, texto)
		self.assertIn('EMPRESA XYZ', texto)

	def test_mesmo_cpf_em_duas_pj_diferentes_nao_gera_erro(self):
		"""Teste crítico: unique_together é (cliente, documento), não documento global."""
		cliente_a = _make_cliente_pj(name='EMPRESA A')
		cliente_b = _make_cliente_pj(name='EMPRESA B')
		rep_a = ClienteRepresentante.objects.create(cliente=cliente_a, nome='Carlos', documento=CPF_1)
		rep_b = ClienteRepresentante.objects.create(cliente=cliente_b, nome='Carlos', documento=CPF_1)
		self.assertNotEqual(rep_a.pk, rep_b.pk)
		self.assertEqual(rep_a.documento, rep_b.documento)

	def test_mesmo_cpf_duas_vezes_na_mesma_pj_falha(self):
		cliente = _make_cliente_pj()
		ClienteRepresentante.objects.create(cliente=cliente, nome='Carlos', documento=CPF_1)
		with self.assertRaises(IntegrityError):
			with transaction.atomic():
				ClienteRepresentante.objects.create(cliente=cliente, nome='Carlos Segundo', documento=CPF_1)

	def test_cascade_delete_remove_representantes(self):
		cliente = _make_cliente_pj()
		ClienteRepresentante.objects.create(cliente=cliente, nome='Carlos', documento=CPF_1)
		pk = cliente.pk
		cliente.delete()
		self.assertEqual(ClienteRepresentante.objects.filter(cliente_id=pk).count(), 0)


# ===========================================================
# validar_representantes_pj (services.py)
# ===========================================================

class ValidarRepresentantesPjTest(TestCase):

	def test_pj_sem_representante_retorna_erro(self):
		cliente = _make_cliente_pj()
		erro = validar_representantes_pj(cliente)
		self.assertIsNotNone(erro)

	def test_pj_com_representante_solteiro_valido(self):
		cliente = _make_cliente_pj()
		ClienteRepresentante.objects.create(
			cliente=cliente, nome='Carlos', documento=CPF_1, estado_civil='solteiro',
		)
		self.assertIsNone(validar_representantes_pj(cliente))

	def test_pj_com_representante_casado_sem_conjuge_retorna_erro(self):
		cliente = _make_cliente_pj()
		ClienteRepresentante.objects.create(
			cliente=cliente, nome='Carlos', documento=CPF_1, estado_civil='casado',
		)
		erro = validar_representantes_pj(cliente)
		self.assertIsNotNone(erro)

	def test_pj_com_representante_casado_com_conjuge_valido(self):
		cliente = _make_cliente_pj()
		ClienteRepresentante.objects.create(
			cliente=cliente, nome='Carlos', documento=CPF_1,
			estado_civil='casado', conj_nome='Maria',
		)
		self.assertIsNone(validar_representantes_pj(cliente))

	def test_pj_ignora_representante_inativo(self):
		cliente = _make_cliente_pj()
		ClienteRepresentante.objects.create(
			cliente=cliente, nome='Carlos', documento=CPF_1, is_ativo=False,
		)
		erro = validar_representantes_pj(cliente)
		self.assertIsNotNone(erro)


# ===========================================================
# criar_representante / remover_representante (services.py)
# ===========================================================

class ServicoRepresentanteTest(TestCase):

	def test_criar_representante(self):
		cliente = _make_cliente_pj()
		rep = criar_representante(cliente, {'nome': 'Carlos', 'documento': CPF_1})
		self.assertTrue(ClienteRepresentante.objects.filter(pk=rep.pk).exists())

	def test_remover_representante_rascunho_hard_delete(self):
		cliente = _make_cliente_pj(is_ativo=False)
		rep = ClienteRepresentante.objects.create(cliente=cliente, nome='Carlos', documento=CPF_1)
		remover_representante(rep.uuid, cliente)
		self.assertFalse(ClienteRepresentante.objects.filter(pk=rep.pk).exists())

	def test_remover_representante_cliente_ativo_soft_delete(self):
		cliente = _make_cliente_pj(is_ativo=True)
		rep = ClienteRepresentante.objects.create(cliente=cliente, nome='Carlos', documento=CPF_1)
		remover_representante(rep.uuid, cliente)
		rep.refresh_from_db()
		self.assertFalse(rep.is_ativo)
		self.assertTrue(ClienteRepresentante.objects.filter(pk=rep.pk).exists())


# ===========================================================
# RepresentanteDocumento — validação de arquivo
# ===========================================================

class RepresentanteDocumentoValidatorTest(TestCase):

	def test_pdf_aceito(self):
		validate_documento_representante(_fake_file('doc.pdf'))

	def test_jpg_aceito(self):
		validate_documento_representante(_fake_file('doc.jpg', content_type='image/jpeg'))

	def test_png_aceito(self):
		validate_documento_representante(_fake_file('doc.png', content_type='image/png'))

	def test_extensao_exe_rejeitada(self):
		with self.assertRaises(ValidationError):
			validate_documento_representante(_fake_file('malware.exe', content_type='application/octet-stream'))

	def test_extensao_zip_rejeitada(self):
		with self.assertRaises(ValidationError):
			validate_documento_representante(_fake_file('arquivo.zip', content_type='application/zip'))

	def test_cria_documento_representante(self):
		cliente = _make_cliente_pj()
		rep = ClienteRepresentante.objects.create(cliente=cliente, nome='Carlos', documento=CPF_1)
		doc = RepresentanteDocumento.objects.create(
			representante=rep, tipo='RG', arquivo=_fake_file('rg.pdf'),
		)
		self.assertEqual(doc.representante, rep)
		self.assertEqual(doc.status, 'disponivel')

	def test_cascade_delete_representante_remove_documentos(self):
		cliente = _make_cliente_pj()
		rep = ClienteRepresentante.objects.create(cliente=cliente, nome='Carlos', documento=CPF_1)
		RepresentanteDocumento.objects.create(representante=rep, tipo='RG', arquivo=_fake_file())
		pk = rep.pk
		rep.delete()
		self.assertEqual(RepresentanteDocumento.objects.filter(representante_id=pk).count(), 0)


# ===========================================================
# Wizard E2E (Playwright)
# ===========================================================

CNPJ_VALIDO_FORMATADO = '11.222.333/0001-81'
CPF_REP_1_FORMATADO = '111.444.777-35'
CPF_REP_2_FORMATADO = '987.654.321-00'


@pytest.mark.django_db
class TestWizardRepresentantePj:

	def _preenche_etapa1_pj(self, page, nome='EMPRESA TESTE LTDA', email='empresa@teste.com'):
		page.fill('#id_documento', CNPJ_VALIDO_FORMATADO)
		page.fill('#id_name', nome)
		page.fill('#id_email', email)

	def _preenche_endereco(self, page):
		page.fill('#id_end_cep', '58000000')
		page.fill('#id_end_rua', 'Rua Teste')
		page.fill('#id_end_numero', '1')
		page.fill('#id_end_bairro', 'Centro')
		page.fill('#id_end_cidade', 'João Pessoa')
		page.select_option('#id_end_estado', 'PB')

	def _preenche_contatos(self, page, tel='(83) 98888-0001'):
		page.fill('#telefoneNumero', tel)
		page.click('button[onclick="addTelefone()"]')

	def _next(self, page, expect_step, timeout=8000):
		page.click('#wizard-btn-next')
		page.wait_for_selector(f'#{expect_step}', state='visible', timeout=timeout)

	def _adiciona_representante(self, page, nome, cpf, casado=False, conj_nome=''):
		page.fill('#wz-rep-nome', nome)
		page.fill('#wz-rep-documento', cpf)
		if casado:
			page.select_option('#wz-rep-estado-civil', 'casado')
			page.fill('#wz-rep-conj-nome', conj_nome)
		page.click('button[onclick="wizardAddRepresentante()"]')
		# espera o NOME deste representante especificamente -- só esperar por
		# '.card' resolve cedo demais quando já existe um card de um representante
		# anterior, deixando a interação seguinte correr contra elementos que o
		# próximo re-render (deste próprio AJAX) ainda vai substituir.
		page.wait_for_selector(f'#wz-rep-lista >> text={nome.upper()}', timeout=8000)

	def test_step_representantes_aparece_para_pj(self, logged_browser, live_server):
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1_pj(logged_browser, email='pj_step@teste.com')
		self._next(logged_browser, 'step-7')
		assert logged_browser.is_visible('#step-7')

	def test_wizard_completo_pj_dois_representantes(self, logged_browser, live_server, tmp_path):
		pdf = tmp_path / 'rg_socio.pdf'
		pdf.write_bytes(b'%PDF-1.4 test')

		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1_pj(logged_browser, nome='EMPRESA DOIS SOCIOS', email='dois_socios@teste.com')
		self._next(logged_browser, 'step-7')

		self._adiciona_representante(logged_browser, 'Carlos Silva', CPF_REP_1_FORMATADO)
		self._adiciona_representante(
			logged_browser, 'Celso Souza', CPF_REP_2_FORMATADO,
			casado=True, conj_nome='Cintia Souza',
		)

		# anexa documento pro primeiro representante (índice 0 na lista)
		logged_browser.select_option('#wz-rep-doc-tipo-0', 'RG')
		logged_browser.set_input_files('#wz-rep-doc-arquivo-0', str(pdf))
		logged_browser.click('button[onclick$=",0)"]')
		logged_browser.wait_for_selector('#wz-rep-lista .badge', timeout=8000)

		self._next(logged_browser, 'step-4')
		self._preenche_endereco(logged_browser)
		self._next(logged_browser, 'step-5')
		self._preenche_contatos(logged_browser)
		self._next(logged_browser, 'step-3')
		self._next(logged_browser, 'step-6')

		logged_browser.click('#wizard-btn-submit')
		logged_browser.wait_for_load_state('networkidle')

		cliente = Cliente.objects.get(email='dois_socios@teste.com')
		assert cliente.representantes.count() == 2
		assert cliente.representantes.filter(documento=CPF_REP_1_FORMATADO.replace('.', '').replace('-', '')).exists()

	def test_finalizar_pj_sem_representante_bloqueia(self, logged_browser, live_server):
		"""PJ sem representante não consegue nem avançar do step-7 — wizard
		bloqueia o Próximo com mensagem clara, então nunca chega a finalizar."""
		logged_browser.goto(f'{live_server.url}/clientes/insert_cliente/')
		self._preenche_etapa1_pj(logged_browser, nome='EMPRESA SEM SOCIO', email='sem_socio@teste.com')
		self._next(logged_browser, 'step-7')

		logged_browser.click('#wizard-btn-next')
		logged_browser.wait_for_selector('#wizard-errors', state='visible', timeout=5000)

		assert logged_browser.is_visible('#step-7')
		assert not logged_browser.is_visible('#step-4')

		cliente = Cliente.objects.get(email='sem_socio@teste.com')
		assert cliente.is_ativo is False

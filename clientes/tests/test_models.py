from django.test import TestCase
from django.db import IntegrityError

from clientes.models import Cliente
from clientes.forms import validar_cpf, validar_cnpj, ClienteForm, ClienteConjugeForm


CPF_VALIDO = '52998224725'
CPF_INVALIDO = '11111111111'
CNPJ_VALIDO = '11222333000181'


def _make_cliente(**kwargs):
	defaults = {
		'name': 'FULANO SILVA',
		'documento': CPF_VALIDO,
		'email': 'fulano@teste.com',
	}
	defaults.update(kwargs)
	return Cliente.objects.create(**defaults)


# ===========================================================
# Model
# ===========================================================

class ClienteModelTest(TestCase):

	def test_str_retorna_nome(self):
		c = _make_cliente()
		self.assertEqual(str(c), 'FULANO SILVA')

	def test_save_converte_nome_para_maiusculo(self):
		c = _make_cliente(name='fulano da silva')
		self.assertEqual(c.name, 'FULANO DA SILVA')

	def test_save_converte_email_para_minusculo(self):
		c = _make_cliente(email='FULANO@TESTE.COM')
		self.assertEqual(c.email, 'fulano@teste.com')

	def test_save_remove_pontuacao_do_documento(self):
		c = _make_cliente(documento='529.982.247-25')
		self.assertEqual(c.documento, CPF_VALIDO)

	def test_solteiro_sem_conjuge_salva_ok(self):
		c = _make_cliente(estado_civil='solteiro')
		self.assertIsNone(c.conj_nome)
		self.assertIsNotNone(c.pk)

	def test_documento_duplicado_levanta_integrity_error(self):
		_make_cliente(email='outro@teste.com')
		with self.assertRaises(IntegrityError):
			Cliente.objects.create(name='OUTRO', documento=CPF_VALIDO, email='outro2@teste.com')

	def test_email_duplicado_levanta_integrity_error(self):
		_make_cliente()
		with self.assertRaises(IntegrityError):
			Cliente.objects.create(name='OUTRO', documento='12345678901', email='fulano@teste.com')


# ===========================================================
# Função validar_cpf (forms.py)
# ===========================================================

class ValidarCpfTest(TestCase):

	def test_cpf_valido_retorna_true(self):
		self.assertTrue(validar_cpf(CPF_VALIDO))

	def test_cpf_todos_iguais_retorna_false(self):
		self.assertFalse(validar_cpf(CPF_INVALIDO))

	def test_cpf_digito_verificador_errado_retorna_false(self):
		# último dígito alterado
		cpf_errado = CPF_VALIDO[:-1] + str((int(CPF_VALIDO[-1]) + 1) % 10)
		self.assertFalse(validar_cpf(cpf_errado))


# ===========================================================
# ClienteForm — validação de documento
# ===========================================================

class ClienteFormDocumentoTest(TestCase):

	def _form(self, documento, email='teste@exemplo.com'):
		return ClienteForm(data={
			'name': 'TESTE SILVA',
			'documento': documento,
			'email': email,
		})

	def test_cpf_valido_aceito(self):
		form = self._form(CPF_VALIDO)
		self.assertTrue(form.is_valid(), form.errors)

	def test_cpf_invalido_rejeitado(self):
		form = self._form(CPF_INVALIDO)
		self.assertFalse(form.is_valid())
		self.assertIn('documento', form.errors)

	def test_cpf_formatado_aceito(self):
		form = self._form('529.982.247-25')
		self.assertTrue(form.is_valid(), form.errors)

	def test_cpf_duplicado_rejeitado(self):
		_make_cliente(email='existente@teste.com')
		form = self._form(CPF_VALIDO, email='novo@teste.com')
		self.assertFalse(form.is_valid())
		self.assertIn('documento', form.errors)


# ===========================================================
# ClienteConjugeForm — validação de conj_documento
# ===========================================================

class ClienteConjugeFormTest(TestCase):

	def test_cnpj_valido_aceito_em_conj_documento(self):
		form = ClienteConjugeForm(data={'conj_documento': CNPJ_VALIDO})
		self.assertTrue(form.is_valid(), form.errors)

	def test_conj_documento_vazio_aceito(self):
		form = ClienteConjugeForm(data={'conj_nome': 'Maria Silva'})
		self.assertTrue(form.is_valid(), form.errors)

	def test_conj_documento_cpf_invalido_rejeitado(self):
		# '12345678901' é CPF inválido (dígito verificador errado)
		form = ClienteConjugeForm(data={'conj_documento': '12345678901'})
		self.assertFalse(form.is_valid())
		self.assertIn('conj_documento', form.errors)

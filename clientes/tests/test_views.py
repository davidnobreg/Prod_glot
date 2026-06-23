import json
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from clientes.models import Cliente, ClienteTelefone


User = get_user_model()

CPF_VALIDO = '52998224725'
CPF_VALIDO_2 = '11144477735'


def _make_user(username='testuser'):
	# is_superuser=True → rolepermissions SUPERUSER_SUPERPOWERS bypassa checagem de role
	return User.objects.create_user(username=username, password='pass123',
	                                email=f'{username}@test.com',
	                                is_superuser=True, is_staff=True)


def _make_cliente(**kwargs):
	defaults = {
		'name': 'CLIENTE TESTE',
		'documento': CPF_VALIDO,
		'email': 'cliente@teste.com',
	}
	defaults.update(kwargs)
	return Cliente.objects.create(**defaults)


def _post_criar(**kwargs):
	defaults = {
		'name': 'NOVO CLIENTE',
		'documento': CPF_VALIDO,
		'email': 'novo@teste.com',
		'estado_civil': 'solteiro',
		'end_cep': '58000000',
		'end_rua': 'Rua das Flores',
		'end_numero': '100',
		'end_bairro': 'Centro',
		'end_cidade': 'João Pessoa',
		'end_estado': 'PB',
		'telefones_json': json.dumps(['(83) 99999-9999']),
	}
	defaults.update(kwargs)
	return defaults


# ===========================================================
# criarCliente
# ===========================================================

@override_settings(
	DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
	STORAGES={
		'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
		'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
	},
)
class CriarClienteViewTest(TestCase):

	def setUp(self):
		self.user = _make_user()
		self.client.force_login(self.user)
		self.url = reverse('criar-cliente')
		self._tmpdir = tempfile.mkdtemp()

	def tearDown(self):
		shutil.rmtree(self._tmpdir, ignore_errors=True)

	def test_get_retorna_200_com_form(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('form', response.context)

	def test_anonimo_bloqueado(self):
		# rolepermissions levanta PermissionDenied (403) para usuários sem permissão,
		# incluindo anônimos — ROLEPERMISSIONS_REDIRECT_TO_LOGIN é False por padrão
		self.client.logout()
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 403)

	def test_post_valido_solteiro_cria_cliente_e_redireciona(self):
		response = self.client.post(self.url, _post_criar())
		self.assertRedirects(response, reverse('lista-cliente'))
		self.assertTrue(Cliente.objects.filter(email='novo@teste.com').exists())

	def test_post_casado_sem_conjuge_retorna_200_com_mensagem_erro(self):
		data = _post_criar(estado_civil='casado')
		response = self.client.post(self.url, data)
		self.assertEqual(response.status_code, 200)
		msgs = [str(m) for m in response.wsgi_request._messages]
		self.assertTrue(any('cônjuge' in m.lower() for m in msgs))

	def test_post_cpf_duplicado_retorna_form_com_erro(self):
		_make_cliente(email='existente@teste.com')
		data = _post_criar(email='outro@teste.com')
		response = self.client.post(self.url, data)
		self.assertEqual(response.status_code, 200)
		self.assertIn('form', response.context)
		self.assertIn('documento', response.context['form'].errors)

	def test_post_com_foto_rg_frente_salva_arquivo(self):
		arquivo = SimpleUploadedFile('rg.jpg', b'x' * 1024, 'image/jpeg')
		data = _post_criar(email='arquivo@teste.com')
		with self.settings(MEDIA_ROOT=self._tmpdir):
			response = self.client.post(self.url, {**data, 'foto_rg_frente': arquivo})
		self.assertEqual(response.status_code, 302)
		cliente = Cliente.objects.get(email='arquivo@teste.com')
		self.assertTrue(bool(cliente.foto_rg_frente))


# ===========================================================
# atualizarCliente
# ===========================================================

@override_settings(
	DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
	STORAGES={
		'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
		'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
	},
)
class AtualizarClienteViewTest(TestCase):

	def setUp(self):
		self.user = _make_user()
		self.client.force_login(self.user)
		self.cliente = _make_cliente()
		ClienteTelefone.objects.create(cliente=self.cliente, numero='(83) 99999-9999')
		self.url = reverse('atualizar-cliente', args=[self.cliente.uuid])

	def _post_update(self, **kwargs):
		defaults = {
			'name': self.cliente.name,
			'documento': self.cliente.documento,
			'email': self.cliente.email,
			'estado_civil': 'solteiro',
			'end_cep': '58000000',
			'end_rua': 'Rua Teste',
			'end_numero': '10',
			'end_bairro': 'Centro',
			'end_cidade': 'João Pessoa',
			'end_estado': 'PB',
			'telefones_json': json.dumps(['(83) 99999-9999']),
		}
		defaults.update(kwargs)
		return defaults

	def test_get_retorna_200_com_instancia(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['cliente'].pk, self.cliente.pk)

	def test_anonimo_bloqueado(self):
		# rolepermissions levanta PermissionDenied (403) para usuários sem permissão
		self.client.logout()
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 403)

	def test_post_atualiza_nome(self):
		response = self.client.post(self.url, self._post_update(name='NOME ATUALIZADO'))
		self.assertRedirects(response, reverse('lista-cliente'))
		self.cliente.refresh_from_db()
		self.assertEqual(self.cliente.name, 'NOME ATUALIZADO')

	def test_post_file_vazio_nao_apaga_campo_vazio(self):
		# Se não havia arquivo antes, enviar campo vazio não gera erro
		data = self._post_update()
		data['foto_rg_frente'] = ''
		response = self.client.post(self.url, data)
		self.assertRedirects(response, reverse('lista-cliente'))
		self.cliente.refresh_from_db()
		self.assertFalse(bool(self.cliente.foto_rg_frente))

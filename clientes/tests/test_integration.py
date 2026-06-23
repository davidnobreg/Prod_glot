import json
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from clientes.models import Cliente, ClienteTelefone


User = get_user_model()

CPF_VALIDO = '52998224725'


def _make_user(username='admin'):
	# is_superuser=True → rolepermissions SUPERUSER_SUPERPOWERS bypassa checagem de role
	return User.objects.create_user(username=username, password='pass123',
	                                email=f'{username}@test.com',
	                                is_superuser=True, is_staff=True)


def _make_cliente(**kwargs):
	defaults = {
		'name': 'CLIENTE TESTE',
		'documento': CPF_VALIDO,
		'email': 'cliente@teste.com',
		'end_cep': '58000000',
		'end_rua': 'Rua A',
		'end_numero': '1',
		'end_bairro': 'Centro',
		'end_cidade': 'João Pessoa',
		'end_estado': 'PB',
	}
	defaults.update(kwargs)
	return Cliente.objects.create(**defaults)


def _post_update(cliente, **kwargs):
	defaults = {
		'name': cliente.name,
		'documento': cliente.documento,
		'email': cliente.email,
		'estado_civil': cliente.estado_civil or 'solteiro',
		'end_cep': '58000000',
		'end_rua': 'Rua A',
		'end_numero': '1',
		'end_bairro': 'Centro',
		'end_cidade': 'João Pessoa',
		'end_estado': 'PB',
		'telefones_json': json.dumps(['(83) 88888-8888']),
	}
	defaults.update(kwargs)
	return defaults


# ===========================================================
# Listagem
# ===========================================================

class ClienteListagemIntegracaoTest(TestCase):

	def setUp(self):
		self.user = _make_user()
		self.client.force_login(self.user)

	def test_cliente_recem_criado_aparece_na_listagem(self):
		c = _make_cliente()
		response = self.client.get(reverse('lista-cliente'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, c.name)

	def test_cliente_inativo_nao_aparece_na_listagem(self):
		c = _make_cliente(email='inativo@teste.com', documento='11144477735')
		c.is_ativo = False
		c.save()
		response = self.client.get(reverse('lista-cliente'))
		self.assertNotContains(response, 'inativo@teste.com')


# ===========================================================
# Soft delete
# ===========================================================

class ClienteDeleteIntegracaoTest(TestCase):

	def setUp(self):
		self.user = _make_user()
		self.client.force_login(self.user)
		self.cliente = _make_cliente()

	def test_delete_marca_cliente_inativo(self):
		url = reverse('delete-cliente', args=[self.cliente.uuid])
		self.client.post(url)
		self.cliente.refresh_from_db()
		self.assertFalse(self.cliente.is_ativo)

	def test_delete_cliente_com_telefone_nao_levanta_erro(self):
		ClienteTelefone.objects.create(cliente=self.cliente, numero='(83) 99999-9999')
		url = reverse('delete-cliente', args=[self.cliente.uuid])
		response = self.client.post(url)
		self.assertRedirects(response, reverse('lista-cliente'))
		self.cliente.refresh_from_db()
		self.assertFalse(self.cliente.is_ativo)


# ===========================================================
# Fluxo completo
# ===========================================================

@override_settings(
	DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
	STORAGES={
		'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
		'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
	},
)
class FluxoClienteCasadoTest(TestCase):

	def setUp(self):
		self.user = _make_user()
		self.client.force_login(self.user)
		self._tmpdir = tempfile.mkdtemp()

	def tearDown(self):
		shutil.rmtree(self._tmpdir, ignore_errors=True)

	def test_criar_casado_editar_para_solteiro_apaga_conjuge(self):
		# 1. Criar cliente casado com cônjuge
		cliente = _make_cliente(
			estado_civil='casado',
			conj_nome='MARIA SILVA',
		)
		ClienteTelefone.objects.create(cliente=cliente, numero='(83) 99999-9999')
		self.assertEqual(cliente.conj_nome, 'MARIA SILVA')

		# 2. Editar: trocar estado civil para solteiro
		url = reverse('atualizar-cliente', args=[cliente.uuid])
		data = _post_update(cliente, estado_civil='solteiro')
		response = self.client.post(url, data)
		self.assertRedirects(response, reverse('lista-cliente'))

		# 3. DB: cônjuge apagado pelo view
		cliente.refresh_from_db()
		self.assertEqual(cliente.estado_civil, 'solteiro')
		self.assertIsNone(cliente.conj_nome)

		# 4. Página de edição não carrega dados de cônjuge
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertIsNone(response.context['cliente'].conj_nome)

	def test_upload_documento_persiste_apos_reload(self):
		cliente = _make_cliente()
		ClienteTelefone.objects.create(cliente=cliente, numero='(83) 99999-9999')
		url = reverse('upload-documentos-cliente', args=[cliente.uuid])

		from django.core.files.uploadedfile import SimpleUploadedFile
		arquivo = SimpleUploadedFile('rg_frente.jpg', b'x' * 512, 'image/jpeg')

		with self.settings(MEDIA_ROOT=self._tmpdir):
			response = self.client.post(url, {'foto_rg_frente': arquivo})

		self.assertRedirects(response, reverse('atualizar-cliente', args=[cliente.uuid]))
		cliente.refresh_from_db()
		self.assertTrue(bool(cliente.foto_rg_frente))

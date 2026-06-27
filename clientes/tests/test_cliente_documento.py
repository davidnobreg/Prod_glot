import io
import shutil
import tempfile
import uuid as _uuid_mod

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from clientes.models import Cliente, ClienteDocumento
from clientes.forms import ClienteDocumentoForm, ClienteBaseForm

User = get_user_model()


def _make_user():
	uid = _uuid_mod.uuid4().hex[:8]
	return User.objects.create_user(
		username=f'testdoc_{uid}', password='pass123',
		email=f'testdoc_{uid}@test.com',
		is_superuser=True, is_staff=True,
	)


def _make_cliente_pf(**kwargs):
	# 11 dígitos decimais → PF (modelo strip não-dígitos)
	digits = str(_uuid_mod.uuid4().int)[:11]
	uid_hex = _uuid_mod.uuid4().hex[:8]
	defaults = {
		'name': 'FULANO PF',
		'documento': digits,
		'email': f'pf_{uid_hex}@teste.com',
	}
	defaults.update(kwargs)
	return Cliente.objects.create(**defaults)


def _make_cliente_pj(**kwargs):
	# 14 dígitos decimais → PJ (modelo strip não-dígitos)
	digits = str(_uuid_mod.uuid4().int)[:14]
	uid_hex = _uuid_mod.uuid4().hex[:8]
	defaults = {
		'name': 'EMPRESA PJ',
		'documento': digits,
		'email': f'pj_{uid_hex}@teste.com',
	}
	defaults.update(kwargs)
	return Cliente.objects.create(**defaults)


def _fake_file(name='doc.pdf'):
	return SimpleUploadedFile(name, b'X' * 512, content_type='application/pdf')


# ===========================================================
# Model
# ===========================================================

class ClienteDocumentoModelTest(TestCase):

	def test_cria_documento_pf(self):
		cliente = _make_cliente_pf()
		doc = ClienteDocumento.objects.create(
			cliente=cliente,
			tipo='RG',
			arquivo=_fake_file('rg.pdf'),
		)
		self.assertEqual(doc.cliente, cliente)
		self.assertEqual(doc.tipo, 'RG')
		self.assertIsNotNone(doc.criado_em)

	def test_cria_documento_pj(self):
		cliente = _make_cliente_pj()
		doc = ClienteDocumento.objects.create(
			cliente=cliente,
			tipo='CNPJ',
			arquivo=_fake_file('cnpj.pdf'),
			descricao='CNPJ da empresa',
		)
		self.assertEqual(doc.tipo, 'CNPJ')
		self.assertEqual(doc.descricao, 'CNPJ da empresa')

	def test_str_retorna_tipo_e_cliente(self):
		cliente = _make_cliente_pf()
		doc = ClienteDocumento(cliente=cliente, tipo='CPF')
		self.assertIn('CPF', str(doc))
		self.assertIn('FULANO PF', str(doc))

	def test_related_name_arquivos_cliente(self):
		cliente = _make_cliente_pf()
		ClienteDocumento.objects.create(cliente=cliente, tipo='RG', arquivo=_fake_file())
		ClienteDocumento.objects.create(cliente=cliente, tipo='CPF', arquivo=_fake_file())
		self.assertEqual(cliente.arquivos_cliente.count(), 2)

	def test_cascade_delete(self):
		cliente = _make_cliente_pf()
		ClienteDocumento.objects.create(cliente=cliente, tipo='RG', arquivo=_fake_file())
		pk = cliente.pk
		cliente.delete()
		self.assertEqual(ClienteDocumento.objects.filter(cliente_id=pk).count(), 0)


# ===========================================================
# Form — choices filtradas por tipo_pessoa
# ===========================================================

class ClienteDocumentoFormTest(TestCase):

	def test_choices_pf_contem_rg_e_cpf(self):
		form = ClienteDocumentoForm(tipo_pessoa='PF')
		choice_keys = [k for k, _ in form.fields['tipo'].choices if k]
		self.assertIn('RG', choice_keys)
		self.assertIn('CPF', choice_keys)
		self.assertNotIn('CNPJ', choice_keys)
		self.assertNotIn('CONTRATO_SOCIAL', choice_keys)

	def test_choices_pj_contem_cnpj(self):
		form = ClienteDocumentoForm(tipo_pessoa='PJ')
		choice_keys = [k for k, _ in form.fields['tipo'].choices if k]
		self.assertIn('CNPJ', choice_keys)
		self.assertIn('CONTRATO_SOCIAL', choice_keys)
		self.assertNotIn('RG', choice_keys)
		self.assertNotIn('CPF', choice_keys)


# ===========================================================
# Labels dinâmicas PF / PJ
# ===========================================================

class ClienteLabelsTest(TestCase):

	def test_label_nome_pf(self):
		cliente = _make_cliente_pf()
		form = ClienteBaseForm(instance=cliente)
		self.assertEqual(form.fields['name'].label, 'Nome completo')
		self.assertEqual(form.fields['nome_usual'].label, 'Nome social')

	def test_label_nome_pj(self):
		cliente = _make_cliente_pj()
		form = ClienteBaseForm(instance=cliente)
		self.assertEqual(form.fields['name'].label, 'Razão social')
		self.assertEqual(form.fields['nome_usual'].label, 'Nome fantasia')

	def test_label_default_pf_sem_instancia(self):
		form = ClienteBaseForm()
		self.assertEqual(form.fields['name'].label, 'Nome completo')
		self.assertEqual(form.fields['nome_usual'].label, 'Nome social')


# ===========================================================
# Views — adicionar e excluir
# ===========================================================

@override_settings(
	DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
	STORAGES={
		'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
		'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
	},
)
class AdicionarDocumentoViewTest(TestCase):

	def setUp(self):
		self.user = _make_user()
		self.client.force_login(self.user)
		self.cliente = _make_cliente_pf()
		self.url = reverse('adicionar-documento-cliente', args=[self.cliente.uuid])
		self._tmpdir = tempfile.mkdtemp()

	def tearDown(self):
		shutil.rmtree(self._tmpdir, ignore_errors=True)

	def test_get_redireciona(self):
		response = self.client.get(self.url)
		self.assertRedirects(
			response,
			reverse('atualizar-cliente', args=[self.cliente.uuid]),
			fetch_redirect_response=False,
		)

	def test_post_valido_cria_documento(self):
		with self.settings(MEDIA_ROOT=self._tmpdir):
			response = self.client.post(self.url, {
				'tipo': 'RG',
				'arquivo': _fake_file('rg.pdf'),
			})
		self.assertRedirects(
			response,
			reverse('atualizar-cliente', args=[self.cliente.uuid]),
			fetch_redirect_response=False,
		)
		self.assertEqual(self.cliente.arquivos_cliente.count(), 1)

	def test_post_sem_arquivo_nao_cria(self):
		response = self.client.post(self.url, {'tipo': 'RG'})
		self.assertRedirects(
			response,
			reverse('atualizar-cliente', args=[self.cliente.uuid]),
			fetch_redirect_response=False,
		)
		self.assertEqual(self.cliente.arquivos_cliente.count(), 0)

	def test_anonimo_bloqueado(self):
		self.client.logout()
		response = self.client.post(self.url, {'tipo': 'RG', 'arquivo': _fake_file()})
		self.assertEqual(response.status_code, 403)


@override_settings(
	DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
	STORAGES={
		'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
		'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
	},
)
class ExcluirDocumentoViewTest(TestCase):

	def setUp(self):
		self.user = _make_user()
		self.client.force_login(self.user)
		self.cliente = _make_cliente_pf()
		self._tmpdir = tempfile.mkdtemp()

	def tearDown(self):
		shutil.rmtree(self._tmpdir, ignore_errors=True)

	def test_post_exclui_documento(self):
		with self.settings(MEDIA_ROOT=self._tmpdir):
			doc = ClienteDocumento.objects.create(
				cliente=self.cliente, tipo='RG', arquivo=_fake_file(),
			)
		url = reverse('excluir-documento-cliente', args=[doc.id])
		response = self.client.post(url)
		self.assertRedirects(
			response,
			reverse('atualizar-cliente', args=[self.cliente.uuid]),
			fetch_redirect_response=False,
		)
		self.assertFalse(ClienteDocumento.objects.filter(id=doc.id).exists())

	def test_get_retorna_404(self):
		with self.settings(MEDIA_ROOT=self._tmpdir):
			doc = ClienteDocumento.objects.create(
				cliente=self.cliente, tipo='RG', arquivo=_fake_file(),
			)
		url = reverse('excluir-documento-cliente', args=[doc.id])
		response = self.client.get(url)
		self.assertEqual(response.status_code, 404)

	def test_anonimo_bloqueado(self):
		with self.settings(MEDIA_ROOT=self._tmpdir):
			doc = ClienteDocumento.objects.create(
				cliente=self.cliente, tipo='RG', arquivo=_fake_file(),
			)
		self.client.logout()
		url = reverse('excluir-documento-cliente', args=[doc.id])
		response = self.client.post(url)
		self.assertEqual(response.status_code, 403)


# ===========================================================
# View detalhe — lista documentos no contexto
# ===========================================================

@override_settings(
	DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
	STORAGES={
		'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
		'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
	},
)
class AtualizarClienteDocumentosContextTest(TestCase):

	def setUp(self):
		self.user = _make_user()
		self.client.force_login(self.user)
		self.cliente = _make_cliente_pf()
		self._tmpdir = tempfile.mkdtemp()

	def tearDown(self):
		shutil.rmtree(self._tmpdir, ignore_errors=True)

	def test_documentos_no_contexto(self):
		with self.settings(MEDIA_ROOT=self._tmpdir):
			ClienteDocumento.objects.create(
				cliente=self.cliente, tipo='RG', arquivo=_fake_file(),
			)
		url = reverse('atualizar-cliente', args=[self.cliente.uuid])
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('documentos', response.context)
		self.assertEqual(len(response.context['documentos']), 1)

	def test_form_doc_no_contexto(self):
		url = reverse('atualizar-cliente', args=[self.cliente.uuid])
		response = self.client.get(url)
		self.assertIn('form_doc', response.context)
		self.assertIsInstance(response.context['form_doc'], ClienteDocumentoForm)

	def test_tipo_pessoa_pf_no_contexto(self):
		url = reverse('atualizar-cliente', args=[self.cliente.uuid])
		response = self.client.get(url)
		self.assertEqual(response.context['tipo_pessoa'], 'PF')

	def test_tipo_pessoa_pj_no_contexto(self):
		cliente_pj = _make_cliente_pj()
		url = reverse('atualizar-cliente', args=[cliente_pj.uuid])
		response = self.client.get(url)
		self.assertEqual(response.context['tipo_pessoa'], 'PJ')
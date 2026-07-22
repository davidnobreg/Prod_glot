import os

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from base.models import Endereco
from empreendimentos import services as empreendimento_services
from empreendimentos.models import Empreendimento, RepresentanteLegal, DocumentoEmpreendimento
from empreendimentos.views.cadastro import _WIZARD_SESSION_KEY

User = get_user_model()


def make_user(username='wizard_cancelar_user'):
	return User.objects.create_user(
		username=username, password='pass123', email=f'{username}@test.com',
		is_superuser=True, is_staff=True,
	)


def make_draft(**kwargs):
	defaults = {
		'nome': 'Empreendimento Cancelar', 'telefone': '(83) 99999-9999',
		'tempo_reserva': 30, 'quantidade_parcela': 60, 'is_ativo': False,
	}
	defaults.update(kwargs)
	return Empreendimento.objects.create(**defaults)


@override_settings(
	DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
	STORAGES={
		'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
		'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
	},
)
class WizardCancelarViewTest(TestCase):
	"""Botão Cancelar do wizard de cadastro (ver cadastro.py::wizard_cancelar).
	Antes só redirecionava pra listagem sem limpar nada, abandonando o
	draft is_ativo=False (+ tudo vinculado a ele) permanentemente no banco."""

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.draft = make_draft()
		session = self.client.session
		session[_WIZARD_SESSION_KEY] = str(self.draft.uuid)
		session.save()
		self.url = reverse('empreendimento_wizard_cancelar')

	def test_cancelar_sem_nada_vinculado_apaga_draft_e_redireciona(self):
		response = self.client.post(self.url)
		self.assertRedirects(response, reverse('lista-empreendimento-tabela'))
		self.assertFalse(Empreendimento.objects.filter(pk=self.draft.pk).exists())
		self.assertNotIn(_WIZARD_SESSION_KEY, self.client.session)

	def test_cancelar_apaga_representante_endereco_e_documentos_do_storage(self):
		endereco_rep = Endereco.objects.create(
			cep='58000000', rua='Rua Rep', numero='1', complemento='',
			bairro='Bairro', cidade='João Pessoa', estado='PB',
		)
		representante = RepresentanteLegal.objects.create(
			empreendimento=self.draft, nome='Rep Cancelado', documento='11122233344',
			cargo='Sócio', endereco=endereco_rep,
		)
		doc_rep = empreendimento_services.criar_documento_representante(
			representante, 'rg_representante',
			SimpleUploadedFile('rg.pdf', b'conteudo', content_type='application/pdf'),
		)
		doc_empr = empreendimento_services.criar_documento_empreendimento(
			self.draft, 'matricula_imovel',
			SimpleUploadedFile('mat.pdf', b'conteudo', content_type='application/pdf'),
		)
		arquivo_rep_path = doc_rep.arquivo.path
		arquivo_empr_path = doc_empr.arquivo.path
		representante_pk = representante.pk
		endereco_rep_pk = endereco_rep.pk

		response = self.client.post(self.url)

		self.assertRedirects(response, reverse('lista-empreendimento-tabela'))
		self.assertFalse(Empreendimento.objects.filter(pk=self.draft.pk).exists())
		self.assertFalse(RepresentanteLegal.objects.filter(pk=representante_pk).exists())
		self.assertFalse(Endereco.objects.filter(pk=endereco_rep_pk).exists())
		self.assertFalse(DocumentoEmpreendimento.objects.filter(pk=doc_empr.pk).exists())
		self.assertFalse(os.path.exists(arquivo_rep_path))
		self.assertFalse(os.path.exists(arquivo_empr_path))

	def test_get_rejeitado_com_405(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 405)

	def test_cancelar_sem_draft_na_sessao_nao_quebra(self):
		session = self.client.session
		del session[_WIZARD_SESSION_KEY]
		session.save()
		response = self.client.post(self.url)
		self.assertRedirects(response, reverse('lista-empreendimento-tabela'))

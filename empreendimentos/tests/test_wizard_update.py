from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from base.models import Endereco
from empreendimentos import services as empreendimento_services
from empreendimentos import views_update
from empreendimentos import forms_update
from empreendimentos.models import Empreendimento

User = get_user_model()


def make_user(username='update_wizard_user'):
	return User.objects.create_user(
		username=username, password='pass123', email=f'{username}@test.com',
		is_superuser=True, is_staff=True,
	)


def make_empreendimento(**kwargs):
	defaults = {
		'nome': 'Empreendimento Real', 'telefone': '(83) 99999-9999',
		'tempo_reserva': 30, 'quantidade_parcela': 60, 'cnpj': '11222333000181',
	}
	defaults.update(kwargs)
	return Empreendimento.objects.create(**defaults)


def make_endereco(**kwargs):
	defaults = {
		'cep': '58000000', 'rua': 'Rua Original', 'numero': '10',
		'complemento': '', 'bairro': 'Centro', 'cidade': 'João Pessoa', 'estado': 'PB',
	}
	defaults.update(kwargs)
	return Endereco.objects.create(**defaults)


class SincronizarEnderecoTest(TestCase):

	def test_origem_none_retorna_destino_sem_alterar(self):
		destino = make_endereco(rua='Fica igual')
		resultado = empreendimento_services.sincronizar_endereco(destino, None)
		self.assertEqual(resultado, destino)
		destino.refresh_from_db()
		self.assertEqual(destino.rua, 'Fica igual')

	def test_destino_none_cria_endereco_novo(self):
		origem = make_endereco(rua='Rua Origem', cidade='Campina Grande')
		resultado = empreendimento_services.sincronizar_endereco(None, origem)
		self.assertIsNotNone(resultado.pk)
		self.assertNotEqual(resultado.pk, origem.pk)
		self.assertEqual(resultado.rua, 'Rua Origem')
		self.assertEqual(resultado.cidade, 'Campina Grande')

	def test_destino_existente_e_atualizado_in_place(self):
		origem = make_endereco(rua='Rua Nova', numero='999')
		destino = make_endereco(rua='Rua Velha', numero='1')
		destino_pk = destino.pk
		resultado = empreendimento_services.sincronizar_endereco(destino, origem)
		self.assertEqual(resultado.pk, destino_pk)
		self.assertEqual(resultado.rua, 'Rua Nova')
		self.assertEqual(resultado.numero, '999')


class GetOrCreateDraftTest(TestCase):

	def setUp(self):
		self.factory_endereco_empresa = make_endereco(rua='Rua Empresa')
		self.factory_endereco_empr = make_endereco(rua='Rua Empreendimento')
		self.real = make_empreendimento(
			endereco_empresa=self.factory_endereco_empresa,
			endereco_empreendimento=self.factory_endereco_empr,
		)

	def _fake_request(self):
		from django.test import RequestFactory
		request = RequestFactory().get('/')
		from django.contrib.sessions.backends.db import SessionStore
		request.session = SessionStore()
		return request

	def test_cria_draft_com_campos_copiados(self):
		request = self._fake_request()
		real, draft = views_update._get_or_create_draft(request, self.real.uuid)

		self.assertEqual(real.pk, self.real.pk)
		self.assertFalse(draft.is_ativo)
		self.assertNotEqual(draft.pk, real.pk)
		self.assertEqual(draft.nome, real.nome)
		self.assertIsNone(draft.cnpj)  # cnpj NUNCA vai pro draft (unique=True no banco, ver Global Constraints)
		wizard_session = request.session['wizard_update'][str(real.uuid)]
		self.assertEqual(wizard_session['cnpj_pendente'], real.cnpj)
		self.assertNotEqual(draft.endereco_empresa_id, real.endereco_empresa_id)
		self.assertEqual(draft.endereco_empresa.rua, 'Rua Empresa')
		self.assertNotEqual(draft.endereco_empreendimento_id, real.endereco_empreendimento_id)

	def test_segunda_chamada_reaproveita_mesmo_draft(self):
		request = self._fake_request()
		_, draft1 = views_update._get_or_create_draft(request, self.real.uuid)
		_, draft2 = views_update._get_or_create_draft(request, self.real.uuid)
		self.assertEqual(draft1.pk, draft2.pk)
		self.assertEqual(Empreendimento.objects.filter(is_ativo=False).count(), 1)

	def test_deletar_draft_remove_draft_e_enderecos_mas_nao_o_real(self):
		request = self._fake_request()
		_, draft = views_update._get_or_create_draft(request, self.real.uuid)
		draft_pk = draft.pk
		endereco_empresa_draft_pk = draft.endereco_empresa_id
		endereco_empr_draft_pk = draft.endereco_empreendimento_id

		views_update._deletar_draft(request, self.real.uuid)

		self.assertFalse(Empreendimento.objects.filter(pk=draft_pk).exists())
		self.assertFalse(Endereco.objects.filter(pk=endereco_empresa_draft_pk).exists())
		self.assertFalse(Endereco.objects.filter(pk=endereco_empr_draft_pk).exists())
		self.real.refresh_from_db()
		self.assertEqual(self.real.nome, 'Empreendimento Real')
		self.assertNotIn(str(self.real.uuid), request.session.get('wizard_update', {}))


class WizardUpdateCancelarViewTest(TestCase):

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento()

	def test_cancelar_redireciona_e_nao_altera_real(self):
		session = self.client.session

		class _FakeRequest:
			pass

		fake_request = _FakeRequest()
		fake_request.session = session
		views_update._get_or_create_draft(fake_request, self.real.uuid)
		session.save()

		response = self.client.post(reverse('wizard_update_cancelar', args=[self.real.uuid]))
		self.assertRedirects(response, reverse('lista-empreendimento-tabela'))
		self.assertEqual(Empreendimento.objects.filter(is_ativo=False).count(), 0)
		self.real.refresh_from_db()
		self.assertTrue(self.real.is_ativo)

	def test_get_rejeitado_com_405(self):
		response = self.client.get(reverse('wizard_update_cancelar', args=[self.real.uuid]))
		self.assertEqual(response.status_code, 405)


class EmpreendimentoUpdateStep1FormTest(TestCase):

	def setUp(self):
		self.real = make_empreendimento(nome='Nome Original')
		self.draft = make_empreendimento(nome='Nome Original', is_ativo=False, cnpj=None)

	def test_nome_igual_ao_do_proprio_real_nao_gera_erro(self):
		form = forms_update.EmpreendimentoUpdateStep1Form(
			{'nome': 'Nome Original', 'telefone': '(83) 98888-8888', 'observacao': ''},
			instance=self.draft, real_pk=self.real.pk,
		)
		self.assertTrue(form.is_valid(), form.errors)

	def test_nome_de_outro_empreendimento_ativo_gera_erro(self):
		make_empreendimento(nome='Outro Ativo', cnpj='11222333000280')
		form = forms_update.EmpreendimentoUpdateStep1Form(
			{'nome': 'Outro Ativo', 'telefone': '(83) 98888-8888', 'observacao': ''},
			instance=self.draft, real_pk=self.real.pk,
		)
		self.assertFalse(form.is_valid())
		self.assertIn('nome', form.errors)


class WizardUpdateStep1Test(TestCase):

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento(nome='Nome Antigo')
		self.url = reverse('empreendimento_update_step1', args=[self.real.uuid])

	def test_get_pre_preenche_com_dados_do_real(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Nome Antigo')

	def test_post_valido_atualiza_draft_nao_real(self):
		response = self.client.post(self.url, {
			'nome': 'Nome Novo', 'telefone': '(83) 97777-7777', 'observacao': 'obs nova',
		})
		self.assertRedirects(response, reverse('empreendimento_update_step2', args=[self.real.uuid]))

		self.real.refresh_from_db()
		self.assertEqual(self.real.nome, 'Nome Antigo')

		draft = Empreendimento.objects.get(is_ativo=False)
		self.assertEqual(draft.nome, 'Nome Novo')
		self.assertEqual(draft.observacao, 'obs nova')

	def test_anonimo_bloqueado(self):
		self.client.logout()
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 403)


class EmpresaUpdateStep2FormTest(TestCase):

	def setUp(self):
		self.real = make_empreendimento(cnpj='11222333000181')
		# draft nunca guarda cnpj de verdade (unique=True no banco colide com
		# o do real) — ver Global Constraints e Task 2/5/11. Testando aqui só
		# a validação da form, que é independente de onde o valor é gravado.
		self.draft = make_empreendimento(nome='Draft', is_ativo=False, cnpj=None)

	def test_cnpj_igual_ao_do_proprio_real_nao_gera_erro(self):
		form = forms_update.EmpresaUpdateStep2Form(
			{'cnpj': '11222333000181', 'razaoSocial': 'Razao', 'codBanco': '', 'banco': '', 'agencia': '1', 'conta': '1'},
			instance=self.draft, real_pk=self.real.pk,
		)
		self.assertTrue(form.is_valid(), form.errors)

	def test_cnpj_de_outro_empreendimento_ativo_gera_erro(self):
		make_empreendimento(nome='Outro', cnpj='44555666000122')
		form = forms_update.EmpresaUpdateStep2Form(
			{'cnpj': '44555666000122', 'razaoSocial': 'Razao', 'codBanco': '', 'banco': '', 'agencia': '1', 'conta': '1'},
			instance=self.draft, real_pk=self.real.pk,
		)
		self.assertFalse(form.is_valid())
		self.assertIn('cnpj', form.errors)

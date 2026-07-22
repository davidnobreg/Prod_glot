from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from empreendimentos.models import Empreendimento, RepresentanteLegal
from empreendimentos.views.cadastro import _WIZARD_SESSION_KEY

User = get_user_model()


def make_user(username='wizard_rep_user'):
	return User.objects.create_user(
		username=username, password='pass123', email=f'{username}@test.com',
		is_superuser=True, is_staff=True,
	)


def make_draft(**kwargs):
	defaults = {
		'nome': 'Empreendimento Representantes', 'telefone': '(83) 99999-9999',
		'tempo_reserva': 30, 'quantidade_parcela': 60, 'is_ativo': False,
	}
	defaults.update(kwargs)
	return Empreendimento.objects.create(**defaults)


def management_form(total_forms, initial_forms=0):
	return {
		'representante-TOTAL_FORMS': str(total_forms),
		'representante-INITIAL_FORMS': str(initial_forms),
		'representante-MIN_NUM_FORMS': '0',
		'representante-MAX_NUM_FORMS': '1000',
	}


class WizardStep3RepresentantesTest(TestCase):
	"""Step3 do wizard de cadastro — criação de representantes legais.

	Cobre 2 correções: (1) submeter o formset em branco (min_num=1, todos
	os campos opcionais) não deve criar um RepresentanteLegal vazio; (2)
	dois representantes sem CPF no mesmo empreendimento não devem colidir
	no unique_together (documento='' conta como valor igual pro Postgres).
	"""

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.draft = make_draft()
		session = self.client.session
		session[_WIZARD_SESSION_KEY] = str(self.draft.uuid)
		session.save()
		self.url = reverse('empreendimento_wizard_step3')

	def test_post_formset_em_branco_nao_cria_representante_vazio(self):
		payload = {**management_form(total_forms=1)}
		response = self.client.post(self.url, payload)

		self.assertEqual(response.status_code, 302)
		self.assertFalse(RepresentanteLegal.objects.filter(empreendimento=self.draft).exists())

	def test_post_com_nome_preenchido_e_documento_em_branco_cria_representante(self):
		payload = {
			**management_form(total_forms=1),
			'representante-0-nome': 'Fulano de Tal',
			'representante-0-documento': '',
			'representante-0-cargo': 'Sócio',
			'representante-0-endereco-cep': '',
		}
		self.client.post(self.url, payload)

		self.assertEqual(RepresentanteLegal.objects.filter(empreendimento=self.draft).count(), 1)
		representante = RepresentanteLegal.objects.get(empreendimento=self.draft)
		self.assertEqual(representante.documento, '')

	def test_post_dois_representantes_sem_cpf_nao_colide_unique_together(self):
		"""Antes da constraint condicional, o segundo `full_clean()` levantava
		ValidationError (documento='' contando como duplicata) e o request
		quebrava com 500 — não relacionado a formulário mal preenchido."""
		payload = {
			**management_form(total_forms=2),
			'representante-0-nome': 'Primeiro Socio',
			'representante-0-documento': '',
			'representante-0-cargo': 'Sócio',
			'representante-1-nome': 'Segundo Socio',
			'representante-1-documento': '',
			'representante-1-cargo': 'Sócio',
		}
		response = self.client.post(self.url, payload)

		# Fica em 200 (volta pro step3 pra liberar upload de documentos dos
		# representantes recém-criados) — comportamento normal quando
		# `algum_novo=True`, não indica erro de validação.
		self.assertEqual(response.status_code, 200)
		self.assertEqual(RepresentanteLegal.objects.filter(empreendimento=self.draft).count(), 2)

	def test_post_dois_representantes_mesmo_cpf_retorna_erro_sem_500_e_preserva_dados(self):
		"""CPF real duplicado ainda viola a constraint condicional (ela só
		libera documento=''). full_clean() levanta ValidationError — a view
		precisa capturar isso, mostrar erro no formulário, não criar nada e
		nunca vazar como HTTP 500."""
		payload = {
			**management_form(total_forms=2),
			'representante-0-nome': 'Primeiro Socio',
			'representante-0-documento': '11144477735',
			'representante-0-cargo': 'Sócio',
			'representante-1-nome': 'Segundo Socio',
			'representante-1-documento': '11144477735',
			'representante-1-cargo': 'Sócio',
		}
		response = self.client.post(self.url, payload)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(RepresentanteLegal.objects.filter(empreendimento=self.draft).count(), 0)
		# dados preenchidos precisam voltar pro form (não perder o que o usuário digitou)
		content = response.content.decode('utf-8')
		self.assertIn('Primeiro Socio', content)
		self.assertIn('Segundo Socio', content)

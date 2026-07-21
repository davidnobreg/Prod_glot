from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cobranca.models import ConfiguracaoGateway
from empreendimentos.models import Empreendimento
from empreendimentos.views.cadastro import _WIZARD_SESSION_KEY

User = get_user_model()


def make_user(username='wizard_gateway_user'):
	return User.objects.create_user(
		username=username, password='pass123', email=f'{username}@test.com',
		is_superuser=True, is_staff=True,
	)


def make_empreendimento(**kwargs):
	defaults = {
		'nome': 'Empreendimento Gateway', 'telefone': '(83) 99999-9999',
		'tempo_reserva': 30, 'quantidade_parcela': 60,
	}
	defaults.update(kwargs)
	return Empreendimento.objects.create(**defaults)


class WizardCadastroStep4GatewayTest(TestCase):
	"""Step4 do wizard de cadastro — seção de configuração de gateway."""

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.draft = make_empreendimento(is_ativo=False, cnpj='11222333000181')
		session = self.client.session
		session[_WIZARD_SESSION_KEY] = str(self.draft.uuid)
		session.save()
		self.url = reverse('empreendimento_wizard_step4')

	def test_post_com_dados_de_gateway_cria_configuracao(self):
		self.client.post(self.url, {
			'tempo_reserva': '30', 'quantidade_parcela': '60',
			'desconto': '0', 'tipo_correcao': 'IGPM',
			'gateway-gateway': 'sicoob',
			'gateway-client_id': 'abc123',
			'gateway-client_secret': 'segredo',
			'gateway-convenio': '9999',
			'gateway-sandbox': 'on',
		})
		config = ConfiguracaoGateway.objects.get(empreendimento=self.draft)
		self.assertEqual(config.gateway, 'sicoob')
		self.assertEqual(config.client_id, 'abc123')
		self.assertEqual(config.client_secret, 'segredo')
		self.assertTrue(config.sandbox)

	def test_post_sem_dados_de_gateway_nao_cria_configuracao(self):
		response = self.client.post(self.url, {
			'tempo_reserva': '30', 'quantidade_parcela': '60',
			'desconto': '0', 'tipo_correcao': 'IGPM',
		})
		self.assertEqual(response.status_code, 302)
		self.assertFalse(ConfiguracaoGateway.objects.filter(empreendimento=self.draft).exists())


class WizardUpdateStep4GatewayTest(TestCase):
	"""Step4 do wizard de update — seção de configuração de gateway."""

	def setUp(self):
		self.user = make_user()
		self.client.force_login(self.user)
		self.real = make_empreendimento(cnpj='11222333000181')
		self.url = reverse('empreendimento_update_step4', args=[self.real.uuid])

	def test_post_com_novo_gateway_atualiza_configuracao_existente(self):
		ConfiguracaoGateway.objects.create(
			empreendimento=self.real, gateway='banco_brasil', client_id='antigo', sandbox=True,
		)
		self.client.post(self.url, {
			'tempo_reserva': '30', 'quantidade_parcela': '60',
			'desconto': '0', 'tipo_correcao': 'IGPM',
			'gateway-gateway': 'sicredi',
			'gateway-client_id': 'novo123',
		})

		draft = Empreendimento.objects.get(is_ativo=False)
		draft_config = ConfiguracaoGateway.objects.get(empreendimento=draft)
		self.assertEqual(draft_config.gateway, 'sicredi')
		self.assertEqual(draft_config.client_id, 'novo123')

		self.real.refresh_from_db()
		self.assertEqual(self.real.configuracao_gateway.gateway, 'banco_brasil')

	def test_post_com_campos_em_branco_mantem_valores_anteriores(self):
		step1_url = reverse('empreendimento_update_step1', args=[self.real.uuid])
		self.client.post(step1_url, {
			'nome': self.real.nome, 'telefone': self.real.telefone, 'observacao': '',
			'empreendimento-cep': '58000000', 'empreendimento-rua': 'Rua X', 'empreendimento-numero': '1',
			'empreendimento-complemento': '', 'empreendimento-bairro': 'Centro',
			'empreendimento-cidade': 'João Pessoa', 'empreendimento-estado': 'PB',
		})

		self.client.post(self.url, {
			'tempo_reserva': '30', 'quantidade_parcela': '60',
			'desconto': '0', 'tipo_correcao': 'IGPM',
			'gateway-gateway': 'sicoob',
			'gateway-client_id': 'client-inicial',
			'gateway-client_secret': 'segredo-inicial',
		})

		self.client.post(self.url, {
			'tempo_reserva': '30', 'quantidade_parcela': '60',
			'desconto': '0', 'tipo_correcao': 'IGPM',
			'gateway-gateway': '',
			'gateway-client_id': '',
			'gateway-client_secret': '',
		})

		draft = Empreendimento.objects.get(is_ativo=False)
		draft_config = ConfiguracaoGateway.objects.get(empreendimento=draft)
		self.assertEqual(draft_config.gateway, 'sicoob')
		self.assertEqual(draft_config.client_id, 'client-inicial')
		self.assertEqual(draft_config.client_secret, 'segredo-inicial')

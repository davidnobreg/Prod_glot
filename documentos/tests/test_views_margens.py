import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from documentos.models import ConfiguracaoDocumento
from empreendimentos.models import Empreendimento

User = get_user_model()


def _make_empreendimento():
	return Empreendimento.objects.create(
		nome='Residencial Teste', telefone='(83) 99999-9999',
		tempo_reserva=30, quantidade_parcela=60,
	)


class EmpreendimentoMargensSalvarTest(TestCase):

	def setUp(self):
		self.user = User.objects.create_user(
			username='admin_margens_test', password='pass123', tipo_usuario='ADMINISTRADOR',
		)
		self.client.force_login(self.user)
		self.empr = _make_empreendimento()

	def test_salva_margens_validas_cria_configuracao(self):
		url = reverse('documentos:empreendimento-margens-salvar', args=[self.empr.pk])
		resp = self.client.post(
			url,
			data=json.dumps({'margem_sup': 30, 'margem_dir': 25, 'margem_inf': 25, 'margem_esq': 35}),
			content_type='application/json',
		)
		self.assertEqual(resp.status_code, 200)
		self.assertTrue(resp.json()['ok'])
		cfg = ConfiguracaoDocumento.objects.get(empreendimento=self.empr)
		self.assertEqual(cfg.margem_sup, 30)
		self.assertEqual(cfg.margem_dir, 25)
		self.assertEqual(cfg.margem_inf, 25)
		self.assertEqual(cfg.margem_esq, 35)

	def test_atualiza_configuracao_existente(self):
		ConfiguracaoDocumento.objects.create(empreendimento=self.empr)
		url = reverse('documentos:empreendimento-margens-salvar', args=[self.empr.pk])
		self.client.post(
			url,
			data=json.dumps({'margem_sup': 40, 'margem_dir': 20, 'margem_inf': 20, 'margem_esq': 30}),
			content_type='application/json',
		)
		self.assertEqual(ConfiguracaoDocumento.objects.filter(empreendimento=self.empr).count(), 1)
		cfg = ConfiguracaoDocumento.objects.get(empreendimento=self.empr)
		self.assertEqual(cfg.margem_sup, 40)

	def test_rejeita_margem_fora_do_intervalo(self):
		url = reverse('documentos:empreendimento-margens-salvar', args=[self.empr.pk])
		resp = self.client.post(
			url,
			data=json.dumps({'margem_sup': 200, 'margem_dir': 25, 'margem_inf': 25, 'margem_esq': 35}),
			content_type='application/json',
		)
		self.assertEqual(resp.status_code, 400)
		self.assertFalse(resp.json()['ok'])
		self.assertFalse(ConfiguracaoDocumento.objects.filter(empreendimento=self.empr).exists())

	def test_get_nao_permitido(self):
		url = reverse('documentos:empreendimento-margens-salvar', args=[self.empr.pk])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 405)
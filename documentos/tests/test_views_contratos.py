"""Regressão: proposta_rascunho não pode estourar 404 puro
quando venda inexistente ou sem modelo de proposta configurado."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from empreendimentos.models import Empreendimento, Quadra, Lote
from vendas.models import RegisterVenda

User = get_user_model()


def _make_empreendimento():
	return Empreendimento.objects.create(
		nome='Residencial Teste',
		telefone='(83) 99999-9999',
		tempo_reserva=30,
		quantidade_parcela=60,
	)


def _make_quadra(empr):
	return Quadra.objects.create(namequadra='Quadra A', empr=empr)


def _make_lote(quadra):
	return Lote.objects.create(
		quadra=quadra,
		lote='Lote 01',
		area='200',
		situacao='ANALISE',
		valor_metro_quadrado='1500.00',
		telefone='(83) 99999-9999',
		telefone_user='(83) 99999-9999',
		user='teste',
		cliente_reserva='0',
	)


class PropostaRascunhoFallbackTest(TestCase):

	def setUp(self):
		self.user = User.objects.create_user(
			username='corretor_test',
			password='pass123',
			tipo_usuario='CORRETOR',
		)
		self.client.force_login(self.user)
		self.empr = _make_empreendimento()
		self.quadra = _make_quadra(self.empr)
		self.lote = _make_lote(self.quadra)

	def test_uuid_inexistente_renderiza_aguardando_analise(self):
		import uuid
		url = reverse('documentos:proposta-rascunho', args=[uuid.uuid4()])
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Aguardando análise')
		self.assertContains(response, reverse('lista-empreendimento'))

	def test_venda_sem_modelo_proposta_renderiza_aguardando_analise(self):
		venda = RegisterVenda.objects.create(lote=self.lote, tipo_venda='ANALISE')
		url = reverse('documentos:proposta-rascunho', args=[venda.uuid])
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Aguardando análise')
		self.assertContains(response, reverse('listar-quadras', args=[self.empr.uuid]))
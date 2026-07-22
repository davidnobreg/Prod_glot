from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from clientes.models import Cliente
from empreendimentos.models import Empreendimento, Lote, Quadra
from vendas.models import RegisterVenda

from cobranca.models import Carne, Parcela
from cobranca.services import gerar_carne, gerar_entrada


class CobrancaViewsTestCase(TestCase):

	def setUp(self):
		self.admin = User.objects.create_user(
			username='admin_test',
			password='senha123',
			tipo_usuario='ADMINISTRADOR',
			is_superuser=True,
		)
		self.corretor = User.objects.create_user(
			username='corretor_test',
			password='senha123',
			tipo_usuario='CORRETOR',
		)
		self.empreendimento = Empreendimento.objects.create(
			nome='Empr Teste',
			telefone='(83) 99999-9999',
			tempo_reserva=7,
			quantidade_parcela=60,
			cnpj='00000000000100',
		)
		self.quadra = Quadra.objects.create(namequadra='Q1', empr=self.empreendimento)
		self.lote = Lote.objects.create(
			lote='L1',
			area='200',
			situacao='DISPONIVEL',
			quadra=self.quadra,
			valor_metro_quadrado='100',
			telefone='(83) 99999-9999',
			telefone_user='(83) 99999-9999',
		)
		self.cliente = Cliente.objects.create(
			name='Cliente PF Teste',
			documento='00000000000',
			email='pf@test.com',
			estado_civil='solteiro',
		)
		self.venda = RegisterVenda.objects.create(
			lote=self.lote,
			cliente=self.cliente,
			corretor=self.admin,
			tipo_venda='RESERVADO',
			is_ativo=True,
		)

	# ─── ListaCarnesVendaView ───────────────────────────────────────

	def test_lista_carnes_venda_200_admin(self):
		self.client.force_login(self.admin)
		url = reverse('lista_carnes_venda', kwargs={'venda_uuid': self.venda.uuid})
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)

	def test_lista_carnes_venda_redireciona_nao_admin(self):
		self.client.force_login(self.corretor)
		url = reverse('lista_carnes_venda', kwargs={'venda_uuid': self.venda.uuid})
		response = self.client.get(url)
		self.assertEqual(response.status_code, 302)

	# ─── GerarCarneView ─────────────────────────────────────────────

	def test_gerar_carne_get_200(self):
		self.client.force_login(self.admin)
		url = reverse('gerar_carne', kwargs={'venda_uuid': self.venda.uuid})
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)

	def test_gerar_carne_post_cria_e_redireciona(self):
		self.client.force_login(self.admin)
		url = reverse('gerar_carne', kwargs={'venda_uuid': self.venda.uuid})
		response = self.client.post(url, {
			'numero_parcelas': '3',
			'valor_parcela': '500',
			'data_primeira_parcela': '2026-01-10',
			'ano_referencia': '2026',
			'modalidade': 'BOLETO',
		})
		self.assertEqual(Carne.objects.count(), 1)
		self.assertEqual(Parcela.objects.filter(carne=Carne.objects.first()).count(), 3)
		self.assertEqual(response.status_code, 302)

	def test_gerar_carne_post_mais_de_12_parcelas_nao_cria(self):
		self.client.force_login(self.admin)
		url = reverse('gerar_carne', kwargs={'venda_uuid': self.venda.uuid})
		response = self.client.post(url, {
			'numero_parcelas': '13',
			'valor_parcela': '500',
			'data_primeira_parcela': '2026-01-10',
			'ano_referencia': '2026',
			'modalidade': 'BOLETO',
		})
		self.assertEqual(Carne.objects.count(), 0)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Carnê não pode ter mais de 12 parcelas')

	# ─── GerarEntradaView ───────────────────────────────────────────

	def test_gerar_entrada_post_cria_e_redireciona(self):
		self.client.force_login(self.admin)
		url = reverse('gerar_entrada', kwargs={'venda_uuid': self.venda.uuid})
		response = self.client.post(url, {
			'valor': '1000',
			'data_vencimento': '2026-01-05',
			'modalidade': 'BOLETO',
		})
		self.assertEqual(Parcela.objects.filter(tipo='ENTRADA').count(), 1)
		self.assertEqual(response.status_code, 302)

	def test_gerar_entrada_get_prefill_valor_entrada_da_venda(self):
		self.venda.valor_entrada = Decimal('2500.00')
		self.venda.save(update_fields=['valor_entrada'])
		self.client.force_login(self.admin)
		url = reverse('gerar_entrada', kwargs={'venda_uuid': self.venda.uuid})
		response = self.client.get(url)
		self.assertEqual(response.context['initial']['valor'], Decimal('2500.00'))
		self.assertEqual(response.context['initial']['quantidade_parcelas'], 1)

	def test_gerar_entrada_post_quantidade_3_divide_valor_e_gera_datas_mensais(self):
		self.client.force_login(self.admin)
		url = reverse('gerar_entrada', kwargs={'venda_uuid': self.venda.uuid})
		response = self.client.post(url, {
			'valor': '3000',
			'data_vencimento': '2026-01-05',
			'modalidade': 'BOLETO',
			'quantidade_parcelas': '3',
		})
		self.assertEqual(response.status_code, 302)
		entradas = Parcela.objects.filter(tipo='ENTRADA').order_by('numero_parcela')
		self.assertEqual(entradas.count(), 3)
		self.assertTrue(all(p.carne is None for p in entradas))
		self.assertEqual(list(entradas.values_list('valor', flat=True)), [Decimal('1000.00')] * 3)
		self.assertEqual(
			list(entradas.values_list('data_vencimento', flat=True)),
			[date(2026, 1, 5), date(2026, 2, 5), date(2026, 3, 5)],
		)

	def test_gerar_entrada_post_quantidade_12_nao_gera_erro_unique_together(self):
		self.client.force_login(self.admin)
		url = reverse('gerar_entrada', kwargs={'venda_uuid': self.venda.uuid})
		response = self.client.post(url, {
			'valor': '1200',
			'data_vencimento': '2026-01-05',
			'modalidade': 'BOLETO',
			'quantidade_parcelas': '12',
		})
		self.assertEqual(response.status_code, 302)
		self.assertEqual(Parcela.objects.filter(tipo='ENTRADA').count(), 12)

	def test_gerar_entrada_post_quantidade_13_nao_cria_e_retorna_erro(self):
		self.client.force_login(self.admin)
		url = reverse('gerar_entrada', kwargs={'venda_uuid': self.venda.uuid})
		response = self.client.post(url, {
			'valor': '1300',
			'data_vencimento': '2026-01-05',
			'modalidade': 'BOLETO',
			'quantidade_parcelas': '13',
		})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Parcela.objects.filter(tipo='ENTRADA').count(), 0)

	# ─── BaixaManualParcelaView ─────────────────────────────────────

	def test_baixa_manual_post_baixa_e_redireciona(self):
		parcela = gerar_entrada(
			venda=self.venda,
			valor=1000,
			data_vencimento=date(2026, 1, 5),
			usuario=self.admin,
		)
		self.client.force_login(self.admin)
		url = reverse('baixa_manual_parcela', kwargs={'parcela_uuid': parcela.uuid})
		response = self.client.post(url, {
			'valor_pago': '1000',
			'data_pagamento': '2026-01-06',
		})
		parcela.refresh_from_db()
		self.assertEqual(parcela.status, 'PAGA')
		self.assertEqual(response.status_code, 302)

	def test_baixa_manual_post_parcela_paga_exibe_erro(self):
		parcela = gerar_entrada(
			venda=self.venda,
			valor=1000,
			data_vencimento=date(2026, 1, 5),
			usuario=self.admin,
		)
		parcela.status = 'PAGA'
		parcela.save(update_fields=['status'])

		self.client.force_login(self.admin)
		url = reverse('baixa_manual_parcela', kwargs={'parcela_uuid': parcela.uuid})
		response = self.client.post(url, {
			'valor_pago': '1000',
			'data_pagamento': '2026-01-06',
		})
		parcela.refresh_from_db()
		self.assertEqual(parcela.status, 'PAGA')
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Parcela não pode ser baixada com status atual')

	# ─── DetalheCarneView / DetalheParcelaView ─────────────────────

	def test_detalhe_carne_200_admin(self):
		carne = gerar_carne(
			venda=self.venda,
			numero_parcelas=1,
			valor_parcela=500,
			data_primeira_parcela=date(2026, 1, 10),
			ano_referencia=2026,
			usuario=self.admin,
		)
		self.client.force_login(self.admin)
		url = reverse('detalhe_carne', kwargs={'carne_uuid': carne.uuid})
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)

	def test_detalhe_parcela_200_admin(self):
		parcela = gerar_entrada(
			venda=self.venda,
			valor=1000,
			data_vencimento=date(2026, 1, 5),
			usuario=self.admin,
		)
		self.client.force_login(self.admin)
		url = reverse('detalhe_parcela', kwargs={'parcela_uuid': parcela.uuid})
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)

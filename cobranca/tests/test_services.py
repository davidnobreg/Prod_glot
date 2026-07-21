from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from clientes.models import Cliente
from empreendimentos.models import Empreendimento, Lote, Quadra
from vendas.models import RegisterVenda

from cobranca.models import Carne, Parcela
from cobranca.services import gerar_carne, gerar_entrada, registrar_baixa_manual


class CobrancaServicesTestCase(TestCase):

	def setUp(self):
		self.usuario = User.objects.create_user(
			username='admin_test',
			password='senha123',
			tipo_usuario='ADMINISTRADOR',
			is_superuser=True,
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
			corretor=self.usuario,
			tipo_venda='RESERVADO',
			is_ativo=True,
		)

	# ─── gerar_carne ────────────────────────────────────────────────

	def test_gerar_carne_12_parcelas(self):
		carne = gerar_carne(
			venda=self.venda,
			numero_parcelas=12,
			valor_parcela=500,
			data_primeira_parcela=date(2026, 1, 10),
			ano_referencia=2026,
			usuario=self.usuario,
		)
		self.assertEqual(Parcela.objects.filter(carne=carne).count(), 12)

	def test_gerar_carne_datas_vencimento_mensais(self):
		carne = gerar_carne(
			venda=self.venda,
			numero_parcelas=3,
			valor_parcela=500,
			data_primeira_parcela=date(2026, 1, 10),
			ano_referencia=2026,
			usuario=self.usuario,
		)
		parcelas = Parcela.objects.filter(carne=carne).order_by('numero_parcela')
		self.assertEqual(parcelas[0].data_vencimento, date(2026, 1, 10))
		self.assertEqual(parcelas[1].data_vencimento, date(2026, 2, 10))
		self.assertEqual(parcelas[2].data_vencimento, date(2026, 3, 10))

	def test_gerar_carne_mais_de_12_parcelas_levanta_valueerror(self):
		with self.assertRaisesMessage(ValueError, 'Carnê não pode ter mais de 12 parcelas'):
			gerar_carne(
				venda=self.venda,
				numero_parcelas=13,
				valor_parcela=500,
				data_primeira_parcela=date(2026, 1, 10),
				ano_referencia=2026,
				usuario=self.usuario,
			)

	def test_gerar_carne_numero_sequencial(self):
		gerar_carne(
			venda=self.venda,
			numero_parcelas=1,
			valor_parcela=500,
			data_primeira_parcela=date(2026, 1, 10),
			ano_referencia=2026,
			usuario=self.usuario,
		)
		segundo = gerar_carne(
			venda=self.venda,
			numero_parcelas=1,
			valor_parcela=500,
			data_primeira_parcela=date(2026, 2, 10),
			ano_referencia=2026,
			usuario=self.usuario,
		)
		self.assertEqual(segundo.numero_carne, 2)

	def test_gerar_carne_unique_together_impede_duplicata(self):
		carne = gerar_carne(
			venda=self.venda,
			numero_parcelas=1,
			valor_parcela=500,
			data_primeira_parcela=date(2026, 1, 10),
			ano_referencia=2026,
			usuario=self.usuario,
		)
		with self.assertRaises(IntegrityError):
			with transaction.atomic():
				Parcela.objects.create(
					carne=carne,
					venda=self.venda,
					tipo='PARCELA',
					modalidade='BOLETO',
					numero_parcela=1,
					valor=500,
					data_vencimento=date(2026, 1, 10),
					status='PENDENTE',
				)

	# ─── gerar_entrada ──────────────────────────────────────────────

	def test_gerar_entrada_cria_parcela_tipo_entrada_sem_carne(self):
		parcela = gerar_entrada(
			venda=self.venda,
			valor=1000,
			data_vencimento=date(2026, 1, 5),
			usuario=self.usuario,
		)
		self.assertEqual(parcela.tipo, 'ENTRADA')
		self.assertIsNone(parcela.carne)

	def test_gerar_entrada_numero_parcela_zero(self):
		parcela = gerar_entrada(
			venda=self.venda,
			valor=1000,
			data_vencimento=date(2026, 1, 5),
			usuario=self.usuario,
		)
		self.assertEqual(parcela.numero_parcela, 0)

	# ─── registrar_baixa_manual ─────────────────────────────────────

	def test_registrar_baixa_manual_parcela_pendente(self):
		parcela = gerar_entrada(
			venda=self.venda,
			valor=1000,
			data_vencimento=date(2026, 1, 5),
			usuario=self.usuario,
		)
		atualizada = registrar_baixa_manual(
			parcela=parcela,
			valor_pago=1000,
			data_pagamento=date(2026, 1, 6),
			usuario=self.usuario,
		)
		self.assertEqual(atualizada.status, 'PAGA')
		self.assertEqual(atualizada.valor_pago, 1000)
		self.assertEqual(atualizada.baixado_por, self.usuario)

	def test_registrar_baixa_manual_parcela_inadimplente(self):
		parcela = gerar_entrada(
			venda=self.venda,
			valor=1000,
			data_vencimento=date(2026, 1, 5),
			usuario=self.usuario,
		)
		parcela.status = 'INADIMPLENTE'
		parcela.save(update_fields=['status'])

		atualizada = registrar_baixa_manual(
			parcela=parcela,
			valor_pago=1000,
			data_pagamento=date(2026, 1, 6),
			usuario=self.usuario,
		)
		self.assertEqual(atualizada.status, 'PAGA')

	def test_registrar_baixa_manual_parcela_paga_levanta_valueerror(self):
		parcela = gerar_entrada(
			venda=self.venda,
			valor=1000,
			data_vencimento=date(2026, 1, 5),
			usuario=self.usuario,
		)
		parcela.status = 'PAGA'
		parcela.save(update_fields=['status'])

		with self.assertRaisesMessage(ValueError, 'Parcela não pode ser baixada com status atual'):
			registrar_baixa_manual(
				parcela=parcela,
				valor_pago=1000,
				data_pagamento=date(2026, 1, 6),
				usuario=self.usuario,
			)

	def test_registrar_baixa_manual_parcela_cancelada_levanta_valueerror(self):
		parcela = gerar_entrada(
			venda=self.venda,
			valor=1000,
			data_vencimento=date(2026, 1, 5),
			usuario=self.usuario,
		)
		parcela.status = 'CANCELADA'
		parcela.save(update_fields=['status'])

		with self.assertRaisesMessage(ValueError, 'Parcela não pode ser baixada com status atual'):
			registrar_baixa_manual(
				parcela=parcela,
				valor_pago=1000,
				data_pagamento=date(2026, 1, 6),
				usuario=self.usuario,
			)

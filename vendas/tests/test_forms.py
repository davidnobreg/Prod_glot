import pytest
from decimal import Decimal

from vendas.forms import RegisterVendaForm


@pytest.mark.django_db
class TestCalcularValorFinanciado:
	"""
	Trava o comportamento intencional (confirmado com o cliente) de que
	valor_sinal NÃO abate valor_financiado — só valor_desconto e valor_entrada
	entram na conta. Ver docstring de _calcular_valor_financiado em forms.py.
	"""

	def _build_form(self, lote, corretor_user, valor_desconto='R$ 0,00', valor_entrada='R$ 0,00', valor_sinal='R$ 0,00'):
		return RegisterVendaForm(
			data={
				'valor_desconto': valor_desconto,
				'valor_entrada': valor_entrada,
				'valor_sinal': valor_sinal,
				'reajuste': 'True',
			},
			lote=lote,
			user=corretor_user,
		)

	def test_sem_desconto_sem_sinal(self, lote, corretor_user):
		form = self._build_form(lote, corretor_user)
		assert form.is_valid(), form.errors
		instance = form.save(commit=False)
		assert instance.valor_financiado == Decimal('20000.00')

	def test_com_desconto_sem_sinal(self, lote, corretor_user):
		form = self._build_form(lote, corretor_user, valor_desconto='R$ 1.000,00')
		assert form.is_valid(), form.errors
		instance = form.save(commit=False)
		assert instance.valor_financiado == Decimal('19000.00')

	def test_sem_desconto_com_sinal(self, lote, corretor_user):
		# sinal é gravado no form mas não deve reduzir o valor financiado
		form = self._build_form(lote, corretor_user, valor_sinal='R$ 2.000,00')
		assert form.is_valid(), form.errors
		instance = form.save(commit=False)
		assert instance.valor_financiado == Decimal('20000.00')
		assert instance.valor_sinal == Decimal('2000.00')

	def test_com_desconto_com_sinal(self, lote, corretor_user):
		form = self._build_form(
			lote, corretor_user,
			valor_desconto='R$ 1.000,00',
			valor_sinal='R$ 2.000,00',
		)
		assert form.is_valid(), form.errors
		instance = form.save(commit=False)
		assert instance.valor_financiado == Decimal('19000.00')


@pytest.mark.django_db
class TestPersistenciaValorTotal:
	"""
	Valor total do lote precisa ficar gravado no banco em valor_inicio_contrato
	(RegisterVenda não tem campo valor_total — setattr nele é descartado
	silenciosamente pelo Django).
	"""

	def test_valor_total_do_lote_persiste_em_valor_inicio_contrato(self, lote, corretor_user):
		form = RegisterVendaForm(
			data={'reajuste': 'True'},
			lote=lote,
			user=corretor_user,
		)
		assert form.is_valid(), form.errors
		instance = form.save(commit=False)
		assert instance.valor_inicio_contrato == Decimal('20000.00')
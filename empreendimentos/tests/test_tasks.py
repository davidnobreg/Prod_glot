import pytest
from empreendimentos.models import Lote
from empreendimentos.tasks import liberar_lotes_sem_venda
from vendas.models import RegisterVenda


def _lote(quadra, situacao='EM_RESERVA', nome='L_TASK'):
	return Lote.objects.create(
		lote=nome,
		area='100',
		situacao=situacao,
		quadra=quadra,
		valor_metro_quadrado='100',
		telefone='(83) 99999-9999',
		telefone_user='(83) 99999-9999',
	)


class TestLiberarLotesSemVenda:

	def test_lote_sem_venda_liberado(self, db, quadra):
		"""EM_RESERVA sem RegisterVenda → DISPONIVEL."""
		lote = _lote(quadra)
		liberar_lotes_sem_venda.apply()
		lote.refresh_from_db()
		assert lote.situacao == 'DISPONIVEL'

	def test_lote_com_venda_ativa_nao_liberado(self, db, quadra, cliente_pf, admin_user):
		"""EM_RESERVA com is_ativo=True → permanece EM_RESERVA."""
		lote = _lote(quadra)
		RegisterVenda.objects.create(
			lote=lote,
			cliente=cliente_pf,
			corretor=admin_user,
			tipo_venda='RESERVADO',
			is_ativo=True,
		)
		liberar_lotes_sem_venda.apply()
		lote.refresh_from_db()
		assert lote.situacao == 'EM_RESERVA'

	def test_lote_com_venda_ativa_cancelada_nao_liberado(self, db, quadra, cliente_pf, admin_user):
		"""
		Regressão: is_ativo=True + tipo_venda='CANCELADA' (estado corrompido)
		→ NÃO deve liberar o lote.
		Bug anterior usava .exclude(tipo_venda='CANCELADA') que ignorava esse caso.
		"""
		lote = _lote(quadra)
		RegisterVenda.objects.create(
			lote=lote,
			cliente=cliente_pf,
			corretor=admin_user,
			tipo_venda='CANCELADA',
			is_ativo=True,
		)
		liberar_lotes_sem_venda.apply()
		lote.refresh_from_db()
		assert lote.situacao == 'EM_RESERVA'

	def test_lote_com_venda_inativa_liberado(self, db, quadra, cliente_pf, admin_user):
		"""EM_RESERVA com is_ativo=False → DISPONIVEL."""
		lote = _lote(quadra, nome='L_INATIVA')
		RegisterVenda.objects.create(
			lote=lote,
			cliente=cliente_pf,
			corretor=admin_user,
			tipo_venda='CANCELADA',
			is_ativo=False,
		)
		liberar_lotes_sem_venda.apply()
		lote.refresh_from_db()
		assert lote.situacao == 'DISPONIVEL'

	def test_lote_disponivel_nao_afetado(self, db, quadra):
		"""Lote DISPONIVEL não é tocado."""
		lote = _lote(quadra, situacao='DISPONIVEL')
		liberar_lotes_sem_venda.apply()
		lote.refresh_from_db()
		assert lote.situacao == 'DISPONIVEL'

	def test_multiplos_lotes_estados_mistos(self, db, quadra, cliente_pf, admin_user):
		"""Só lotes sem venda ativa são liberados; os com venda ativa permanecem."""
		lote_livre = _lote(quadra, nome='L_LIVRE')
		lote_preso = _lote(quadra, nome='L_PRESO')
		RegisterVenda.objects.create(
			lote=lote_preso,
			cliente=cliente_pf,
			corretor=admin_user,
			tipo_venda='RESERVADO',
			is_ativo=True,
		)
		liberar_lotes_sem_venda.apply()
		lote_livre.refresh_from_db()
		lote_preso.refresh_from_db()
		assert lote_livre.situacao == 'DISPONIVEL'
		assert lote_preso.situacao == 'EM_RESERVA'

	def test_sem_lotes_nao_gera_erro(self, db):
		"""Queryset vazio → sem crash, retorna 0."""
		result = liberar_lotes_sem_venda.apply()
		assert result.result == 0
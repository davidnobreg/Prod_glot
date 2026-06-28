import pytest
from vendas.models import RegisterVenda, VendaDocumento


@pytest.mark.django_db
class TestRegisterVendaStr:

	def test_str_com_lote(self, venda):
		resultado = str(venda)
		assert resultado is not None

	def test_str_sem_lote_nao_crasha(self, db, cliente_pf, admin_user):
		venda = RegisterVenda.objects.create(
			lote=None,
			cliente=cliente_pf,
			corretor=admin_user,
			tipo_venda='CANCELADA',
			is_ativo=False,
		)
		resultado = str(venda)
		assert resultado is not None


@pytest.mark.django_db
class TestVendaDocumento:

	def test_ciclo_default_e_1(self, venda, admin_user):
		doc = VendaDocumento.objects.create(
			venda=venda,
			tipo='proposta_assinada',
			arquivo_assinado='vendas/doc.pdf',
			status='enviado',
			enviado_por=admin_user,
		)
		assert doc.ciclo == 1

	def test_status_choices_inclui_arquivado(self):
		choices = dict(VendaDocumento.STATUS_CHOICES)
		assert 'arquivado' in choices
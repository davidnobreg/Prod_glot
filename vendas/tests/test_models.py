import pytest
from django.db import IntegrityError, transaction

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

	def test_constraint_impede_dois_aprovados_mesmo_venda_tipo(self, venda, admin_user):
		"""Rede de segurança do banco: mesmo bypassando a lógica de aplicação (create()
		direto), o banco não permite dois VendaDocumento aprovados pro mesmo (venda, tipo)."""
		VendaDocumento.objects.create(
			venda=venda, tipo='proposta_assinada', status='aprovado',
			enviado_por=admin_user, arquivo_assinado='fake/primeira.pdf',
		)
		with pytest.raises(IntegrityError):
			with transaction.atomic():
				VendaDocumento.objects.create(
					venda=venda, tipo='proposta_assinada', status='aprovado',
					enviado_por=admin_user, arquivo_assinado='fake/segunda.pdf',
				)

	def test_constraint_nao_impede_dois_pendentes_mesmo_venda_tipo(self, venda, admin_user):
		"""A constraint é condicional (status='aprovado') — outros status coexistem
		normalmente, é o ciclo de upload/reenvio normal."""
		VendaDocumento.objects.create(
			venda=venda, tipo='proposta_assinada', status='enviado',
			enviado_por=admin_user, arquivo_assinado='fake/primeira.pdf',
		)
		segunda = VendaDocumento.objects.create(
			venda=venda, tipo='proposta_assinada', status='enviado',
			enviado_por=admin_user, arquivo_assinado='fake/segunda.pdf',
		)
		assert segunda.pk is not None
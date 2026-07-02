import pytest
from django.urls import reverse

from vendas.models import VendaDocumento


class TestCancelarReservaView:
	"""
	URL: /vendas/reservado_delete/<reserva_uuid>/
	Proteção: has_permission_decorator('cancelarReservado') — superuser bypassa.
	"""

	def test_cancelar_reserva_arquiva_documento_rejeitado(self, client, admin_user, venda):
		"""Documento rejeitado também deve ser arquivado ao cancelar — a venda não é
		apagada no cancelamento, então um doc rejeitado fora de 'arquivado' ficaria
		"vigente" pra sempre numa venda morta."""
		VendaDocumento.objects.create(
			venda=venda, tipo='outros', status='rejeitado', ciclo=1,
			arquivo_assinado='fake/rej.pdf', enviado_por=admin_user,
		)
		client.force_login(admin_user)
		client.post(reverse('delete-reservado', kwargs={'reserva_uuid': venda.uuid}))
		doc = VendaDocumento.objects.get(venda=venda)
		assert doc.status == 'arquivado'

	def test_cancelar_reserva_arquiva_documento_aprovado(self, client, admin_user, venda):
		"""Comportamento preexistente preservado: aprovado também arquiva."""
		VendaDocumento.objects.create(
			venda=venda, tipo='outros', status='aprovado', ciclo=1,
			arquivo_assinado='fake/apr.pdf', enviado_por=admin_user,
		)
		client.force_login(admin_user)
		client.post(reverse('delete-reservado', kwargs={'reserva_uuid': venda.uuid}))
		doc = VendaDocumento.objects.get(venda=venda)
		assert doc.status == 'arquivado'

	def test_cancelar_reserva_nao_reprocessa_documento_ja_arquivado(self, client, admin_user, venda):
		"""Doc já arquivado continua arquivado (sem erro), status não muda."""
		VendaDocumento.objects.create(
			venda=venda, tipo='outros', status='arquivado', ciclo=1,
			arquivo_assinado='fake/arq.pdf', enviado_por=admin_user,
		)
		client.force_login(admin_user)
		response = client.post(reverse('delete-reservado', kwargs={'reserva_uuid': venda.uuid}))
		assert response.status_code == 302
		doc = VendaDocumento.objects.get(venda=venda)
		assert doc.status == 'arquivado'

	def test_cancelar_reserva_atualiza_venda_e_lote(self, client, admin_user, venda):
		client.force_login(admin_user)
		client.post(reverse('delete-reservado', kwargs={'reserva_uuid': venda.uuid}))
		venda.refresh_from_db()
		venda.lote.refresh_from_db()
		assert venda.tipo_venda == 'CANCELADA'
		assert venda.is_ativo is False
		assert venda.lote.situacao == 'DISPONIVEL'

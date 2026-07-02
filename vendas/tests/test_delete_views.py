import pytest
from django.urls import reverse

from vendas.models import VendaDocumento


def test_cancelar_reserva_arquiva_documento_rejeitado(client, admin_user, venda):
	VendaDocumento.objects.create(
		venda=venda, tipo='outros', status='rejeitado', ciclo=1,
		arquivo_assinado='fake/rej.pdf', enviado_por=admin_user,
	)
	client.force_login(admin_user)
	client.post(reverse('delete-reservado', kwargs={'reserva_uuid': venda.uuid}))
	doc = VendaDocumento.objects.get(venda=venda)
	assert doc.status == 'arquivado'
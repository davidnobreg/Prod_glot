import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from accounts.models import User
from vendas.models import VendaDocumento


class TestCancelarReservadoCadastroView:
	"""
	URL: /vendas/reservado_cancelada_cadastro/<lote_uuid>/
	Proteção: has_permission_decorator('cancelarReservadoCadastro') — superuser bypassa.
	"""

	def test_primeira_tentativa_cancela_e_desativa_venda(self, client, admin_user, venda):
		client.force_login(admin_user)
		client.post(reverse('cancelar-reservado-cadastro', kwargs={'cancelaReserva_uuid': venda.lote.uuid}))
		venda.refresh_from_db()
		venda.lote.refresh_from_db()
		assert venda.tipo_venda == 'CANCELADA'
		assert venda.is_ativo is False
		assert venda.lote.situacao == 'DISPONIVEL'

	def test_segunda_tentativa_e_idempotente_nao_reprocessa(self, client, admin_user, venda):
		"""Dupla-submissão (double-click, retry de rede) não deve reprocessar
		nem confundir o usuário com uma segunda mensagem de sucesso."""
		client.force_login(admin_user)
		client.post(reverse('cancelar-reservado-cadastro', kwargs={'cancelaReserva_uuid': venda.lote.uuid}))

		response = client.post(
			reverse('cancelar-reservado-cadastro', kwargs={'cancelaReserva_uuid': venda.lote.uuid}),
			follow=False,
		)

		venda.refresh_from_db()
		assert venda.tipo_venda == 'CANCELADA'
		assert venda.is_ativo is False

		mensagens = [str(m) for m in get_messages(response.wsgi_request)]
		assert any('já estava cancelada' in m.lower() for m in mensagens)


class TestCancelarVendaView:
	"""
	URL: /vendas/venda_delete/<venda_uuid>/
	Proteção: has_permission_decorator('cancelarVenda') — superuser bypassa.
	"""

	def test_cancela_venda_atualiza_lote_e_venda(self, client, admin_user, venda):
		client.force_login(admin_user)
		client.post(reverse('delete-venda', kwargs={'delete_uuid': venda.uuid}))
		venda.refresh_from_db()
		venda.lote.refresh_from_db()
		assert venda.tipo_venda == 'CANCELADA'
		assert venda.is_ativo is False
		assert venda.lote.situacao == 'DISPONIVEL'


class TestCancelarAceiteReservaView:
	"""
	URL: /vendas/reservado_delete_aceite/<reserva_uuid>/
	Proteção: has_permission_decorator('cancelarAceiteReservado') — superuser bypassa.
	"""

	def test_cancela_aceite_marca_nao_aceite_e_lote_pre_reserva(self, client, admin_user, venda):
		client.force_login(admin_user)
		response = client.post(reverse('delete-aceite', kwargs={'reserva_uuid': venda.uuid}))
		venda.refresh_from_db()
		venda.lote.refresh_from_db()
		assert venda.tipo_venda == 'NAO_ACEITE'
		assert venda.is_ativo is False
		assert venda.lote.situacao == 'PRE-RESERVA'
		assert response.url == reverse(
			'listar-quadras', kwargs={'empreendimento_uuid': venda.lote.quadra.empr.uuid}
		)

	def test_administrador_nao_superuser_tem_permissao(self, client, db, venda):
		"""Botão 'Não aceita' em analisa.html é admin-only, mas a role
		Administrador não tinha o codename cancelarAceiteReservado (só a role
		Corretor tinha) — gap de permissão real, só não pego pelos outros
		testes por usarem admin_user com is_superuser=True (bypassa o decorator)."""
		administrador = User.objects.create_user(
			username='administrador_nao_super',
			password='senha123',
			tipo_usuario='ADMINISTRADOR',
		)
		client.force_login(administrador)
		response = client.post(reverse('delete-aceite', kwargs={'reserva_uuid': venda.uuid}))
		assert response.status_code == 302
		venda.refresh_from_db()
		assert venda.tipo_venda == 'NAO_ACEITE'


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
		response = client.post(reverse('delete-reservado', kwargs={'reserva_uuid': venda.uuid}))
		venda.refresh_from_db()
		venda.lote.refresh_from_db()
		assert venda.tipo_venda == 'CANCELADA'
		assert venda.is_ativo is False
		assert venda.lote.situacao == 'DISPONIVEL'
		assert response.url == reverse(
			'listar-quadras', kwargs={'empreendimento_uuid': venda.lote.quadra.empr.uuid}
		)


class TestCancelarPreVendaView:
	"""
	URL: /vendas/pre-venda/cancelar/<venda_uuid>/
	Proteção: has_permission_decorator('criarVenda') + checagem ADMINISTRADOR em runtime.
	"""

	def test_cancela_pre_venda_volta_para_reservado(self, client, admin_user, venda_pre_venda):
		client.force_login(admin_user)
		response = client.post(reverse('cancelar-pre-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))

		venda_pre_venda.refresh_from_db()
		venda_pre_venda.lote.refresh_from_db()
		assert venda_pre_venda.tipo_venda == 'RESERVADO'
		assert venda_pre_venda.lote.situacao == 'RESERVADO'
		assert response.url == reverse('reservadoDetalhes', kwargs={'reserva_uuid': venda_pre_venda.lote.uuid})

	def test_nao_administrador_e_bloqueado(self, client, corretor_user, venda_pre_venda):
		client.force_login(corretor_user)
		client.post(reverse('cancelar-pre-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))

		venda_pre_venda.refresh_from_db()
		assert venda_pre_venda.tipo_venda == 'PRE-VENDA'

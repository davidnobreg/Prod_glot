import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone

from vendas.models import RegisterVenda, VendaDocumento


@pytest.fixture
def proprietario_user(db):
	from accounts.models import User
	return User.objects.create_user(
		username='proprietario_test',
		password='senha123',
		tipo_usuario='PROPRIETARIO',
	)


class TestCriarVendaView:

	@pytest.fixture
	def documento_gerado_finalizado(self, db, venda, admin_user):
		from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
		modelo = ModeloDocumento.objects.create(
			titulo='Proposta Padrão', tipo='proposta', conteudo_html='<p>x</p>',
			eh_global=True, criado_por=admin_user,
		)
		return DocumentoGerado.objects.create(
			modelo=modelo, modelo_versao_snapshot=1, venda=venda, titulo='Proposta',
			conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
		)

	@pytest.fixture
	def contrato_gerado_finalizado(self, db, venda, admin_user):
		from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
		modelo = ModeloDocumento.objects.create(
			titulo='Contrato Padrão', tipo='contrato', conteudo_html='<p>x</p>',
			eh_global=True, criado_por=admin_user,
		)
		return DocumentoGerado.objects.create(
			modelo=modelo, modelo_versao_snapshot=1, venda=venda, titulo='Contrato',
			conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
		)

	@pytest.fixture
	def proposta_aprovada(self, venda, admin_user, documento_gerado_finalizado):
		return VendaDocumento.objects.create(
			venda=venda, tipo='proposta_assinada', status='aprovado',
			enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
			documento_gerado=documento_gerado_finalizado,
		)

	@pytest.fixture
	def contrato_aprovado(self, venda, admin_user, contrato_gerado_finalizado):
		return VendaDocumento.objects.create(
			venda=venda, tipo='contrato_assinado', status='aprovado',
			enviado_por=admin_user, arquivo_assinado='fake/contrato.pdf',
			documento_gerado=contrato_gerado_finalizado,
		)

	@pytest.fixture
	def checklist_cliente_completo(self, venda):
		from clientes.models import ClienteDocumento
		ClienteDocumento.objects.create(
			cliente=venda.cliente, tipo='CNH', arquivo='fake/cnh.pdf', status='disponivel',
		)
		ClienteDocumento.objects.create(
			cliente=venda.cliente, tipo='COMPROVANTE_RESIDENCIA',
			arquivo='fake/comp.pdf', status='disponivel',
		)
		# cliente_pf (conftest) tem estado_civil='solteiro' — COMPROVANTE_ESTADO_CIVIL não obrigatório

	def test_post_avanca_tipo_venda_para_pre_venda(
		self, client, admin_user, venda, proposta_aprovada, contrato_aprovado,
		checklist_cliente_completo,
	):
		client.force_login(admin_user)
		client.post(reverse('criar-venda', kwargs={'venda_uuid': venda.uuid}))
		venda.refresh_from_db()
		assert venda.tipo_venda == 'PRE-VENDA'

	def test_post_avanca_lote_para_pre_venda(
		self, client, admin_user, venda, proposta_aprovada, contrato_aprovado,
		checklist_cliente_completo,
	):
		client.force_login(admin_user)
		client.post(reverse('criar-venda', kwargs={'venda_uuid': venda.uuid}))
		venda.lote.refresh_from_db()
		assert venda.lote.situacao == 'PRE-VENDA'

	def test_dt_venda_nao_setada_na_criacao(
		self, client, admin_user, venda, proposta_aprovada, contrato_aprovado,
	):
		client.force_login(admin_user)
		client.post(reverse('criar-venda', kwargs={'venda_uuid': venda.uuid}))
		venda.refresh_from_db()
		assert venda.dt_venda is None

	def test_redirect_para_pre_venda_detalhe(
		self, client, admin_user, venda, proposta_aprovada, contrato_aprovado,
		checklist_cliente_completo,
	):
		client.force_login(admin_user)
		response = client.post(reverse('criar-venda', kwargs={'venda_uuid': venda.uuid}))
		expected = reverse('pre-venda-detalhe', kwargs={'venda_uuid': venda.uuid})
		assert response.status_code == 302
		assert response.url == expected

	def test_anonimo_retorna_403(self, client, venda):
		response = client.post(reverse('criar-venda', kwargs={'venda_uuid': venda.uuid}))
		assert response.status_code == 403

	def test_sem_permissao_retorna_403(self, client, proprietario_user, venda):
		client.force_login(proprietario_user)
		response = client.post(reverse('criar-venda', kwargs={'venda_uuid': venda.uuid}))
		assert response.status_code == 403

	def test_bloqueado_so_com_proposta(self, client, admin_user, venda, proposta_aprovada):
		"""Só proposta aprovada e vinculada, sem contrato — não avança."""
		client.force_login(admin_user)
		response = client.post(reverse('criar-venda', kwargs={'venda_uuid': venda.uuid}))
		venda.refresh_from_db()
		assert venda.tipo_venda != 'PRE-VENDA'
		mensagens = [str(m) for m in get_messages(response.wsgi_request)]
		assert any('contrato' in m.lower() for m in mensagens)
		assert not any('proposta' in m.lower() for m in mensagens)

	def test_bloqueado_so_com_contrato(self, client, admin_user, venda, contrato_aprovado):
		"""Só contrato aprovado e vinculado, sem proposta — não avança."""
		client.force_login(admin_user)
		response = client.post(reverse('criar-venda', kwargs={'venda_uuid': venda.uuid}))
		venda.refresh_from_db()
		assert venda.tipo_venda != 'PRE-VENDA'
		mensagens = [str(m) for m in get_messages(response.wsgi_request)]
		assert any('proposta' in m.lower() for m in mensagens)
		assert not any('contrato' in m.lower() for m in mensagens)

	def test_bloqueado_sem_nenhum(self, client, admin_user, venda):
		"""Sem proposta nem contrato aprovados — não avança, mensagem cita os dois."""
		client.force_login(admin_user)
		response = client.post(reverse('criar-venda', kwargs={'venda_uuid': venda.uuid}))
		venda.refresh_from_db()
		assert venda.tipo_venda != 'PRE-VENDA'
		mensagens = [str(m) for m in get_messages(response.wsgi_request)]
		assert any('proposta' in m.lower() and 'contrato' in m.lower() for m in mensagens)


@pytest.fixture
def documento_gerado_finalizado(db, venda_pre_venda, admin_user):
	from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
	modelo = ModeloDocumento.objects.create(
		titulo='Proposta Padrão', tipo='proposta', conteudo_html='<p>x</p>',
		eh_global=True, criado_por=admin_user,
	)
	return DocumentoGerado.objects.create(
		modelo=modelo, modelo_versao_snapshot=1, venda=venda_pre_venda, titulo='Proposta',
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
	)


@pytest.fixture
def contrato_gerado_finalizado(db, venda_pre_venda, admin_user):
	from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
	modelo = ModeloDocumento.objects.create(
		titulo='Contrato Padrão', tipo='contrato', conteudo_html='<p>x</p>',
		eh_global=True, criado_por=admin_user,
	)
	return DocumentoGerado.objects.create(
		modelo=modelo, modelo_versao_snapshot=1, venda=venda_pre_venda, titulo='Contrato',
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
	)


class TestEfetivarVendaView:

	@pytest.fixture
	def proposta_aprovada(self, venda_pre_venda, admin_user, documento_gerado_finalizado):
		return VendaDocumento.objects.create(
			venda=venda_pre_venda,
			tipo='proposta_assinada',
			status='aprovado',
			enviado_por=admin_user,
			arquivo_assinado='fake/proposta.pdf',
			documento_gerado=documento_gerado_finalizado,
		)

	@pytest.fixture
	def contrato_aprovado(self, venda_pre_venda, admin_user, contrato_gerado_finalizado):
		return VendaDocumento.objects.create(
			venda=venda_pre_venda,
			tipo='contrato_assinado',
			status='aprovado',
			enviado_por=admin_user,
			arquivo_assinado='fake/contrato.pdf',
			documento_gerado=contrato_gerado_finalizado,
		)

	@pytest.fixture
	def checklist_cliente_completo(self, venda_pre_venda):
		from clientes.models import ClienteDocumento
		ClienteDocumento.objects.create(
			cliente=venda_pre_venda.cliente, tipo='CNH', arquivo='fake/cnh.pdf', status='disponivel',
		)
		ClienteDocumento.objects.create(
			cliente=venda_pre_venda.cliente, tipo='COMPROVANTE_RESIDENCIA',
			arquivo='fake/comp.pdf', status='disponivel',
		)
		# cliente_pf (conftest) tem estado_civil='solteiro' — COMPROVANTE_ESTADO_CIVIL não obrigatório

	def test_post_seta_venda_vendido(
		self, client, admin_user, venda_pre_venda, proposta_aprovada, contrato_aprovado,
		checklist_cliente_completo,
	):
		client.force_login(admin_user)
		client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		venda_pre_venda.refresh_from_db()
		assert venda_pre_venda.tipo_venda == 'VENDIDO'

	def test_post_seta_lote_vendido(
		self, client, admin_user, venda_pre_venda, proposta_aprovada, contrato_aprovado,
		checklist_cliente_completo,
	):
		client.force_login(admin_user)
		client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		venda_pre_venda.lote.refresh_from_db()
		assert venda_pre_venda.lote.situacao == 'VENDIDO'

	def test_dt_venda_preenchida_apos_efetivar(
		self, client, admin_user, venda_pre_venda, proposta_aprovada, contrato_aprovado,
		checklist_cliente_completo,
	):
		client.force_login(admin_user)
		client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		venda_pre_venda.refresh_from_db()
		assert venda_pre_venda.dt_venda == timezone.localdate()

	def test_nao_administrador_e_redirecionado(self, client, corretor_user, venda_pre_venda):
		client.force_login(corretor_user)
		response = client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		assert response.status_code == 302
		venda_pre_venda.refresh_from_db()
		assert venda_pre_venda.tipo_venda != 'VENDIDO'

	def test_sem_proposta_aprovada_nao_efetiva(self, client, admin_user, venda_pre_venda):
		client.force_login(admin_user)
		client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		venda_pre_venda.refresh_from_db()
		assert venda_pre_venda.tipo_venda != 'VENDIDO'

	def test_sem_contrato_aprovado_nao_efetiva(
		self, client, admin_user, venda_pre_venda, proposta_aprovada, checklist_cliente_completo,
	):
		"""Só proposta aprovada, sem contrato — não efetiva."""
		client.force_login(admin_user)
		client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		venda_pre_venda.refresh_from_db()
		assert venda_pre_venda.tipo_venda != 'VENDIDO'

	def test_checklist_incompleto_nao_efetiva(
		self, client, admin_user, venda_pre_venda, proposta_aprovada, contrato_aprovado,
	):
		"""Proposta e contrato aprovados, mas checklist do cliente incompleto — não efetiva."""
		client.force_login(admin_user)
		client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		venda_pre_venda.refresh_from_db()
		assert venda_pre_venda.tipo_venda != 'VENDIDO'

	def test_proposta_aprovada_sem_documento_gerado_nao_efetiva(
		self, client, admin_user, venda_pre_venda,
	):
		"""proposta_assinada aprovado SEM documento_gerado vinculado (caso venda 301) — bloqueia."""
		VendaDocumento.objects.create(
			venda=venda_pre_venda, tipo='proposta_assinada', status='aprovado',
			enviado_por=admin_user, arquivo_assinado='fake/proposta.pdf',
			# documento_gerado=None — de propósito
		)
		client.force_login(admin_user)
		client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		venda_pre_venda.refresh_from_db()
		assert venda_pre_venda.tipo_venda != 'VENDIDO'

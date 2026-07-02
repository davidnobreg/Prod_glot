import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from accounts.models import User
from vendas.models import RegisterVenda, VendaDocumento
from clientes.models import ClienteDocumento


def _fake_file(name='test.pdf'):
	return SimpleUploadedFile(name, b'%PDF-1.4 fake', content_type='application/pdf')


def _documento_gerado_finalizado(venda, admin_user, tipo):
	from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
	modelo = ModeloDocumento.objects.create(
		titulo=f'{tipo.title()} Padrão', tipo=tipo, conteudo_html='<p>x</p>',
		eh_global=True, criado_por=admin_user,
	)
	return DocumentoGerado.objects.create(
		modelo=modelo, modelo_versao_snapshot=1, venda=venda, titulo=tipo.title(),
		conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
	)


# ─── ReservadoView ────────────────────────────────────────────────────────────

class TestReservadoView:
	"""
	URL: /vendas/reservado/<lote_uuid>/
	Proteção: has_permission_decorator('reservado') — superuser bypassa.
	"""

	def test_get_200_admin(self, client, admin_user, venda):
		client.force_login(admin_user)
		url = reverse('reservado', kwargs={'lote_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.status_code == 200

	def test_anonimo_retorna_403(self, client, venda):
		url = reverse('reservado', kwargs={'lote_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.status_code == 403

	def test_contexto_contem_lote(self, client, admin_user, venda):
		client.force_login(admin_user)
		url = reverse('reservado', kwargs={'lote_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.context['lote'] == venda.lote

	def test_contexto_contem_reservas(self, client, admin_user, venda):
		client.force_login(admin_user)
		url = reverse('reservado', kwargs={'lote_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.context['reservas'] == venda

	def test_lote_vendido_sem_venda_retorna_reservas_none(
		self, client, admin_user, lote
	):
		"""Lote situacao=VENDIDO sem RegisterVenda → reservas=None no contexto."""
		lote.situacao = 'VENDIDO'
		lote.save()
		client.force_login(admin_user)
		url = reverse('reservado', kwargs={'lote_uuid': lote.uuid})
		response = client.get(url)
		assert response.status_code == 200
		assert response.context['reservas'] is None


# ─── AnaliseView ──────────────────────────────────────────────────────────────

class TestAnaliseView:
	"""
	URL: /vendas/analise/<lote_uuid>/
	Proteção: has_permission_decorator('analiseReserva') — superuser bypassa.
	"""

	@pytest.fixture
	def venda_analise(self, db, lote, cliente_pf, admin_user):
		lote.situacao = 'ANALISE'
		lote.save()
		return RegisterVenda.objects.create(
			lote=lote,
			cliente=cliente_pf,
			corretor=admin_user,
			tipo_venda='ANALISE',
			is_ativo=True,
		)

	def test_get_200_admin(self, client, admin_user, venda_analise):
		client.force_login(admin_user)
		url = reverse('analise', kwargs={'lote_uuid': venda_analise.lote.uuid})
		response = client.get(url)
		assert response.status_code == 200

	def test_anonimo_retorna_403(self, client, venda_analise):
		url = reverse('analise', kwargs={'lote_uuid': venda_analise.lote.uuid})
		response = client.get(url)
		assert response.status_code == 403

	def test_contexto_contem_lote_e_reserva(self, client, admin_user, venda_analise):
		client.force_login(admin_user)
		url = reverse('analise', kwargs={'lote_uuid': venda_analise.lote.uuid})
		response = client.get(url)
		assert response.context['lote'] == venda_analise.lote
		assert response.context['reservas'] == venda_analise

	def test_valor_lote_calculado_corretamente(self, client, admin_user, venda_analise):
		"""valor_lote = area * valor_metro_quadrado."""
		lote = venda_analise.lote
		expected = float(lote.area or 0) * float(lote.valor_metro_quadrado or 0)
		client.force_login(admin_user)
		url = reverse('analise', kwargs={'lote_uuid': lote.uuid})
		response = client.get(url)
		assert response.context['valor_lote'] == expected

	def test_lote_analise_sem_venda_renderiza_sem_erro(self, client, admin_user, lote, db):
		"""Regressão: lote ANALISE sem RegisterVenda não deve crashar com NoReverseMatch."""
		lote.situacao = 'ANALISE'
		lote.save()
		client.force_login(admin_user)
		url = reverse('analise', kwargs={'lote_uuid': lote.uuid})
		response = client.get(url)
		assert response.status_code == 200
		assert response.context['reservas'] is None


# ─── ReservadoDetalheView ─────────────────────────────────────────────────────

class TestReservadoDetalheView:
	"""
	URL: /vendas/reservado_detalhes/<reserva_uuid>/
	Proteção: has_permission_decorator('reservadoDetalhe') — superuser bypassa.
	Ownership: ADMINISTRADOR vê tudo; CORRETOR só vê própria venda.
	"""

	def test_get_200_admin(self, client, admin_user, venda):
		client.force_login(admin_user)
		url = reverse('reservadoDetalhes', kwargs={'reserva_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.status_code == 200

	def test_anonimo_retorna_403(self, client, venda):
		url = reverse('reservadoDetalhes', kwargs={'reserva_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.status_code == 403

	def test_proposta_aprovada_false_sem_documento(self, client, admin_user, venda):
		client.force_login(admin_user)
		url = reverse('reservadoDetalhes', kwargs={'reserva_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.context['proposta_aprovada'] is False

	def test_proposta_aprovada_true_com_documento_aprovado(
		self, client, admin_user, venda, settings, tmp_path
	):
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		VendaDocumento.objects.create(
			venda=venda,
			tipo='proposta_assinada',
			status='aprovado',
			ciclo=1,
			arquivo_assinado=_fake_file(),
			enviado_por=admin_user,
		)
		client.force_login(admin_user)
		url = reverse('reservadoDetalhes', kwargs={'reserva_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.context['proposta_aprovada'] is True

	def test_pre_venda_liberada_false_sem_documentos(self, client, admin_user, venda):
		client.force_login(admin_user)
		url = reverse('reservadoDetalhes', kwargs={'reserva_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.context['pre_venda_liberada'] is False

	def test_pre_venda_liberada_false_so_com_proposta(
		self, client, admin_user, venda, settings, tmp_path
	):
		"""Reproduz o bug relatado em teste manual: botão não pode ficar habilitado só com proposta."""
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		doc_gerado = _documento_gerado_finalizado(venda, admin_user, 'proposta')
		VendaDocumento.objects.create(
			venda=venda, tipo='proposta_assinada', status='aprovado', ciclo=1,
			arquivo_assinado=_fake_file(), enviado_por=admin_user, documento_gerado=doc_gerado,
		)
		client.force_login(admin_user)
		url = reverse('reservadoDetalhes', kwargs={'reserva_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.context['pre_venda_liberada'] is False

	def test_pre_venda_liberada_false_so_com_contrato(
		self, client, admin_user, venda, settings, tmp_path
	):
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		doc_gerado = _documento_gerado_finalizado(venda, admin_user, 'contrato')
		VendaDocumento.objects.create(
			venda=venda, tipo='contrato_assinado', status='aprovado', ciclo=1,
			arquivo_assinado=_fake_file(), enviado_por=admin_user, documento_gerado=doc_gerado,
		)
		client.force_login(admin_user)
		url = reverse('reservadoDetalhes', kwargs={'reserva_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.context['pre_venda_liberada'] is False

	def test_pre_venda_liberada_false_proposta_aprovada_sem_documento_gerado(
		self, client, admin_user, venda, settings, tmp_path
	):
		"""proposta_aprovada (contexto legado) fica True, mas pre_venda_liberada exige lastro — continua False."""
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		VendaDocumento.objects.create(
			venda=venda, tipo='proposta_assinada', status='aprovado', ciclo=1,
			arquivo_assinado=_fake_file(), enviado_por=admin_user,
			# documento_gerado=None — de propósito
		)
		client.force_login(admin_user)
		url = reverse('reservadoDetalhes', kwargs={'reserva_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.context['proposta_aprovada'] is True
		assert response.context['pre_venda_liberada'] is False

	def test_pre_venda_liberada_true_com_proposta_e_contrato_vinculados(
		self, client, admin_user, venda, settings, tmp_path
	):
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		doc_proposta = _documento_gerado_finalizado(venda, admin_user, 'proposta')
		doc_contrato = _documento_gerado_finalizado(venda, admin_user, 'contrato')
		VendaDocumento.objects.create(
			venda=venda, tipo='proposta_assinada', status='aprovado', ciclo=1,
			arquivo_assinado=_fake_file(), enviado_por=admin_user, documento_gerado=doc_proposta,
		)
		VendaDocumento.objects.create(
			venda=venda, tipo='contrato_assinado', status='aprovado', ciclo=1,
			arquivo_assinado=_fake_file(), enviado_por=admin_user, documento_gerado=doc_contrato,
		)
		client.force_login(admin_user)
		url = reverse('reservadoDetalhes', kwargs={'reserva_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.context['pre_venda_liberada'] is True

	def test_acesso_bloqueado_sem_permissao(self, client, corretor_user, venda):
		"""Usuário sem ownership vê permissaoVenda.html (acesso restrito), não os detalhes."""
		client.force_login(corretor_user)
		url = reverse('reservadoDetalhes', kwargs={'reserva_uuid': venda.lote.uuid})
		response = client.get(url)
		assert response.status_code == 200
		assert any('permissaoVenda' in t.name for t in response.templates)

	def test_venda_documentos_excluem_arquivados(
		self, client, admin_user, venda, settings, tmp_path
	):
		"""venda_documentos no contexto não inclui docs com status=arquivado."""
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		VendaDocumento.objects.create(
			venda=venda, tipo='outros', status='arquivado', ciclo=1,
			arquivo_assinado=_fake_file('doc_arq.pdf'), enviado_por=admin_user,
		)
		VendaDocumento.objects.create(
			venda=venda, tipo='outros', status='enviado', ciclo=2,
			arquivo_assinado=_fake_file('doc_env.pdf'), enviado_por=admin_user,
		)
		client.force_login(admin_user)
		url = reverse('reservadoDetalhes', kwargs={'reserva_uuid': venda.lote.uuid})
		response = client.get(url)
		docs = list(response.context['venda_documentos'])
		assert len(docs) == 1
		assert docs[0].status == 'enviado'

	def test_historico_por_ciclo_agrupa_arquivados(
		self, client, admin_user, venda, settings, tmp_path
	):
		"""historico_por_ciclo agrupa docs arquivados por número de ciclo."""
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		VendaDocumento.objects.create(
			venda=venda, tipo='outros', status='arquivado', ciclo=1,
			arquivo_assinado=_fake_file('hist.pdf'), enviado_por=admin_user,
		)
		client.force_login(admin_user)
		url = reverse('reservadoDetalhes', kwargs={'reserva_uuid': venda.lote.uuid})
		response = client.get(url)
		historico = response.context['historico_por_ciclo']
		assert len(historico) == 1
		assert historico[0]['ciclo'] == 1


# ─── PreVendaDetalheView ──────────────────────────────────────────────────────

class TestPreVendaDetalheView:
	"""
	URL: /vendas/pre-venda/<venda_uuid>/
	Proteção: LoginRequiredMixin + tipo_usuario == 'ADMINISTRADOR'.
	"""

	def test_get_200_admin(self, client, admin_user, venda_pre_venda):
		client.force_login(admin_user)
		url = reverse('pre-venda-detalhe', kwargs={'venda_uuid': venda_pre_venda.uuid})
		response = client.get(url)
		assert response.status_code == 200

	def test_nao_admin_redirecionado(self, client, corretor_user, venda_pre_venda):
		client.force_login(corretor_user)
		url = reverse('pre-venda-detalhe', kwargs={'venda_uuid': venda_pre_venda.uuid})
		response = client.get(url)
		assert response.status_code == 302

	def test_anonimo_redirecionado(self, client, venda_pre_venda):
		url = reverse('pre-venda-detalhe', kwargs={'venda_uuid': venda_pre_venda.uuid})
		response = client.get(url)
		assert response.status_code == 302

	def test_checklist_pf_cnh_dispensa_rg_cpf(
		self, client, admin_user, venda_pre_venda, settings, tmp_path
	):
		"""CNH disponível → checklist não deve incluir RG nem CPF."""
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		ClienteDocumento.objects.create(
			cliente=venda_pre_venda.cliente,
			tipo='CNH',
			arquivo=_fake_file('cnh.pdf'),
			status='disponivel',
		)
		client.force_login(admin_user)
		url = reverse('pre-venda-detalhe', kwargs={'venda_uuid': venda_pre_venda.uuid})
		response = client.get(url)
		tipos = [item['tipo'] for item in response.context['checklist_cliente']]
		assert 'CNH' in tipos
		assert 'RG' not in tipos
		assert 'CPF' not in tipos

	def test_checklist_pf_solteiro_dispensa_estado_civil(
		self, client, admin_user, venda_pre_venda
	):
		"""cliente_pf tem estado_civil='solteiro' — COMPROVANTE_ESTADO_CIVIL não entra."""
		client.force_login(admin_user)
		url = reverse('pre-venda-detalhe', kwargs={'venda_uuid': venda_pre_venda.uuid})
		response = client.get(url)
		tipos = [item['tipo'] for item in response.context['checklist_cliente']]
		assert 'COMPROVANTE_ESTADO_CIVIL' not in tipos

	def test_checklist_pf_casado_inclui_estado_civil(
		self, client, admin_user, lote, cliente_pf_casado
	):
		"""PF casado → COMPROVANTE_ESTADO_CIVIL entra no checklist."""
		venda_casado = RegisterVenda.objects.create(
			lote=lote,
			cliente=cliente_pf_casado,
			corretor=admin_user,
			tipo_venda='PRE-VENDA',
			is_ativo=True,
		)
		client.force_login(admin_user)
		url = reverse('pre-venda-detalhe', kwargs={'venda_uuid': venda_casado.uuid})
		response = client.get(url)
		tipos = [item['tipo'] for item in response.context['checklist_cliente']]
		assert 'COMPROVANTE_ESTADO_CIVIL' in tipos

	def test_checklist_pj_documentos_obrigatorios(
		self, client, admin_user, lote, cliente_pj
	):
		"""PJ (14 dígitos) → CNPJ, CONTRATO_SOCIAL, RG_CPF_ADMINISTRADOR obrigatórios."""
		venda_pj = RegisterVenda.objects.create(
			lote=lote,
			cliente=cliente_pj,
			corretor=admin_user,
			tipo_venda='PRE-VENDA',
			is_ativo=True,
		)
		client.force_login(admin_user)
		url = reverse('pre-venda-detalhe', kwargs={'venda_uuid': venda_pj.uuid})
		response = client.get(url)
		assert response.status_code == 200
		tipos = [item['tipo'] for item in response.context['checklist_cliente']]
		assert 'CNPJ' in tipos
		assert 'CONTRATO_SOCIAL' in tipos
		assert 'RG_CPF_ADMINISTRADOR' in tipos

	def test_proposta_aprovada_preenchida_no_contexto(
		self, client, admin_user, venda_pre_venda
	):
		"""proposta_aprovada no contexto aponta para o VendaDocumento correto."""
		VendaDocumento.objects.create(
			venda=venda_pre_venda,
			tipo='proposta_assinada',
			status='aprovado',
			arquivo_assinado='fake/proposta.pdf',
			enviado_por=admin_user,
		)
		client.force_login(admin_user)
		url = reverse('pre-venda-detalhe', kwargs={'venda_uuid': venda_pre_venda.uuid})
		response = client.get(url)
		assert response.context['proposta_aprovada'] is not None
		assert response.context['contrato_aprovado'] is None

	def test_contrato_aprovado_preenchido_no_contexto(
		self, client, admin_user, venda_pre_venda
	):
		"""contrato_aprovado no contexto aponta para o VendaDocumento correto."""
		VendaDocumento.objects.create(
			venda=venda_pre_venda,
			tipo='contrato_assinado',
			status='aprovado',
			arquivo_assinado='fake/contrato.pdf',
			enviado_por=admin_user,
		)
		client.force_login(admin_user)
		url = reverse('pre-venda-detalhe', kwargs={'venda_uuid': venda_pre_venda.uuid})
		response = client.get(url)
		assert response.context['contrato_aprovado'] is not None
		assert response.context['proposta_aprovada'] is None


# ─── VendaDocumentoUploadView ─────────────────────────────────────────────────

class TestVendaDocumentoUploadView:
	"""
	URL: /vendas/venda/<venda_uuid>/documento/upload/  (POST only)
	Proteção: LoginRequiredMixin + tipo_usuario in ('CORRETOR', 'ADMINISTRADOR').
	CORRETOR só pode fazer upload na própria venda.
	"""

	def test_anonimo_redirecionado(self, client, venda):
		url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
		response = client.post(url, {'tipo': 'outros'})
		assert response.status_code == 302

	def test_proprietario_retorna_404(self, client, venda):
		prop = User.objects.create_user(
			username='prop_upload', password='senha123', tipo_usuario='PROPRIETARIO'
		)
		client.force_login(prop)
		url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
		response = client.post(url, {'tipo': 'outros'})
		assert response.status_code == 404

	def test_corretor_sem_ownership_retorna_404(
		self, client, corretor_user, venda
	):
		"""Corretor que não é o corretor da venda recebe 404."""
		client.force_login(corretor_user)
		url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
		response = client.post(url, {'tipo': 'outros'})
		assert response.status_code == 404

	def test_admin_upload_cria_documento(
		self, client, admin_user, venda, settings, tmp_path
	):
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		client.force_login(admin_user)
		url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
		response = client.post(url, {
			'tipo': 'proposta_assinada',
			'arquivo_assinado': _fake_file(),
		})
		assert response.status_code == 302
		assert VendaDocumento.objects.filter(venda=venda, tipo='proposta_assinada').exists()

	def test_upload_sem_arquivo_nao_cria_documento(self, client, admin_user, venda):
		"""POST sem arquivo → redirect com mensagem de erro, sem criar registro."""
		client.force_login(admin_user)
		url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
		response = client.post(url, {'tipo': 'outros'})
		assert response.status_code == 302
		assert not VendaDocumento.objects.filter(venda=venda).exists()

	def test_upload_ciclo_1_quando_sem_docs(
		self, client, admin_user, venda, settings, tmp_path
	):
		"""Primeiro upload usa ciclo=1."""
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		client.force_login(admin_user)
		url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
		client.post(url, {
			'tipo': 'outros',
			'arquivo_assinado': _fake_file(),
		})
		doc = VendaDocumento.objects.get(venda=venda)
		assert doc.ciclo == 1

	def test_upload_reutiliza_ciclo_maximo_existente(
		self, client, admin_user, venda, settings, tmp_path
	):
		"""Novo upload usa mesmo ciclo do doc ativo mais recente."""
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		VendaDocumento.objects.create(
			venda=venda, tipo='outros', status='enviado', ciclo=3,
			arquivo_assinado='fake/old.pdf', enviado_por=admin_user,
		)
		client.force_login(admin_user)
		url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
		client.post(url, {
			'tipo': 'outros',
			'arquivo_assinado': _fake_file('new.pdf'),
		})
		novo = VendaDocumento.objects.order_by('-id').first()
		assert novo.ciclo == 3

	def test_corretor_owner_pode_fazer_upload(
		self, client, venda, settings, tmp_path
	):
		"""Corretor que É o corretor da venda pode fazer upload."""
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		corretor_dono = User.objects.create_user(
			username='corretor_dono', password='senha123', tipo_usuario='CORRETOR'
		)
		venda.corretor = corretor_dono
		venda.save(update_fields=['corretor'])
		client.force_login(corretor_dono)
		url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
		response = client.post(url, {
			'tipo': 'outros',
			'arquivo_assinado': _fake_file(),
		})
		assert response.status_code == 302
		assert VendaDocumento.objects.filter(venda=venda).exists()

	def test_upload_vincula_documento_gerado_finalizado_mais_recente(
		self, client, admin_user, venda, settings, tmp_path
	):
		"""Upload de 'proposta_assinada' encontra e vincula o DocumentoGerado FINALIZADO mais recente."""
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
		modelo = ModeloDocumento.objects.create(
			titulo='Proposta', tipo='proposta', conteudo_html='<p>x</p>',
			eh_global=True, criado_por=admin_user,
		)
		doc_gerado = DocumentoGerado.objects.create(
			modelo=modelo, modelo_versao_snapshot=1, venda=venda, titulo='Proposta',
			conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
		)
		client.force_login(admin_user)
		url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
		client.post(url, {'tipo': 'proposta_assinada', 'arquivo_assinado': _fake_file()})
		novo = VendaDocumento.objects.get(venda=venda, tipo='proposta_assinada')
		assert novo.documento_gerado_id == doc_gerado.id

	def test_upload_sem_documento_gerado_finalizado_deixa_campo_nulo(
		self, client, admin_user, venda, settings, tmp_path
	):
		"""Upload sem DocumentoGerado FINALIZADO deixa documento_gerado como NULL."""
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		client.force_login(admin_user)
		url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
		client.post(url, {'tipo': 'proposta_assinada', 'arquivo_assinado': _fake_file()})
		novo = VendaDocumento.objects.get(venda=venda, tipo='proposta_assinada')
		assert novo.documento_gerado_id is None

	def test_upload_vincula_o_mais_recente_entre_multiplos_finalizados(
		self, client, admin_user, venda, settings, tmp_path
	):
		"""Com 2+ FINALIZADOS do mesmo tipo, o upload liga ao de criado_em mais recente,
		não ao primeiro criado nem por acidente de ordem de query."""
		from django.utils import timezone
		from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		modelo = ModeloDocumento.objects.create(
			titulo='Proposta', tipo='proposta', conteudo_html='<p>x</p>',
			eh_global=True, criado_por=admin_user,
		)
		doc_antigo = DocumentoGerado.objects.create(
			modelo=modelo, modelo_versao_snapshot=1, venda=venda, titulo='Proposta v1',
			conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
		)
		DocumentoGerado.objects.filter(pk=doc_antigo.pk).update(
			criado_em=timezone.now() - timezone.timedelta(days=1)
		)
		doc_recente = DocumentoGerado.objects.create(
			modelo=modelo, modelo_versao_snapshot=1, venda=venda, titulo='Proposta v2',
			conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
		)
		client.force_login(admin_user)
		url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
		client.post(url, {'tipo': 'proposta_assinada', 'arquivo_assinado': _fake_file()})
		novo = VendaDocumento.objects.get(venda=venda, tipo='proposta_assinada')
		assert novo.documento_gerado_id == doc_recente.id

	def test_upload_com_empate_de_criado_em_resolve_por_id_maior(
		self, client, admin_user, venda, settings, tmp_path
	):
		"""Dois FINALIZADOS com o MESMO criado_em (empate real) — sem desempate por id
		a ordem seria indefinida no banco. Trava o critério: o de id maior (criado por
		último) vence, de forma determinística."""
		from documentos.models import ModeloDocumento, DocumentoGerado, StatusDocumento
		settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
		settings.MEDIA_ROOT = str(tmp_path)
		modelo = ModeloDocumento.objects.create(
			titulo='Proposta', tipo='proposta', conteudo_html='<p>x</p>',
			eh_global=True, criado_por=admin_user,
		)
		doc_a = DocumentoGerado.objects.create(
			modelo=modelo, modelo_versao_snapshot=1, venda=venda, titulo='Proposta A',
			conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
		)
		doc_b = DocumentoGerado.objects.create(
			modelo=modelo, modelo_versao_snapshot=1, venda=venda, titulo='Proposta B',
			conteudo_final_html='<p>x</p>', status=StatusDocumento.FINALIZADO, criado_por=admin_user,
		)
		empate = doc_b.criado_em
		DocumentoGerado.objects.filter(pk__in=[doc_a.pk, doc_b.pk]).update(criado_em=empate)
		assert doc_b.pk > doc_a.pk  # premissa do teste: b tem id maior
		client.force_login(admin_user)
		url = reverse('venda-documento-upload', kwargs={'venda_uuid': venda.uuid})
		client.post(url, {'tipo': 'proposta_assinada', 'arquivo_assinado': _fake_file()})
		novo = VendaDocumento.objects.get(venda=venda, tipo='proposta_assinada')
		assert novo.documento_gerado_id == doc_b.id


# ─── VendaDocumentoAprovarView ────────────────────────────────────────────────

class TestVendaDocumentoAprovarView:
	"""
	URL: /vendas/venda/documento/<pk>/aprovar/  (POST only)
	Proteção: LoginRequiredMixin + tipo_usuario == 'ADMINISTRADOR' (else 404).
	"""

	@pytest.fixture
	def doc_enviado(self, venda, admin_user):
		return VendaDocumento.objects.create(
			venda=venda,
			tipo='proposta_assinada',
			status='enviado',
			ciclo=1,
			arquivo_assinado='fake/doc.pdf',
			enviado_por=admin_user,
		)

	def test_admin_aprova_documento(self, client, admin_user, doc_enviado):
		client.force_login(admin_user)
		url = reverse('venda-documento-aprovar', kwargs={'pk': doc_enviado.pk})
		response = client.post(url)
		assert response.status_code == 302
		doc_enviado.refresh_from_db()
		assert doc_enviado.status == 'aprovado'

	def test_aprovado_por_preenchido(self, client, admin_user, doc_enviado):
		client.force_login(admin_user)
		url = reverse('venda-documento-aprovar', kwargs={'pk': doc_enviado.pk})
		client.post(url)
		doc_enviado.refresh_from_db()
		assert doc_enviado.aprovado_por == admin_user

	def test_aprovado_em_preenchido(self, client, admin_user, doc_enviado):
		client.force_login(admin_user)
		url = reverse('venda-documento-aprovar', kwargs={'pk': doc_enviado.pk})
		client.post(url)
		doc_enviado.refresh_from_db()
		assert doc_enviado.aprovado_em is not None

	def test_nao_admin_retorna_404(self, client, corretor_user, doc_enviado):
		client.force_login(corretor_user)
		url = reverse('venda-documento-aprovar', kwargs={'pk': doc_enviado.pk})
		response = client.post(url)
		assert response.status_code == 404

	def test_anonimo_redirecionado(self, client, doc_enviado):
		url = reverse('venda-documento-aprovar', kwargs={'pk': doc_enviado.pk})
		response = client.post(url)
		assert response.status_code == 302

	def test_redirect_para_reservado_detalhes(self, client, admin_user, doc_enviado):
		client.force_login(admin_user)
		url = reverse('venda-documento-aprovar', kwargs={'pk': doc_enviado.pk})
		response = client.post(url)
		expected = reverse(
			'reservadoDetalhes',
			kwargs={'reserva_uuid': doc_enviado.venda.lote.uuid},
		)
		assert response.url == expected


# ─── VendaDocumentoRejeitarView ───────────────────────────────────────────────

class TestVendaDocumentoRejeitarView:
	"""
	URL: /vendas/venda/documento/<pk>/rejeitar/  (POST only)
	Proteção: LoginRequiredMixin + tipo_usuario == 'ADMINISTRADOR' (else 404).
	"""

	@pytest.fixture
	def doc_enviado(self, venda, admin_user):
		return VendaDocumento.objects.create(
			venda=venda,
			tipo='proposta_assinada',
			status='enviado',
			ciclo=1,
			arquivo_assinado='fake/doc.pdf',
			enviado_por=admin_user,
		)

	def test_admin_rejeita_documento(self, client, admin_user, doc_enviado):
		client.force_login(admin_user)
		url = reverse('venda-documento-rejeitar', kwargs={'pk': doc_enviado.pk})
		response = client.post(url)
		assert response.status_code == 302
		doc_enviado.refresh_from_db()
		assert doc_enviado.status == 'rejeitado'

	def test_nao_admin_retorna_404(self, client, corretor_user, doc_enviado):
		client.force_login(corretor_user)
		url = reverse('venda-documento-rejeitar', kwargs={'pk': doc_enviado.pk})
		response = client.post(url)
		assert response.status_code == 404

	def test_anonimo_redirecionado(self, client, doc_enviado):
		url = reverse('venda-documento-rejeitar', kwargs={'pk': doc_enviado.pk})
		response = client.post(url)
		assert response.status_code == 302

	def test_rejeitar_nao_altera_aprovado_por(self, client, admin_user, doc_enviado):
		"""Rejeitar não deve setar aprovado_por."""
		client.force_login(admin_user)
		url = reverse('venda-documento-rejeitar', kwargs={'pk': doc_enviado.pk})
		client.post(url)
		doc_enviado.refresh_from_db()
		assert doc_enviado.aprovado_por is None

	def test_redirect_para_reservado_detalhes(self, client, admin_user, doc_enviado):
		client.force_login(admin_user)
		url = reverse('venda-documento-rejeitar', kwargs={'pk': doc_enviado.pk})
		response = client.post(url)
		expected = reverse(
			'reservadoDetalhes',
			kwargs={'reserva_uuid': doc_enviado.venda.lote.uuid},
		)
		assert response.url == expected
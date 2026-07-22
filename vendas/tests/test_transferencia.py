from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.urls import reverse

from clientes.models import Cliente, ClienteDocumento
from vendas.models import HistoricoTitularidade, RegisterVenda, TransferenciaTitularidade
from vendas.services import checklist_documentos_cliente, validar_documentos_titular_novo


def _fake_file(name='termo.pdf', content=b'%PDF-1.4 fake', content_type='application/pdf'):
	return SimpleUploadedFile(name, content, content_type=content_type)


@pytest.fixture
def cliente_novo(db):
	return Cliente.objects.create(
		name='Cliente Novo Titular', documento='22222222222',
		email='novo@test.com', estado_civil='solteiro',
	)


@pytest.fixture
def checklist_completo_para():
	def _make(cliente):
		ClienteDocumento.objects.create(
			cliente=cliente, tipo='CNH', arquivo='fake/cnh.pdf', status='disponivel',
		)
		ClienteDocumento.objects.create(
			cliente=cliente, tipo='COMPROVANTE_RESIDENCIA',
			arquivo='fake/comp.pdf', status='disponivel',
		)
	return _make


@pytest.fixture
def transferencia(db, venda, cliente_novo, admin_user):
	return TransferenciaTitularidade.objects.create(
		venda=venda,
		cliente_anterior=venda.cliente,
		cliente_novo=cliente_novo,
		iniciado_por=admin_user,
	)


@pytest.fixture
def local_storage(settings, tmp_path):
	settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
	settings.MEDIA_ROOT = str(tmp_path)


# ─── IniciarTransferenciaView ──────────────────────────────────────────────

class TestIniciarTransferenciaView:

	def test_get_200_admin_exibe_titular_atual(self, client, admin_user, venda):
		client.force_login(admin_user)
		url = reverse('transferencia-iniciar', kwargs={'venda_uuid': venda.uuid})
		response = client.get(url)
		assert response.status_code == 200
		assert response.context['cliente_anterior'] == venda.cliente

	def test_post_admin_cria_transferencia(self, client, admin_user, venda):
		client.force_login(admin_user)
		url = reverse('transferencia-iniciar', kwargs={'venda_uuid': venda.uuid})
		response = client.post(url)

		assert TransferenciaTitularidade.objects.count() == 1
		transferencia = TransferenciaTitularidade.objects.first()
		assert transferencia.venda == venda
		assert transferencia.cliente_anterior == venda.cliente
		assert transferencia.status == 'PRE_TRANSFERENCIA'

		venda.refresh_from_db()
		assert venda.status_transferencia == 'PRE_TRANSFERENCIA'
		assert response.status_code == 302
		assert response.url == reverse('transferencia-detalhe', kwargs={'transferencia_uuid': transferencia.uuid})

	def test_post_bloqueado_transferencia_ja_ativa(self, client, admin_user, venda, transferencia):
		client.force_login(admin_user)
		url = reverse('transferencia-iniciar', kwargs={'venda_uuid': venda.uuid})
		client.post(url)
		assert TransferenciaTitularidade.objects.count() == 1

	def test_post_bloqueado_usuario_nao_admin(self, client, corretor_user, venda):
		client.force_login(corretor_user)
		url = reverse('transferencia-iniciar', kwargs={'venda_uuid': venda.uuid})
		client.post(url)
		assert TransferenciaTitularidade.objects.count() == 0

	def test_post_bloqueado_venda_sem_cliente(self, client, admin_user, venda):
		venda.cliente = None
		venda.save(update_fields=['cliente'])
		client.force_login(admin_user)
		url = reverse('transferencia-iniciar', kwargs={'venda_uuid': venda.uuid})
		client.post(url)
		assert TransferenciaTitularidade.objects.count() == 0


# ─── DetalheTransferenciaView ──────────────────────────────────────────────

class TestDetalheTransferenciaView:

	def test_get_exibe_checklist_quando_cliente_novo_definido(self, client, admin_user, transferencia):
		client.force_login(admin_user)
		url = reverse('transferencia-detalhe', kwargs={'transferencia_uuid': transferencia.uuid})
		response = client.get(url)
		assert response.status_code == 200
		assert response.context['checklist_titular_novo'] != []
		assert response.context['checklist_completo'] is False

	def test_get_com_novo_cliente_id_seta_cliente_novo(self, client, admin_user, venda, cliente_novo):
		transferencia_sem_novo = TransferenciaTitularidade.objects.create(
			venda=venda, cliente_anterior=venda.cliente, iniciado_por=admin_user,
		)
		client.force_login(admin_user)
		url = reverse('transferencia-detalhe', kwargs={'transferencia_uuid': transferencia_sem_novo.uuid})
		response = client.get(url, {'novo_cliente_id': str(cliente_novo.uuid)})
		assert response.status_code == 200
		transferencia_sem_novo.refresh_from_db()
		assert transferencia_sem_novo.cliente_novo == cliente_novo

	def test_pode_efetivar_false_sem_cliente_novo(self, client, admin_user, venda):
		transferencia_sem_novo = TransferenciaTitularidade.objects.create(
			venda=venda, cliente_anterior=venda.cliente, iniciado_por=admin_user,
		)
		client.force_login(admin_user)
		url = reverse('transferencia-detalhe', kwargs={'transferencia_uuid': transferencia_sem_novo.uuid})
		response = client.get(url)
		assert response.context['pode_efetivar'] is False

	def test_pode_efetivar_false_checklist_incompleto(self, client, admin_user, transferencia):
		client.force_login(admin_user)
		url = reverse('transferencia-detalhe', kwargs={'transferencia_uuid': transferencia.uuid})
		response = client.get(url)
		assert response.context['pode_efetivar'] is False

	def test_pode_efetivar_false_sem_arquivo_termo(
		self, client, admin_user, transferencia, checklist_completo_para,
	):
		checklist_completo_para(transferencia.cliente_novo)
		client.force_login(admin_user)
		url = reverse('transferencia-detalhe', kwargs={'transferencia_uuid': transferencia.uuid})
		response = client.get(url)
		assert response.context['checklist_completo'] is True
		assert response.context['pode_efetivar'] is False

	def test_pode_efetivar_false_sem_certidao_iptu(
		self, client, admin_user, transferencia, checklist_completo_para, local_storage,
	):
		checklist_completo_para(transferencia.cliente_novo)
		transferencia.arquivo_termo_assinado = _fake_file()
		transferencia.save(update_fields=['arquivo_termo_assinado'])

		client.force_login(admin_user)
		url = reverse('transferencia-detalhe', kwargs={'transferencia_uuid': transferencia.uuid})
		response = client.get(url)
		assert response.context['pode_efetivar'] is False

	def test_pode_efetivar_true_todas_condicoes(
		self, client, admin_user, transferencia, checklist_completo_para, local_storage,
	):
		checklist_completo_para(transferencia.cliente_novo)
		transferencia.arquivo_termo_assinado = _fake_file()
		transferencia.certidao_negativa_iptu = _fake_file(name='certidao.pdf')
		transferencia.save(update_fields=['arquivo_termo_assinado', 'certidao_negativa_iptu'])

		client.force_login(admin_user)
		url = reverse('transferencia-detalhe', kwargs={'transferencia_uuid': transferencia.uuid})
		response = client.get(url)
		assert response.context['pode_efetivar'] is True


# ─── EfetivarTransferenciaView ─────────────────────────────────────────────

class TestEfetivarTransferenciaView:

	@pytest.fixture
	def transferencia_pronta(self, transferencia, checklist_completo_para, local_storage):
		checklist_completo_para(transferencia.cliente_novo)
		transferencia.arquivo_termo_assinado = _fake_file()
		transferencia.certidao_negativa_iptu = _fake_file(name='certidao.pdf')
		transferencia.save(update_fields=['arquivo_termo_assinado', 'certidao_negativa_iptu'])
		HistoricoTitularidade.objects.create(
			venda=transferencia.venda, cliente=transferencia.cliente_anterior,
			dt_inicio=date(2020, 1, 1), dt_fim=None,
		)
		return transferencia

	def test_sucesso_efetiva_transferencia(self, client, admin_user, transferencia_pronta):
		venda = transferencia_pronta.venda
		cliente_novo = transferencia_pronta.cliente_novo
		cliente_anterior = transferencia_pronta.cliente_anterior

		client.force_login(admin_user)
		url = reverse('transferencia-efetivar', kwargs={'transferencia_uuid': transferencia_pronta.uuid})
		client.post(url)

		venda.refresh_from_db()
		transferencia_pronta.refresh_from_db()
		assert venda.cliente == cliente_novo
		assert venda.status_transferencia == 'TRANSFERENCIA_CONCLUIDA'
		assert transferencia_pronta.status == 'CONCLUIDA'
		assert transferencia_pronta.efetivado_por == admin_user
		assert transferencia_pronta.efetivado_em is not None

		historico_antigo = HistoricoTitularidade.objects.get(venda=venda, cliente=cliente_anterior)
		assert historico_antigo.dt_fim == date.today()

		historico_novo = HistoricoTitularidade.objects.get(venda=venda, cliente=cliente_novo)
		assert historico_novo.dt_fim is None
		assert historico_novo.transferencia_origem == transferencia_pronta

	def test_bloqueado_status_diferente_de_pre_transferencia(self, client, admin_user, transferencia_pronta):
		transferencia_pronta.status = 'CANCELADA'
		transferencia_pronta.save(update_fields=['status'])
		venda = transferencia_pronta.venda
		cliente_anterior_original = venda.cliente

		client.force_login(admin_user)
		url = reverse('transferencia-efetivar', kwargs={'transferencia_uuid': transferencia_pronta.uuid})
		client.post(url)

		venda.refresh_from_db()
		assert venda.cliente == cliente_anterior_original
		assert venda.status_transferencia != 'TRANSFERENCIA_CONCLUIDA'

	def test_bloqueado_sem_cliente_novo(self, client, admin_user, venda, checklist_completo_para, local_storage):
		transferencia_sem_novo = TransferenciaTitularidade.objects.create(
			venda=venda, cliente_anterior=venda.cliente, iniciado_por=admin_user,
			arquivo_termo_assinado=_fake_file(),
		)
		client.force_login(admin_user)
		url = reverse('transferencia-efetivar', kwargs={'transferencia_uuid': transferencia_sem_novo.uuid})
		client.post(url)

		venda.refresh_from_db()
		transferencia_sem_novo.refresh_from_db()
		assert transferencia_sem_novo.status == 'PRE_TRANSFERENCIA'
		assert venda.status_transferencia != 'TRANSFERENCIA_CONCLUIDA'

	def test_bloqueado_checklist_incompleto(self, client, admin_user, transferencia, local_storage):
		transferencia.arquivo_termo_assinado = _fake_file()
		transferencia.save(update_fields=['arquivo_termo_assinado'])

		client.force_login(admin_user)
		url = reverse('transferencia-efetivar', kwargs={'transferencia_uuid': transferencia.uuid})
		client.post(url)

		venda = transferencia.venda
		venda.refresh_from_db()
		transferencia.refresh_from_db()
		assert transferencia.status == 'PRE_TRANSFERENCIA'
		assert venda.status_transferencia != 'TRANSFERENCIA_CONCLUIDA'

	def test_bloqueado_sem_arquivo_termo(self, client, admin_user, transferencia, checklist_completo_para):
		checklist_completo_para(transferencia.cliente_novo)

		client.force_login(admin_user)
		url = reverse('transferencia-efetivar', kwargs={'transferencia_uuid': transferencia.uuid})
		client.post(url)

		venda = transferencia.venda
		venda.refresh_from_db()
		transferencia.refresh_from_db()
		assert transferencia.status == 'PRE_TRANSFERENCIA'
		assert venda.status_transferencia != 'TRANSFERENCIA_CONCLUIDA'

	def test_bloqueado_sem_certidao_iptu(
		self, client, admin_user, transferencia, checklist_completo_para, local_storage,
	):
		checklist_completo_para(transferencia.cliente_novo)
		transferencia.arquivo_termo_assinado = _fake_file()
		transferencia.save(update_fields=['arquivo_termo_assinado'])

		client.force_login(admin_user)
		url = reverse('transferencia-efetivar', kwargs={'transferencia_uuid': transferencia.uuid})
		client.post(url)

		venda = transferencia.venda
		venda.refresh_from_db()
		transferencia.refresh_from_db()
		assert transferencia.status == 'PRE_TRANSFERENCIA'
		assert venda.status_transferencia != 'TRANSFERENCIA_CONCLUIDA'

	def test_atomicidade_falha_nao_persiste_parcial(
		self, client, admin_user, transferencia_pronta, monkeypatch,
	):
		venda = transferencia_pronta.venda
		cliente_anterior = transferencia_pronta.cliente_anterior

		def _raise_save(self, *args, **kwargs):
			raise RuntimeError('falha simulada')

		monkeypatch.setattr(TransferenciaTitularidade, 'save', _raise_save)

		client.force_login(admin_user)
		url = reverse('transferencia-efetivar', kwargs={'transferencia_uuid': transferencia_pronta.uuid})
		with pytest.raises(RuntimeError):
			client.post(url)

		venda.refresh_from_db()
		assert venda.cliente == cliente_anterior
		assert venda.status_transferencia != 'TRANSFERENCIA_CONCLUIDA'

		historico_novo_existe = HistoricoTitularidade.objects.filter(
			venda=venda, cliente=transferencia_pronta.cliente_novo,
		).exists()
		assert historico_novo_existe is False


# ─── CancelarTransferenciaView ─────────────────────────────────────────────

class TestCancelarTransferenciaView:

	def test_sucesso_cancela_transferencia(self, client, admin_user, transferencia):
		venda = transferencia.venda
		venda.status_transferencia = 'PRE_TRANSFERENCIA'
		venda.save(update_fields=['status_transferencia'])
		cliente_original = venda.cliente

		client.force_login(admin_user)
		url = reverse('transferencia-cancelar', kwargs={'transferencia_uuid': transferencia.uuid})
		client.post(url)

		transferencia.refresh_from_db()
		venda.refresh_from_db()
		assert transferencia.status == 'CANCELADA'
		assert venda.status_transferencia is None
		assert venda.cliente == cliente_original

	def test_bloqueado_status_diferente_de_pre_transferencia(self, client, admin_user, transferencia):
		transferencia.status = 'CONCLUIDA'
		transferencia.save(update_fields=['status'])

		client.force_login(admin_user)
		url = reverse('transferencia-cancelar', kwargs={'transferencia_uuid': transferencia.uuid})
		client.post(url)

		transferencia.refresh_from_db()
		assert transferencia.status == 'CONCLUIDA'


# ─── UploadTermoAssinadoView ────────────────────────────────────────────────

class TestUploadTermoAssinadoView:

	def test_upload_valido_salva_arquivo(self, client, admin_user, transferencia, local_storage):
		client.force_login(admin_user)
		url = reverse('transferencia-upload-termo', kwargs={'transferencia_uuid': transferencia.uuid})
		client.post(url, {'arquivo_termo_assinado': _fake_file()})

		transferencia.refresh_from_db()
		assert bool(transferencia.arquivo_termo_assinado) is True

	def test_bloqueado_extensao_invalida(self, client, admin_user, transferencia, local_storage):
		client.force_login(admin_user)
		url = reverse('transferencia-upload-termo', kwargs={'transferencia_uuid': transferencia.uuid})
		arquivo = _fake_file(name='termo.txt', content=b'texto puro', content_type='text/plain')
		client.post(url, {'arquivo_termo_assinado': arquivo})

		transferencia.refresh_from_db()
		assert bool(transferencia.arquivo_termo_assinado) is False

	def test_bloqueado_arquivo_maior_que_10mb(self, client, admin_user, transferencia, local_storage):
		client.force_login(admin_user)
		url = reverse('transferencia-upload-termo', kwargs={'transferencia_uuid': transferencia.uuid})
		arquivo_grande = _fake_file(content=b'x' * (10 * 1024 * 1024 + 1))
		client.post(url, {'arquivo_termo_assinado': arquivo_grande})

		transferencia.refresh_from_db()
		assert bool(transferencia.arquivo_termo_assinado) is False

	def test_bloqueado_transferencia_nao_pendente(self, client, admin_user, transferencia, local_storage):
		transferencia.status = 'CONCLUIDA'
		transferencia.save(update_fields=['status'])

		client.force_login(admin_user)
		url = reverse('transferencia-upload-termo', kwargs={'transferencia_uuid': transferencia.uuid})
		client.post(url, {'arquivo_termo_assinado': _fake_file()})

		transferencia.refresh_from_db()
		assert bool(transferencia.arquivo_termo_assinado) is False


# ─── UploadCertidaoIptuView ─────────────────────────────────────────────────

class TestUploadCertidaoIptuView:

	def test_upload_valido_salva_arquivo(self, client, admin_user, transferencia, local_storage):
		client.force_login(admin_user)
		url = reverse('transferencia-upload-certidao-iptu', kwargs={'transferencia_uuid': transferencia.uuid})
		client.post(url, {'certidao_negativa_iptu': _fake_file(name='certidao.pdf')})

		transferencia.refresh_from_db()
		assert bool(transferencia.certidao_negativa_iptu) is True

	def test_upload_substitui_e_remove_arquivo_antigo_do_storage(self, client, admin_user, transferencia, local_storage):
		client.force_login(admin_user)
		url = reverse('transferencia-upload-certidao-iptu', kwargs={'transferencia_uuid': transferencia.uuid})
		client.post(url, {'certidao_negativa_iptu': _fake_file(name='certidao1.pdf')})

		transferencia.refresh_from_db()
		storage = transferencia.certidao_negativa_iptu.storage
		nome_antigo = transferencia.certidao_negativa_iptu.name

		client.post(url, {'certidao_negativa_iptu': _fake_file(name='certidao2.pdf')})

		transferencia.refresh_from_db()
		assert transferencia.certidao_negativa_iptu.name != nome_antigo
		assert storage.exists(nome_antigo) is False

	def test_bloqueado_extensao_invalida(self, client, admin_user, transferencia, local_storage):
		client.force_login(admin_user)
		url = reverse('transferencia-upload-certidao-iptu', kwargs={'transferencia_uuid': transferencia.uuid})
		arquivo = _fake_file(name='certidao.txt', content=b'texto puro', content_type='text/plain')
		client.post(url, {'certidao_negativa_iptu': arquivo})

		transferencia.refresh_from_db()
		assert bool(transferencia.certidao_negativa_iptu) is False

	def test_bloqueado_arquivo_maior_que_10mb(self, client, admin_user, transferencia, local_storage):
		client.force_login(admin_user)
		url = reverse('transferencia-upload-certidao-iptu', kwargs={'transferencia_uuid': transferencia.uuid})
		arquivo_grande = _fake_file(name='certidao.pdf', content=b'x' * (10 * 1024 * 1024 + 1))
		client.post(url, {'certidao_negativa_iptu': arquivo_grande})

		transferencia.refresh_from_db()
		assert bool(transferencia.certidao_negativa_iptu) is False

	def test_bloqueado_transferencia_nao_pendente(self, client, admin_user, transferencia, local_storage):
		transferencia.status = 'CONCLUIDA'
		transferencia.save(update_fields=['status'])

		client.force_login(admin_user)
		url = reverse('transferencia-upload-certidao-iptu', kwargs={'transferencia_uuid': transferencia.uuid})
		client.post(url, {'certidao_negativa_iptu': _fake_file(name='certidao.pdf')})

		transferencia.refresh_from_db()
		assert bool(transferencia.certidao_negativa_iptu) is False


# ─── Constraint de banco ────────────────────────────────────────────────────

class TestConstraintTransferenciaAtivaUnica:

	def test_segunda_transferencia_pre_transferencia_estoura_integrity_error(
		self, db, venda, admin_user,
	):
		TransferenciaTitularidade.objects.create(
			venda=venda, cliente_anterior=venda.cliente, iniciado_por=admin_user,
		)
		with pytest.raises(IntegrityError):
			with transaction.atomic():
				TransferenciaTitularidade.objects.create(
					venda=venda, cliente_anterior=venda.cliente, iniciado_por=admin_user,
				)


# ─── validar_documentos_titular_novo ───────────────────────────────────────

class TestValidarDocumentosTitularNovo:

	def test_paridade_com_checklist_documentos_cliente(self, cliente_novo):
		checklist_a, completo_a = validar_documentos_titular_novo(cliente_novo)
		checklist_b = checklist_documentos_cliente(cliente_novo)
		assert checklist_a == checklist_b
		assert completo_a == all(item['disponivel'] for item in checklist_b)

	def test_completo_true_quando_todos_disponiveis(self, cliente_novo, checklist_completo_para):
		checklist_completo_para(cliente_novo)
		_checklist, completo = validar_documentos_titular_novo(cliente_novo)
		assert completo is True

	def test_completo_false_quando_algum_pendente(self, cliente_novo):
		ClienteDocumento.objects.create(
			cliente=cliente_novo, tipo='CNH', arquivo='fake/cnh.pdf', status='disponivel',
		)
		_checklist, completo = validar_documentos_titular_novo(cliente_novo)
		assert completo is False

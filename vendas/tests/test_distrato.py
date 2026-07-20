import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.urls import reverse

from vendas.models import DistratoVenda


def _fake_file(name='termo.pdf', content=b'%PDF-1.4 fake', content_type='application/pdf'):
	return SimpleUploadedFile(name, content, content_type=content_type)


@pytest.fixture
def local_storage(settings, tmp_path):
	settings.DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
	settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture
def distrato(db, venda, admin_user):
	return DistratoVenda.objects.create(venda=venda, iniciado_por=admin_user)


@pytest.fixture
def distrato_aguardando(distrato):
	distrato.status = 'AGUARDANDO_ASSINATURA'
	distrato.save(update_fields=['status'])
	distrato.venda.status_distrato = 'AGUARDANDO_ASSINATURA'
	distrato.venda.save(update_fields=['status_distrato'])
	return distrato


# ─── IniciarDistratoView ────────────────────────────────────────────────────

class TestIniciarDistratoView:

	def test_post_admin_cria_distrato(self, client, admin_user, venda):
		client.force_login(admin_user)
		url = reverse('iniciar-distrato', kwargs={'venda_uuid': venda.uuid})
		response = client.post(url, {'motivo': 'Cliente desistiu'})

		assert DistratoVenda.objects.count() == 1
		distrato = DistratoVenda.objects.first()
		assert distrato.venda == venda
		assert distrato.status == 'INICIADO'
		assert distrato.motivo == 'Cliente desistiu'
		assert distrato.is_administrativo is False

		venda.refresh_from_db()
		assert venda.status_distrato == 'INICIADO'
		assert response.status_code == 302
		assert response.url == reverse('distrato-detalhe', kwargs={'distrato_uuid': distrato.uuid})

	def test_post_bloqueado_distrato_ja_ativo(self, client, admin_user, venda, distrato):
		client.force_login(admin_user)
		url = reverse('iniciar-distrato', kwargs={'venda_uuid': venda.uuid})
		client.post(url)
		assert DistratoVenda.objects.count() == 1

	def test_post_bloqueado_usuario_nao_admin(self, client, corretor_user, venda):
		client.force_login(corretor_user)
		url = reverse('iniciar-distrato', kwargs={'venda_uuid': venda.uuid})
		client.post(url)
		assert DistratoVenda.objects.count() == 0


# ─── DetalheDistratoView ────────────────────────────────────────────────────

class TestDetalheDistratoView:

	def test_get_200_admin(self, client, admin_user, distrato):
		client.force_login(admin_user)
		url = reverse('distrato-detalhe', kwargs={'distrato_uuid': distrato.uuid})
		response = client.get(url)
		assert response.status_code == 200
		assert response.context['distrato'] == distrato
		assert response.context['pode_concluir'] is False

	def test_pode_concluir_true_com_termo(self, client, admin_user, distrato_aguardando, local_storage):
		distrato_aguardando.termo_assinado = _fake_file()
		distrato_aguardando.save(update_fields=['termo_assinado'])

		client.force_login(admin_user)
		url = reverse('distrato-detalhe', kwargs={'distrato_uuid': distrato_aguardando.uuid})
		response = client.get(url)
		assert response.context['pode_concluir'] is True

	def test_get_bloqueado_usuario_nao_admin(self, client, corretor_user, distrato):
		client.force_login(corretor_user)
		url = reverse('distrato-detalhe', kwargs={'distrato_uuid': distrato.uuid})
		response = client.get(url)
		assert response.status_code == 302


# ─── AvancarParaAssinaturaView ──────────────────────────────────────────────

class TestAvancarParaAssinaturaView:

	def test_sucesso_avanca_status(self, client, admin_user, distrato):
		client.force_login(admin_user)
		url = reverse('distrato-aguardar-assinatura', kwargs={'distrato_uuid': distrato.uuid})
		client.post(url)

		distrato.refresh_from_db()
		distrato.venda.refresh_from_db()
		assert distrato.status == 'AGUARDANDO_ASSINATURA'
		assert distrato.venda.status_distrato == 'AGUARDANDO_ASSINATURA'

	def test_bloqueado_status_diferente_de_iniciado(self, client, admin_user, distrato_aguardando):
		client.force_login(admin_user)
		url = reverse('distrato-aguardar-assinatura', kwargs={'distrato_uuid': distrato_aguardando.uuid})
		client.post(url)
		distrato_aguardando.refresh_from_db()
		assert distrato_aguardando.status == 'AGUARDANDO_ASSINATURA'


# ─── UploadTermoDistratoView ────────────────────────────────────────────────

class TestUploadTermoDistratoView:

	def test_upload_valido_salva_arquivo(self, client, admin_user, distrato_aguardando, local_storage):
		client.force_login(admin_user)
		url = reverse('distrato-upload-termo', kwargs={'distrato_uuid': distrato_aguardando.uuid})
		client.post(url, {'termo_assinado': _fake_file()})

		distrato_aguardando.refresh_from_db()
		assert bool(distrato_aguardando.termo_assinado) is True

	def test_bloqueado_extensao_invalida(self, client, admin_user, distrato_aguardando, local_storage):
		client.force_login(admin_user)
		url = reverse('distrato-upload-termo', kwargs={'distrato_uuid': distrato_aguardando.uuid})
		arquivo = _fake_file(name='termo.txt', content=b'texto puro', content_type='text/plain')
		client.post(url, {'termo_assinado': arquivo})

		distrato_aguardando.refresh_from_db()
		assert bool(distrato_aguardando.termo_assinado) is False

	def test_bloqueado_distrato_nao_aguardando(self, client, admin_user, distrato, local_storage):
		client.force_login(admin_user)
		url = reverse('distrato-upload-termo', kwargs={'distrato_uuid': distrato.uuid})
		client.post(url, {'termo_assinado': _fake_file()})

		distrato.refresh_from_db()
		assert bool(distrato.termo_assinado) is False


# ─── ConcluirDistratoView ───────────────────────────────────────────────────

class TestConcluirDistratoView:

	def test_bloqueado_sem_termo_fluxo_normal(self, client, admin_user, distrato_aguardando):
		client.force_login(admin_user)
		url = reverse('concluir-distrato', kwargs={'distrato_uuid': distrato_aguardando.uuid})
		client.post(url)

		distrato_aguardando.refresh_from_db()
		distrato_aguardando.venda.refresh_from_db()
		assert distrato_aguardando.status == 'AGUARDANDO_ASSINATURA'
		assert distrato_aguardando.venda.tipo_venda != 'DISTRATADA'

	def test_sucesso_conclui_com_termo(self, client, admin_user, distrato_aguardando, local_storage):
		distrato_aguardando.termo_assinado = _fake_file()
		distrato_aguardando.save(update_fields=['termo_assinado'])

		venda = distrato_aguardando.venda
		lote = venda.lote
		lote.situacao = 'VENDIDO'
		lote.save(update_fields=['situacao'])

		client.force_login(admin_user)
		url = reverse('concluir-distrato', kwargs={'distrato_uuid': distrato_aguardando.uuid})
		client.post(url)

		distrato_aguardando.refresh_from_db()
		venda.refresh_from_db()
		lote.refresh_from_db()

		assert distrato_aguardando.status == 'CONCLUIDO'
		assert distrato_aguardando.concluido_por == admin_user
		assert distrato_aguardando.concluido_em is not None
		assert venda.tipo_venda == 'DISTRATADA'
		assert venda.status_distrato == 'CONCLUIDO'
		assert venda.is_ativo is False
		assert lote.situacao == 'DISPONIVEL'

	def test_administrativo_conclui_sem_termo(self, client, admin_user, venda):
		distrato = DistratoVenda.objects.create(
			venda=venda, iniciado_por=admin_user,
			is_administrativo=True, motivo_administrativo='Erro de cadastro',
			status='AGUARDANDO_ASSINATURA',
		)
		client.force_login(admin_user)
		url = reverse('concluir-distrato', kwargs={'distrato_uuid': distrato.uuid})
		client.post(url)

		distrato.refresh_from_db()
		venda.refresh_from_db()
		assert distrato.status == 'CONCLUIDO'
		assert venda.tipo_venda == 'DISTRATADA'


# ─── CancelarDistratoView ───────────────────────────────────────────────────

class TestCancelarDistratoView:

	def test_sucesso_cancela_distrato(self, client, admin_user, distrato):
		venda = distrato.venda
		venda.status_distrato = 'INICIADO'
		venda.save(update_fields=['status_distrato'])

		client.force_login(admin_user)
		url = reverse('cancelar-distrato', kwargs={'distrato_uuid': distrato.uuid})
		client.post(url)

		distrato.refresh_from_db()
		venda.refresh_from_db()
		assert distrato.status == 'CANCELADO'
		assert venda.status_distrato is None

	def test_bloqueado_status_ja_concluido(self, client, admin_user, distrato):
		distrato.status = 'CONCLUIDO'
		distrato.save(update_fields=['status'])

		client.force_login(admin_user)
		url = reverse('cancelar-distrato', kwargs={'distrato_uuid': distrato.uuid})
		client.post(url)

		distrato.refresh_from_db()
		assert distrato.status == 'CONCLUIDO'


# ─── IniciarDistratoAdministrativoView ──────────────────────────────────────

class TestIniciarDistratoAdministrativoView:

	def test_post_admin_cria_distrato_administrativo(self, client, admin_user, venda):
		client.force_login(admin_user)
		url = reverse('iniciar-distrato-administrativo', kwargs={'venda_uuid': venda.uuid})
		response = client.post(url, {'motivo_administrativo': 'Corretor cadastrou lote errado'})

		assert DistratoVenda.objects.count() == 1
		distrato = DistratoVenda.objects.first()
		assert distrato.is_administrativo is True
		assert distrato.motivo_administrativo == 'Corretor cadastrou lote errado'
		assert response.status_code == 302

	def test_bloqueado_sem_motivo(self, client, admin_user, venda):
		client.force_login(admin_user)
		url = reverse('iniciar-distrato-administrativo', kwargs={'venda_uuid': venda.uuid})
		client.post(url, {'motivo_administrativo': ''})
		assert DistratoVenda.objects.count() == 0

	def test_bloqueado_usuario_nao_admin(self, client, corretor_user, venda):
		client.force_login(corretor_user)
		url = reverse('iniciar-distrato-administrativo', kwargs={'venda_uuid': venda.uuid})
		client.post(url, {'motivo_administrativo': 'x'})
		assert DistratoVenda.objects.count() == 0


# ─── Constraint de banco ────────────────────────────────────────────────────

class TestConstraintDistratoAtivoUnico:

	def test_segundo_distrato_ativo_estoura_integrity_error(self, db, venda, admin_user):
		DistratoVenda.objects.create(venda=venda, iniciado_por=admin_user)
		with pytest.raises(IntegrityError):
			with transaction.atomic():
				DistratoVenda.objects.create(venda=venda, iniciado_por=admin_user)

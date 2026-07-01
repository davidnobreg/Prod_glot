import pytest
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

	def test_post_avanca_tipo_venda_para_pre_venda(self, client, admin_user, venda):
		client.force_login(admin_user)
		client.post(reverse('criar-venda', kwargs={'venda_uuid': venda.uuid}))
		venda.refresh_from_db()
		assert venda.tipo_venda == 'PRE-VENDA'

	def test_post_avanca_lote_para_pre_venda(self, client, admin_user, venda):
		client.force_login(admin_user)
		client.post(reverse('criar-venda', kwargs={'venda_uuid': venda.uuid}))
		venda.lote.refresh_from_db()
		assert venda.lote.situacao == 'PRE-VENDA'

	def test_dt_venda_nao_setada_na_criacao(self, client, admin_user, venda):
		client.force_login(admin_user)
		client.post(reverse('criar-venda', kwargs={'venda_uuid': venda.uuid}))
		venda.refresh_from_db()
		assert venda.dt_venda is None

	def test_redirect_para_pre_venda_detalhe(self, client, admin_user, venda):
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


class TestEfetivarVendaView:

	@pytest.fixture
	def proposta_aprovada(self, venda_pre_venda, admin_user):
		return VendaDocumento.objects.create(
			venda=venda_pre_venda,
			tipo='proposta_assinada',
			status='aprovado',
			enviado_por=admin_user,
			arquivo_assinado='fake/proposta.pdf',
		)

	def test_post_seta_venda_vendido(self, client, admin_user, venda_pre_venda, proposta_aprovada):
		client.force_login(admin_user)
		client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		venda_pre_venda.refresh_from_db()
		assert venda_pre_venda.tipo_venda == 'VENDIDO'

	def test_post_seta_lote_vendido(self, client, admin_user, venda_pre_venda, proposta_aprovada):
		client.force_login(admin_user)
		client.post(reverse('efetivar-venda', kwargs={'venda_uuid': venda_pre_venda.uuid}))
		venda_pre_venda.lote.refresh_from_db()
		assert venda_pre_venda.lote.situacao == 'VENDIDO'

	def test_dt_venda_preenchida_apos_efetivar(self, client, admin_user, venda_pre_venda, proposta_aprovada):
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

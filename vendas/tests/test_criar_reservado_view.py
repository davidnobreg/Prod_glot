import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from vendas.models import RegisterVenda


@pytest.mark.django_db
class TestCriarReservadoViewGet:
	"""
	URL: /vendas/insert_reserva/<lote_uuid>/ (kwarg reserva_uuid, mas é o uuid do lote)
	Proteção: has_permission_decorator('criarReservado') — superuser bypassa.
	"""

	def test_get_sem_reserva_existente_muda_lote_em_reserva_para_pre_reserva(self, client, admin_user, lote):
		lote.situacao = 'EM_RESERVA'
		lote.save(update_fields=['situacao'])

		client.force_login(admin_user)
		response = client.get(reverse('reserva-create', kwargs={'reserva_uuid': lote.uuid}))

		lote.refresh_from_db()
		assert response.status_code == 200
		assert lote.situacao == 'PRE-RESERVA'
		assert lote.tempo_reservado is not None

	def test_get_sem_reserva_existente_nao_mexe_situacao_se_nao_for_em_reserva(self, client, admin_user, lote):
		assert lote.situacao == 'DISPONIVEL'

		client.force_login(admin_user)
		client.get(reverse('reserva-create', kwargs={'reserva_uuid': lote.uuid}))

		lote.refresh_from_db()
		assert lote.situacao == 'DISPONIVEL'


@pytest.mark.django_db
class TestCriarReservadoViewPost:

	def test_post_sem_desconto_cria_reserva_como_analise(self, client, admin_user, lote, cliente_pf):
		"""Toda reserva criada é a porta de entrada da venda: sempre ANALISE,
		mesmo sem desconto e sem histórico prévio no lote."""
		client.force_login(admin_user)
		response = client.post(
			reverse('reserva-create', kwargs={'reserva_uuid': lote.uuid}),
			data={
				'cliente': cliente_pf.pk,
				'valor_desconto': 'R$ 0,00',
				'valor_entrada': 'R$ 0,00',
				'valor_sinal': 'R$ 0,00',
				'quantidade_parcelas': 12,
				'reajuste': 'True',
			},
		)

		lote.refresh_from_db()
		venda = RegisterVenda.objects.get(lote=lote)
		assert response.status_code == 302
		assert venda.tipo_venda == 'ANALISE'
		assert venda.is_ativo is True
		assert lote.situacao == 'ANALISE'

	def test_post_com_desconto_cria_reserva_como_analise(self, client, admin_user, lote, cliente_pf):
		client.force_login(admin_user)
		client.post(
			reverse('reserva-create', kwargs={'reserva_uuid': lote.uuid}),
			data={
				'cliente': cliente_pf.pk,
				'valor_desconto': 'R$ 1.000,00',
				'valor_entrada': 'R$ 0,00',
				'valor_sinal': 'R$ 0,00',
				'quantidade_parcelas': 12,
				'reajuste': 'True',
			},
		)

		lote.refresh_from_db()
		venda = RegisterVenda.objects.get(lote=lote)
		assert venda.tipo_venda == 'ANALISE'
		assert lote.situacao == 'ANALISE'

	def test_post_bloqueia_nova_reserva_se_ja_existe_reserva_ativa(self, client, admin_user, lote, cliente_pf, venda):
		"""`venda` fixture já cria uma RegisterVenda tipo_venda='RESERVADO' pro mesmo lote."""
		client.force_login(admin_user)
		response = client.post(
			reverse('reserva-create', kwargs={'reserva_uuid': lote.uuid}),
			data={
				'cliente': cliente_pf.pk,
				'valor_desconto': 'R$ 0,00',
				'valor_entrada': 'R$ 0,00',
				'valor_sinal': 'R$ 0,00',
				'quantidade_parcelas': 12,
				'reajuste': 'True',
			},
			follow=False,
		)

		mensagens = [str(m) for m in get_messages(response.wsgi_request)]
		# nota: mensagem tem mojibake pré-existente ("JÃ¡") em create_views.py:400,
		# fora do escopo desta tarefa (P1.4 só cobriu forms.py) — testa string real.
		assert any('existe uma' in m.lower() and 'venda ativa' in m.lower() for m in mensagens)
		assert RegisterVenda.objects.filter(lote=lote).count() == 1

	def test_post_reserva_apos_cancelamento_vai_para_analise(self, client, admin_user, lote, cliente_pf, venda):
		"""Reserva que reaproveita o registro cancelado anterior (mesmo pk, via
		OneToOne lote-reg_venda) também cai em ANALISE, como qualquer outra."""
		venda.tipo_venda = 'CANCELADA'
		venda.is_ativo = False
		venda.save(update_fields=['tipo_venda', 'is_ativo'])

		client.force_login(admin_user)
		client.post(
			reverse('reserva-create', kwargs={'reserva_uuid': lote.uuid}),
			data={
				'cliente': cliente_pf.pk,
				'valor_desconto': 'R$ 0,00',
				'valor_entrada': 'R$ 0,00',
				'valor_sinal': 'R$ 0,00',
				'quantidade_parcelas': 12,
				'reajuste': 'True',
			},
		)

		venda.refresh_from_db()
		lote.refresh_from_db()
		assert venda.tipo_venda == 'ANALISE'
		assert venda.is_ativo is True
		assert lote.situacao == 'ANALISE'

	def test_post_reserva_apos_nao_aceite_vai_para_analise(self, client, admin_user, lote, cliente_pf, venda):
		"""Mesmo padrão vale pra reaproveitamento de registro NAO_ACEITE."""
		venda.tipo_venda = 'NAO_ACEITE'
		venda.is_ativo = False
		venda.save(update_fields=['tipo_venda', 'is_ativo'])

		client.force_login(admin_user)
		client.post(
			reverse('reserva-create', kwargs={'reserva_uuid': lote.uuid}),
			data={
				'cliente': cliente_pf.pk,
				'valor_desconto': 'R$ 0,00',
				'valor_entrada': 'R$ 0,00',
				'valor_sinal': 'R$ 0,00',
				'quantidade_parcelas': 12,
				'reajuste': 'True',
			},
		)

		venda.refresh_from_db()
		assert venda.tipo_venda == 'ANALISE'
		assert venda.is_ativo is True

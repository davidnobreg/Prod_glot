import pytest
from django.urls import reverse

from accounts.models import User
from empreendimentos.models import Lote
from vendas.models import RegisterVenda


@pytest.fixture
def proprietario_user(db):
	return User.objects.create_user(
		username='proprietario_test',
		password='senha123',
		tipo_usuario='PROPRIETARIO',
	)


@pytest.fixture
def venda_inativa(db, quadra, cliente_pf, admin_user):
	lote = Lote.objects.create(
		lote='L_INATIVO',
		area='100',
		situacao='CANCELADA',
		quadra=quadra,
		valor_metro_quadrado='100',
		telefone='(83) 99999-9999',
		telefone_user='(83) 99999-9999',
	)
	return RegisterVenda.objects.create(
		lote=lote,
		cliente=cliente_pf,
		corretor=admin_user,
		tipo_venda='CANCELADA',
		is_ativo=False,
	)


class TestListaVendaView:

	def test_get_200_admin(self, client, admin_user, venda):
		client.force_login(admin_user)
		response = client.get(reverse('lista-venda'))
		assert response.status_code == 200

	def test_lista_apenas_ativos_por_padrao(self, client, admin_user, venda, venda_inativa):
		"""Venda ativa aparece; inativa não."""
		client.force_login(admin_user)
		response = client.get(reverse('lista-venda'))
		ids = [r.id for r in response.context['reservas']]
		assert venda.id in ids
		assert venda_inativa.id not in ids

	def test_vendas_inativas_nao_aparecem(self, client, admin_user, venda_inativa):
		"""Apenas vendas inativas no banco → listagem vazia."""
		client.force_login(admin_user)
		response = client.get(reverse('lista-venda'))
		ids = [r.id for r in response.context['reservas']]
		assert venda_inativa.id not in ids

	def test_filtro_tipo_venda_retorna_corretos(self, client, admin_user, venda, quadra, cliente_pf):
		"""?tipo_venda=RESERVADO retorna venda RESERVADO, não PRE-VENDA."""
		lote2 = Lote.objects.create(
			lote='L_PRE_VENDA',
			area='100',
			situacao='PRE-VENDA',
			quadra=quadra,
			valor_metro_quadrado='100',
			telefone='(83) 99999-9999',
			telefone_user='(83) 99999-9999',
		)
		venda_pv = RegisterVenda.objects.create(
			lote=lote2,
			cliente=cliente_pf,
			corretor=admin_user,
			tipo_venda='PRE-VENDA',
			is_ativo=True,
		)
		client.force_login(admin_user)
		response = client.get(reverse('lista-venda') + '?tipo_venda=RESERVADO')
		ids = [r.id for r in response.context['reservas']]
		assert venda.id in ids
		assert venda_pv.id not in ids

	def test_filtro_tipo_venda_nao_traz_inativos(self, client, admin_user, venda, venda_inativa):
		"""Bug corrigido: filtro tipo_venda não deve forçar is_ativo=False.

		Antes da correção, ?tipo_venda=RESERVADO filtrava is_ativo=False, trazendo
		vendas inativas e excluindo as ativas.
		"""
		client.force_login(admin_user)
		response = client.get(reverse('lista-venda') + '?tipo_venda=RESERVADO')
		ids = [r.id for r in response.context['reservas']]
		assert venda.id in ids          # ativo deve aparecer
		assert venda_inativa.id not in ids  # inativo não deve aparecer

	def test_paginacao_primeira_pagina(self, client, admin_user, quadra, cliente_pf):
		"""Com 11 vendas ativas, página 1 retorna exatamente 10 itens."""
		for i in range(11):
			lote = Lote.objects.create(
				lote=f'LPAG{i}',
				area='100',
				situacao='RESERVADO',
				quadra=quadra,
				valor_metro_quadrado='100',
				telefone='(83) 99999-9999',
				telefone_user='(83) 99999-9999',
			)
			RegisterVenda.objects.create(
				lote=lote,
				cliente=cliente_pf,
				corretor=admin_user,
				tipo_venda='RESERVADO',
				is_ativo=True,
			)
		client.force_login(admin_user)
		response = client.get(reverse('lista-venda'))
		assert len(response.context['reservas']) == 10

	def test_paginacao_segunda_pagina(self, client, admin_user, quadra, cliente_pf):
		"""Segunda página retorna o item restante."""
		for i in range(11):
			lote = Lote.objects.create(
				lote=f'LPAG2_{i}',
				area='100',
				situacao='RESERVADO',
				quadra=quadra,
				valor_metro_quadrado='100',
				telefone='(83) 99999-9999',
				telefone_user='(83) 99999-9999',
			)
			RegisterVenda.objects.create(
				lote=lote,
				cliente=cliente_pf,
				corretor=admin_user,
				tipo_venda='RESERVADO',
				is_ativo=True,
			)
		client.force_login(admin_user)
		response = client.get(reverse('lista-venda') + '?page=2')
		assert len(response.context['reservas']) == 1

	def test_acesso_bloqueado_sem_permissao(self, client, proprietario_user):
		client.force_login(proprietario_user)
		response = client.get(reverse('lista-venda'))
		assert response.status_code == 403

	def test_anonimo_retorna_403(self, client):
		response = client.get(reverse('lista-venda'))
		assert response.status_code == 403

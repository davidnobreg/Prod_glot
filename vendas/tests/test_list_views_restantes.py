import pytest
from django.urls import reverse

from empreendimentos.models import Lote
from vendas.models import RegisterVenda


@pytest.fixture
def venda_analise(db, quadra, cliente_pf, admin_user):
	lote = Lote.objects.create(
		lote='L_ANALISE',
		area='100',
		situacao='ANALISE',
		quadra=quadra,
		valor_metro_quadrado='100',
		telefone='(83) 99999-9999',
		telefone_user='(83) 99999-9999',
	)
	return RegisterVenda.objects.create(
		lote=lote,
		cliente=cliente_pf,
		corretor=admin_user,
		tipo_venda='ANALISE',
		is_ativo=True,
	)


class TestListarendaRelatorioView:
	"""
	URL: /vendas/listar_venda_relatorio/
	Proteção: has_permission_decorator('listaVendaRelatorio') — superuser bypassa.
	"""

	def test_get_200_admin(self, client, admin_user, venda):
		client.force_login(admin_user)
		response = client.get(reverse('lista-venda-relatorio'))
		assert response.status_code == 200

	def test_lista_traz_todos_independente_de_is_ativo(self, client, admin_user, venda, venda_analise):
		"""Diferente de ListaVendaView, esta é um relatório — sem filtro is_ativo."""
		client.force_login(admin_user)
		response = client.get(reverse('lista-venda-relatorio'))
		ids = [r.id for r in response.context['vendas']]
		assert venda.id in ids
		assert venda_analise.id in ids

	def test_filtro_tipo_venda(self, client, admin_user, venda, venda_analise):
		client.force_login(admin_user)
		response = client.get(reverse('lista-venda-relatorio') + '?tipo_venda=ANALISE')
		ids = [r.id for r in response.context['vendas']]
		assert venda_analise.id in ids
		assert venda.id not in ids

	def test_filtro_registro_busca_por_nome_cliente(self, client, admin_user, venda):
		client.force_login(admin_user)
		response = client.get(reverse('lista-venda-relatorio') + f'?registro={venda.cliente.name}')
		ids = [r.id for r in response.context['vendas']]
		assert venda.id in ids


class TestRelatorioReservaView:
	"""
	URL: /vendas/listar_reserva/
	Proteção: has_permission_decorator('relatorioReserva') — superuser bypassa.
	Queryset fixo: tipo_venda='RESERVADO' e is_ativo=True.
	"""

	def test_get_200_admin(self, client, admin_user, venda):
		client.force_login(admin_user)
		response = client.get(reverse('lista-reserva'))
		assert response.status_code == 200

	def test_lista_apenas_reservado_ativo(self, client, admin_user, venda, venda_analise):
		client.force_login(admin_user)
		response = client.get(reverse('lista-reserva'))
		ids = [r.id for r in response.context['reservas']]
		assert venda.id in ids
		assert venda_analise.id not in ids

	def test_filtro_search_nome(self, client, admin_user, venda):
		client.force_login(admin_user)
		response = client.get(reverse('lista-reserva') + f'?search_nome={venda.cliente.name}')
		ids = [r.id for r in response.context['reservas']]
		assert venda.id in ids


class TestListasAnalisesView:
	"""
	URL: /vendas/listar_analise/
	Proteção: has_permission_decorator('listasAnalises') — superuser bypassa.
	Queryset fixo: tipo_venda='ANALISE'.
	"""

	def test_get_200_admin(self, client, admin_user, venda_analise):
		client.force_login(admin_user)
		response = client.get(reverse('lista-analise'))
		assert response.status_code == 200

	def test_lista_apenas_analise(self, client, admin_user, venda, venda_analise):
		client.force_login(admin_user)
		response = client.get(reverse('lista-analise'))
		ids = [r.id for r in response.context['reservas']]
		assert venda_analise.id in ids
		assert venda.id not in ids

	def test_filtro_por_empreendimento(self, client, admin_user, venda_analise, empreendimento):
		client.force_login(admin_user)
		response = client.get(reverse('lista-analise') + f'?tipo_empreendimento={empreendimento.id}')
		ids = [r.id for r in response.context['reservas']]
		assert venda_analise.id in ids

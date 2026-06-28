import pytest
from accounts.models import User
from empreendimentos.models import Empreendimento, Quadra, Lote
from clientes.models import Cliente
from vendas.models import RegisterVenda, VendaDocumento


@pytest.fixture
def admin_user(db):
	return User.objects.create_user(
		username='admin_test',
		password='senha123',
		tipo_usuario='ADMINISTRADOR',
		is_superuser=True,
	)


@pytest.fixture
def corretor_user(db):
	return User.objects.create_user(
		username='corretor_test',
		password='senha123',
		tipo_usuario='CORRETOR',
	)


@pytest.fixture
def empreendimento(db):
	return Empreendimento.objects.create(
		nome='Empr Teste',
		telefone='(83) 99999-9999',
		tempo_reserva=7,
		quantidade_parcela=60,
		cnpj='00000000000100',
	)


@pytest.fixture
def quadra(db, empreendimento):
	return Quadra.objects.create(namequadra='Q1', empr=empreendimento)


@pytest.fixture
def lote(db, quadra):
	return Lote.objects.create(
		lote='L1',
		area='200',
		situacao='DISPONIVEL',
		quadra=quadra,
		valor_metro_quadrado='100',
		telefone='(83) 99999-9999',
		telefone_user='(83) 99999-9999',
	)


@pytest.fixture
def cliente_pf(db):
	return Cliente.objects.create(
		name='Cliente PF Teste',
		documento='00000000000',
		email='pf@test.com',
		estado_civil='solteiro',
	)


@pytest.fixture
def cliente_pf_casado(db):
	return Cliente.objects.create(
		name='Cliente PF Casado',
		documento='11111111111',
		email='pfcasado@test.com',
		estado_civil='casado',
	)


@pytest.fixture
def cliente_pj(db):
	return Cliente.objects.create(
		name='Cliente PJ Teste',
		documento='00000000000100',
		email='pj@test.com',
	)


@pytest.fixture
def venda(db, lote, cliente_pf, admin_user):
	return RegisterVenda.objects.create(
		lote=lote,
		cliente=cliente_pf,
		corretor=admin_user,
		tipo_venda='RESERVADO',
		is_ativo=True,
	)


@pytest.fixture
def venda_pre_venda(db, lote, cliente_pf, admin_user):
	lote.situacao = 'PRE-VENDA'
	lote.save()
	return RegisterVenda.objects.create(
		lote=lote,
		cliente=cliente_pf,
		corretor=admin_user,
		tipo_venda='PRE-VENDA',
		is_ativo=True,
	)
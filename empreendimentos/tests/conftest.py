import pytest
from accounts.models import User
from clientes.models import Cliente
from empreendimentos.models import Empreendimento, Quadra


@pytest.fixture
def admin_user(db):
	return User.objects.create_user(
		username='admin_test',
		password='senha123',
		tipo_usuario='ADMINISTRADOR',
		is_superuser=True,
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
def cliente_pf(db):
	return Cliente.objects.create(
		name='Cliente PF Teste',
		documento='00000000000',
		email='pf@test.com',
		estado_civil='solteiro',
	)
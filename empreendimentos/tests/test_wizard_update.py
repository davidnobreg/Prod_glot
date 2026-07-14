from django.contrib.auth import get_user_model
from django.test import TestCase

from base.models import Endereco
from empreendimentos import services as empreendimento_services
from empreendimentos.models import Empreendimento

User = get_user_model()


def make_user(username='update_wizard_user'):
	return User.objects.create_user(
		username=username, password='pass123', email=f'{username}@test.com',
		is_superuser=True, is_staff=True,
	)


def make_empreendimento(**kwargs):
	defaults = {
		'nome': 'Empreendimento Real', 'telefone': '(83) 99999-9999',
		'tempo_reserva': 30, 'quantidade_parcela': 60, 'cnpj': '11222333000181',
	}
	defaults.update(kwargs)
	return Empreendimento.objects.create(**defaults)


def make_endereco(**kwargs):
	defaults = {
		'cep': '58000000', 'rua': 'Rua Original', 'numero': '10',
		'complemento': '', 'bairro': 'Centro', 'cidade': 'João Pessoa', 'estado': 'PB',
	}
	defaults.update(kwargs)
	return Endereco.objects.create(**defaults)


class SincronizarEnderecoTest(TestCase):

	def test_origem_none_retorna_destino_sem_alterar(self):
		destino = make_endereco(rua='Fica igual')
		resultado = empreendimento_services.sincronizar_endereco(destino, None)
		self.assertEqual(resultado, destino)
		destino.refresh_from_db()
		self.assertEqual(destino.rua, 'Fica igual')

	def test_destino_none_cria_endereco_novo(self):
		origem = make_endereco(rua='Rua Origem', cidade='Campina Grande')
		resultado = empreendimento_services.sincronizar_endereco(None, origem)
		self.assertIsNotNone(resultado.pk)
		self.assertNotEqual(resultado.pk, origem.pk)
		self.assertEqual(resultado.rua, 'Rua Origem')
		self.assertEqual(resultado.cidade, 'Campina Grande')

	def test_destino_existente_e_atualizado_in_place(self):
		origem = make_endereco(rua='Rua Nova', numero='999')
		destino = make_endereco(rua='Rua Velha', numero='1')
		destino_pk = destino.pk
		resultado = empreendimento_services.sincronizar_endereco(destino, origem)
		self.assertEqual(resultado.pk, destino_pk)
		self.assertEqual(resultado.rua, 'Rua Nova')
		self.assertEqual(resultado.numero, '999')
